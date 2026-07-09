import uuid
from django.db import models


class Envio(models.Model):
    CANAL_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('email', 'E-mail'),
    ]

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('enviado', 'Enviado'),
        ('entregue', 'Entregue'),
        ('lido', 'Lido'),
        ('falha', 'Falha'),
        ('opt_out', 'Opt-out'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campanha = models.ForeignKey(
        'campanhas.Campanha',
        on_delete=models.PROTECT,
        related_name='envios'
    )
    contato = models.ForeignKey(
        'contatos.Contato',
        on_delete=models.PROTECT,
        related_name='envios'
    )
    canal = models.CharField(max_length=20, choices=CANAL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    mensagem_id_externo = models.CharField(max_length=255, blank=True)
    tentativas = models.PositiveSmallIntegerField(default=0)
    enviado_em = models.DateTimeField(null=True, blank=True)
    entregue_em = models.DateTimeField(null=True, blank=True)
    lido_em = models.DateTimeField(null=True, blank=True)
    falha_motivo = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Envio'
        verbose_name_plural = 'Envios'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['canal']),
            models.Index(fields=['mensagem_id_externo']),
            models.Index(fields=['campanha', 'status']),
            models.Index(fields=['campanha', 'contato']),  
        ]

    def __str__(self):
        return f'{self.contato.nome} — {self.canal} — {self.get_status_display()}'