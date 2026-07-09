import logging
import random
from datetime import timedelta
from email.mime.image import MIMEImage

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone

logger = logging.getLogger(__name__)

def _gerar_horarios_envio(quantidade, inicio, fim, delay_min, delay_max):
    horarios = []
    agora = timezone.now()
    horario_atual = max(inicio, agora)

    for i in range(quantidade):
        if fim and horario_atual > fim:
            logger.warning(
                "Janela de envio esgotada: %d envio(s) serão agendados após o fim da janela",
                quantidade - i
            )

        horarios.append(horario_atual)
        delay = random.randint(delay_min, delay_max)
        horario_atual = horario_atual + timedelta(seconds=delay)

    return horarios

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='campanhas.tasks.iniciar_campanha',
    ignore_result=False,
)
def iniciar_campanha(self, campanha_id: str):
    from .models import Campanha
    from contatos.models import Contato
    from envios.models import Envio

    try:
        campanha = Campanha.objects.get(id=campanha_id)
    except Campanha.DoesNotExist:
        logger.error("Campanha %s não encontrada", campanha_id)
        return

    if campanha.status not in ['rascunho', 'agendada', 'em_andamento']:
        logger.warning("Campanha %s com status inválido: %s", campanha_id, campanha.status)
        return

    contatos_grupos = Contato.objects.filter(
        grupos__campanhas=campanha,
        ativo=True,
        opt_out=False
    )
    contatos_extras = campanha.contatos_extras.filter(
        ativo=True,
        opt_out=False
    )
    contatos = list(set(list(contatos_grupos) + list(contatos_extras)))

    canal = str(campanha.template.canal).lower()

    pares = []
    for contato in contatos:
        canais = ['whatsapp', 'email'] if canal == 'ambos' else [canal]
        for c in canais:
            pares.append((contato, c.lower()))

    inicio = campanha.envios_inicio_em or campanha.agendada_para or timezone.now()
    horarios = _gerar_horarios_envio(
        quantidade=len(pares),
        inicio=inicio,
        fim=campanha.envios_fim_em,
        delay_min=campanha.delay_minimo_segundos,
        delay_max=campanha.delay_maximo_segundos,
    )

    envios_criados = 0

    for (contato, c_lower), horario_envio in zip(pares, horarios):
        envio = Envio.objects.create(
            campanha=campanha,
            contato=contato,
            canal=c_lower,
            status='pendente',
        )
        envios_criados += 1

        logger.info(
            "Agendando envio para %s via %s às %s",
            contato.telefone, c_lower, horario_envio.isoformat()
        )

        if c_lower == 'whatsapp':
            enviar_whatsapp.apply_async(args=[str(envio.id)], eta=horario_envio)
        else:
            enviar_email.apply_async(args=[str(envio.id)], eta=horario_envio)

    campanha.status = 'em_andamento'
    campanha.iniciada_em = timezone.now()
    campanha.save(update_fields=['status', 'iniciada_em', 'atualizado_em'])

    logger.info(
        "Campanha %s processada: %d envio(s) agendado(s)",
        campanha_id, envios_criados
    )

@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=120,
    name='campanhas.tasks.enviar_whatsapp'
)
def enviar_whatsapp(self, envio_id: str):
    from envios.models import Envio
    from .services import EvolutionAPIService

    try:
        envio = Envio.objects.select_related('contato', 'campanha__template').get(id=envio_id)
    except Envio.DoesNotExist:
        logger.error("Envio %s não encontrado", envio_id)
        return

    if envio.status not in ['pendente', 'falha']:
        return

    envio.tentativas += 1
    envio.save(update_fields=['tentativas', 'atualizado_em'])

    template = envio.campanha.template
    mensagem = template.renderizar(envio.contato)

    try:
        service = EvolutionAPIService()
        tem_midia = template.tem_midia_para_canal('whatsapp')

        if tem_midia:
            with template.media.open('rb') as f:
                media_bytes = f.read()
            mensagem_id = service.enviar_midia(
                telefone=envio.contato.telefone,
                media_bytes=media_bytes,
                media_nome=template.media.name.split('/')[-1],
                media_tipo=template.obter_tipo_midia(),
                legenda=mensagem,
            )
        else:
            mensagem_id = service.enviar_mensagem(
                telefone=envio.contato.telefone,
                mensagem=mensagem,
            )

        envio.status = 'enviado'
        envio.mensagem_id_externo = mensagem_id
        envio.enviado_em = timezone.now()
        envio.save(update_fields=['status', 'mensagem_id_externo', 'enviado_em', 'atualizado_em'])
        logger.info("WhatsApp enviado para %s — envio %s", envio.contato.telefone, envio_id)
        envio.campanha.finalizar_se_concluida()

    except Exception as exc:
        envio.status = 'falha'
        envio.falha_motivo = str(exc)
        envio.save(update_fields=['status', 'falha_motivo', 'atualizado_em'])
        logger.error("Falha ao enviar WhatsApp para %s: %s", envio.contato.telefone, exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            envio.campanha.finalizar_se_concluida()

@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=120,
    name='campanhas.tasks.enviar_email'
)
def enviar_email(self, envio_id: str):
    from envios.models import Envio

    try:
        envio = Envio.objects.select_related('contato', 'campanha__template').get(id=envio_id)
    except Envio.DoesNotExist:
        logger.error("Envio %s não encontrado", envio_id)
        return

    if envio.status not in ['pendente', 'falha']:
        return

    envio.tentativas += 1
    envio.save(update_fields=['tentativas', 'atualizado_em'])

    template = envio.campanha.template
    mensagem = template.renderizar(envio.contato)

    try:
        if template.tem_midia_para_canal('email') and template.obter_tipo_midia() == 'image':
            _enviar_email_com_imagem_inline(template, envio.contato, mensagem)
        elif template.tem_midia_para_canal('email'):
            _enviar_email_com_anexo(template, envio.contato, mensagem)
        else:
            _enviar_email_texto(template, envio.contato, mensagem)

        envio.status = 'enviado'
        envio.enviado_em = timezone.now()
        envio.save(update_fields=['status', 'enviado_em', 'atualizado_em'])
        logger.info("Email enviado para %s — envio %s", envio.contato.email, envio_id)
        envio.campanha.finalizar_se_concluida()

    except Exception as exc:
        envio.status = 'falha'
        envio.falha_motivo = str(exc)
        envio.save(update_fields=['status', 'falha_motivo', 'atualizado_em'])
        logger.error("Falha ao enviar email para %s: %s", envio.contato.email, exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            envio.campanha.finalizar_se_concluida()

def _enviar_email_texto(template, contato, mensagem):
    from django.core.mail import send_mail
    from django.conf import settings

    send_mail(
        subject=template.assunto_email or 'Mensagem',
        message=mensagem,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[contato.email],
        fail_silently=False,
    )

def _enviar_email_com_imagem_inline(template, contato, mensagem):
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives
    from django.utils.html import escape

    cid = 'imagem_campanha'
    corpo_html = (
        f'<div style="font-family: sans-serif; white-space: pre-wrap;">'
        f'{escape(mensagem)}'
        f'<br><br><img src="cid:{cid}" style="max-width: 100%; height: auto;">'
        f'</div>'
    )

    email = EmailMultiAlternatives(
        subject=template.assunto_email or 'Mensagem',
        body=mensagem,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[contato.email],
    )
    email.attach_alternative(corpo_html, 'text/html')

    with template.media.open('rb') as f:
        media_bytes = f.read()

    imagem = MIMEImage(media_bytes)
    imagem.add_header('Content-ID', f'<{cid}>')
    imagem.add_header('Content-Disposition', 'inline', filename=template.media.name.split('/')[-1])
    email.attach(imagem)
    email.send(fail_silently=False)

def _enviar_email_com_anexo(template, contato, mensagem):
    from django.conf import settings
    from django.core.mail import EmailMessage

    email = EmailMessage(
        subject=template.assunto_email or 'Mensagem',
        body=mensagem,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[contato.email],
    )
    with template.media.open('rb') as f:
        email.attach(template.media.name.split('/')[-1], f.read())
    email.send(fail_silently=False)

@shared_task(name='campanhas.tasks.verificar_campanhas_agendadas', ignore_result=False)
def verificar_campanhas_agendadas():
    from .models import Campanha

    agora = timezone.now()
    campanhas = Campanha.objects.filter(
        status='agendada',
        agendada_para__lte=agora
    )

    for campanha in campanhas:
        logger.info("Disparando campanha agendada %s", campanha.id)
        iniciar_campanha.delay(str(campanha.id))

@shared_task(name='campanhas.tasks.verificar_campanhas_para_finalizar', ignore_result=False)
def verificar_campanhas_para_finalizar():
    from .models import Campanha

    campanhas = Campanha.objects.filter(status='em_andamento')
    fechadas = 0
    for campanha in campanhas:
        if campanha.finalizar_se_concluida():
            fechadas += 1

    if fechadas:
        logger.info("%d campanha(s) finalizada(s) automaticamente", fechadas)