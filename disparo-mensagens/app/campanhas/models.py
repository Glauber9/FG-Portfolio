import uuid
from django.conf import settings
from django.db import models
from django.urls import reverse


class TemplateMensagem(models.Model):
    CANAL_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('email', 'E-mail'),
        ('ambos', 'Ambos'),
    ]

    MIDIA_CHOICES = [
        ('image', 'Imagem'),
        ('video', 'Vídeo'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    canal = models.CharField(max_length=20, choices=CANAL_CHOICES)
    assunto_email = models.CharField(max_length=255, blank=True)
    corpo = models.TextField(
        help_text='Variáveis disponíveis: {{nome}}, {{link_opt_out}}'
    )
    media = models.FileField(upload_to='campanhas/midias/', blank=True, null=True)
    media_tipo = models.CharField(max_length=10, choices=MIDIA_CHOICES, blank=True)
    midia_canais = models.CharField(
        max_length=20,
        choices=CANAL_CHOICES,
        default='whatsapp',
        help_text='Escolha em quais canais a mídia será usada.',
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Template de Mensagem'
        verbose_name_plural = 'Templates de Mensagem'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.nome} ({self.get_canal_display()})'

    def renderizar(self, contato):
        corpo = self.corpo

        primeiro_nome = contato.nome.split()[0] if contato.nome else ""

        variaveis = {
            "{{nome}}": primeiro_nome,
            "{{link_opt_out}}": self.obter_link_opt_out(contato),
        }

        for chave, valor in variaveis.items():
            corpo = corpo.replace(chave, valor)

        return corpo

    def tem_midia(self):
        return bool(self.media and self.media.name)

    def tem_midia_para_canal(self, canal: str) -> bool:
        if not self.tem_midia():
            return False
        return self.midia_canais in {canal, 'ambos'}

    def obter_tipo_midia(self):
        if self.media_tipo:
            return self.media_tipo

        if self.media and self.media.name:
            nome_arquivo = self.media.name.lower()
            if nome_arquivo.endswith(('.mp4', '.mov', '.mkv', '.webm')):
                return 'video'

        return 'image'

    def obter_link_opt_out(self, contato) -> str:
        caminho = reverse('contatos:opt_out', args=[contato.token_opt_out])
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}{caminho}"


class Campanha(models.Model):
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('agendada', 'Agendada'),
        ('em_andamento', 'Em andamento'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    template = models.ForeignKey(
        TemplateMensagem,
        on_delete=models.PROTECT,
        related_name='campanhas'
    )
    grupos = models.ManyToManyField(
        'contatos.GrupoContatos',
        related_name='campanhas',
        blank=True
    )
    contatos_extras = models.ManyToManyField(
        'contatos.Contato',
        related_name='campanhas_extras',
        blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='rascunho')
    agendada_para = models.DateTimeField(null=True, blank=True)
    envios_inicio_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Início da janela de envio. Se vazio, usa a data agendada ou o momento atual.',
    )
    envios_fim_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fim da janela de envio. O Celery distribui as tarefas dentro desse período.',
    )
    delay_minimo_segundos = models.PositiveIntegerField(
        default=20,
        help_text='Intervalo mínimo, em segundos, entre um envio e o próximo.',
    )
    delay_maximo_segundos = models.PositiveIntegerField(
        default=90,
        help_text='Intervalo máximo, em segundos, entre um envio e o próximo.',
    )
    iniciada_em = models.DateTimeField(null=True, blank=True)
    concluida_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Campanha'
        verbose_name_plural = 'Campanhas'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['status', 'agendada_para']),
            models.Index(fields=['envios_inicio_em']),
            models.Index(fields=['envios_fim_em']),
        ]

    def __str__(self):
        return f'{self.nome} — {self.get_status_display()}'

    def total_destinatarios(self):
        contatos_grupos = self.grupos.values_list(
            'contatos', flat=True
        ).filter(contatos__ativo=True, contatos__opt_out=False)
        contatos_extras = self.contatos_extras.filter(
            ativo=True, opt_out=False
        ).values_list('id', flat=True)
        return len(set(list(contatos_grupos) + list(contatos_extras)))

    def esta_totalmente_processada(self):
        from envios.models import Envio
        return not Envio.objects.filter(campanha=self, status='pendente').exists()

    def finalizar_se_concluida(self):
        from django.utils import timezone
        if self.status == 'em_andamento' and self.esta_totalmente_processada():
            self.status = 'concluida'
            self.concluida_em = timezone.now()
            self.save(update_fields=['status', 'concluida_em', 'atualizado_em'])
            return True
        return False
