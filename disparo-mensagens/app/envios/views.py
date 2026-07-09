import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .models import Envio

logger = logging.getLogger(__name__)


def _verificar_assinatura(request) -> bool:
    secret = settings.EVOLUTION_WEBHOOK_SECRET.encode()
    assinatura_recebida = request.headers.get('X-Webhook-Signature', '')
    mac = hmac.new(secret, request.body, hashlib.sha256)
    return hmac.compare_digest(assinatura_recebida, mac.hexdigest())


@csrf_exempt
@require_POST
@ratelimit(key='ip', rate='60/m', block=True)
def webhook_whatsapp(request):
    if not _verificar_assinatura(request):
        logger.warning(
            "Webhook recebido com assinatura inválida — IP: %s",
            request.META.get('REMOTE_ADDR')
        )
        return HttpResponse(status=401)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("Webhook com payload inválido")
        return HttpResponse(status=400)

    evento = payload.get('event', '')
    dados = payload.get('data', {})

    logger.info("Webhook recebido — evento: %s", evento)

    if evento == 'messages.update':
        _processar_atualizacao_status(dados)
    elif evento == 'send.message':
        _processar_mensagem_enviada(dados)
    elif evento == 'messages.upsert':
        _processar_mensagem_recebida(dados)
    else:
        logger.debug("Evento ignorado: %s", evento)

    return JsonResponse({'status': 'ok'})


def _processar_mensagem_enviada(dados: dict):
    mensagem_id = dados.get('key', {}).get('id', '')
    if not mensagem_id:
        return

    try:
        envio = Envio.objects.get(mensagem_id_externo=mensagem_id)
        if envio.status == 'pendente':
            envio.status = 'enviado'
            envio.enviado_em = timezone.now()
            envio.save(update_fields=['status', 'enviado_em', 'atualizado_em'])
            logger.info("Envio %s marcado como enviado", envio.id)
    except Envio.DoesNotExist:
        logger.debug("Envio não encontrado para mensagem_id %s", mensagem_id)


def _processar_atualizacao_status(dados: dict):
    mensagem_id = dados.get('key', {}).get('id', '')
    status_raw = dados.get('update', {}).get('status', '').upper()

    if not mensagem_id or not status_raw:
        return

    STATUS_MAP = {
        'DELIVERY_ACK': 'entregue',
        'READ': 'lido',
        'PLAYED': 'lido',
    }

    novo_status = STATUS_MAP.get(status_raw)
    if not novo_status:
        return

    try:
        envio = Envio.objects.get(mensagem_id_externo=mensagem_id)

        if novo_status == 'entregue' and envio.status == 'enviado':
            envio.status = 'entregue'
            envio.entregue_em = timezone.now()
            envio.save(update_fields=['status', 'entregue_em', 'atualizado_em'])
            logger.info("Envio %s marcado como entregue", envio.id)

        elif novo_status == 'lido' and envio.status in ['enviado', 'entregue']:
            envio.status = 'lido'
            envio.lido_em = timezone.now()
            envio.save(update_fields=['status', 'lido_em', 'atualizado_em'])
            logger.info("Envio %s marcado como lido", envio.id)

    except Envio.DoesNotExist:
        logger.debug("Envio não encontrado para mensagem_id %s", mensagem_id)


def _extrair_row_id(dados: dict):
    mensagem = dados.get('message', {})

    lista = mensagem.get('listResponseMessage')
    if lista:
        return lista.get('singleSelectReply', {}).get('selectedRowId')

    botoes = mensagem.get('buttonsResponseMessage')
    if botoes:
        return botoes.get('selectedButtonId')

    return None


def _processar_mensagem_recebida(dados: dict):
    from contatos.models import Contato

    row_id = _extrair_row_id(dados)
    if row_id != 'opt_out_confirm':
        return

    remote_jid = dados.get('key', {}).get('remoteJid', '')
    if not remote_jid:
        return

    contato = Contato.buscar_por_numero_whatsapp(remote_jid)
    if not contato:
        logger.warning("Opt-out via WhatsApp recebido de número não cadastrado: %s", remote_jid)
        return

    if not contato.opt_out:
        contato.realizar_opt_out()
        logger.info("Opt-out via WhatsApp confirmado para %s", contato.telefone)