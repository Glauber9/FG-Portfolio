import uuid
from django.db import models


class Contato(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    ativo = models.BooleanField(default=True)
    opt_out = models.BooleanField(default=False)
    opt_out_em = models.DateTimeField(null=True, blank=True)
    token_opt_out = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    token_opt_out_expira_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contato'
        verbose_name_plural = 'Contatos'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['opt_out']),
        ]

    def __str__(self):
        return f'{self.nome} — {self.telefone}'

    def realizar_opt_out(self):
        from django.utils import timezone
        self.opt_out = True
        self.opt_out_em = timezone.now()
        self.ativo = False
        self.save(update_fields=['opt_out', 'opt_out_em', 'ativo', 'atualizado_em'])

    @classmethod
    def buscar_por_numero_whatsapp(cls, remote_jid):
        digitos = ''.join(filter(str.isdigit, remote_jid.split('@')[0]))
        if not digitos:
            return None

        contato = cls.objects.filter(telefone=digitos).first()
        if contato:
            return contato

        sufixo = digitos[-8:]
        return cls.objects.filter(telefone__endswith=sufixo).first()


class GrupoContatos(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    contatos = models.ManyToManyField(Contato, related_name='grupos', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Grupo de Contatos'
        verbose_name_plural = 'Grupos de Contatos'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def total_contatos_ativos(self):
        return self.contatos.filter(ativo=True, opt_out=False).count()
