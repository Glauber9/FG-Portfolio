from django.contrib import admin, messages
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from unfold.admin import ModelAdmin
from unfold.decorators import action

from campanhas.models import Campanha

from .exportacao import exportar_csv, exportar_pdf
from .models import Envio
from .relatorio import montar_relatorio_agrupado


@admin.register(Envio)
class EnvioAdmin(ModelAdmin):
    list_display = ['contato', 'campanha', 'canal', 'status', 'tentativas', 'enviado_em']
    list_filter = ['status', 'canal', 'criado_em', 'campanha']
    search_fields = ['contato__nome', 'contato__telefone', 'campanha__nome', 'mensagem_id_externo']
    readonly_fields = [
        'id', 'campanha', 'contato', 'canal', 'mensagem_id_externo',
        'tentativas', 'enviado_em', 'entregue_em', 'lido_em',
        'falha_motivo', 'criado_em', 'atualizado_em'
    ]
    actions = ['reenviar_selecionados']

    fieldsets = (
        ('Informações', {
            'fields': ('id', 'campanha', 'contato', 'canal')
        }),
        ('Status', {
            'fields': ('status', 'tentativas', 'mensagem_id_externo')
        }),
        ('Timestamps', {
            'fields': ('enviado_em', 'entregue_em', 'lido_em')
        }),
        ('Erro', {
            'fields': ('falha_motivo',),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    class Media:
        js = ('envios/js/autorefresh_envios.js',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'registros/',
                self.admin_site.admin_view(self.changelist_view_bruto),
                name='envios_registros_brutos',
            ),
            path(
                'status-atualizacao/',
                self.admin_site.admin_view(self.status_ultima_atualizacao_view),
                name='envios_envio_status_atualizacao',
            ),
        ]
        return custom_urls + urls

    def status_ultima_atualizacao_view(self, request):
        ultima = (
            Envio.objects
            .order_by('-atualizado_em')
            .values_list('atualizado_em', flat=True)
            .first()
        )
        return JsonResponse({
            'ultima_atualizacao': ultima.isoformat() if ultima else None,
        })

    def changelist_view(self, request, extra_context=None):
        return self.relatorio_agrupado(request)

    def changelist_view_bruto(self, request, extra_context=None):
        return super().changelist_view(request, extra_context)

    def relatorio_agrupado(self, request):
        campanhas = Campanha.objects.order_by('-criado_em')

        campanha_id = request.GET.get('campanha')
        campanha_selecionada = None
        linhas = []

        if campanha_id:
            try:
                campanha_selecionada = campanhas.get(id=campanha_id)
            except Campanha.DoesNotExist:
                raise Http404('Campanha não encontrada')

            linhas = montar_relatorio_agrupado(campanha_selecionada)

            export = request.GET.get('export')
            if export == 'csv':
                return exportar_csv(campanha_selecionada)
            if export == 'pdf':
                return exportar_pdf(campanha_selecionada)

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': 'Envios',
            'campanhas': campanhas,
            'campanha_selecionada': campanha_selecionada,
            'linhas': linhas,
            'url_registros_brutos': reverse('admin:envios_registros_brutos'),
            'media': self.media,
        }
        return TemplateResponse(request, 'admin/envios/envio/relatorio.html', context)

    @admin.action(description='Reenviar selecionados (cria novo envio)')
    def reenviar_selecionados(self, request, queryset):
        from campanhas.tasks import enviar_whatsapp, enviar_email

        total = 0
        for envio_antigo in queryset:
            novo_envio = Envio.objects.create(
                campanha=envio_antigo.campanha,
                contato=envio_antigo.contato,
                canal=envio_antigo.canal,
                status='pendente',
            )
            if novo_envio.canal == 'whatsapp':
                enviar_whatsapp.apply_async(args=[str(novo_envio.id)], queue='whatsapp')
            else:
                enviar_email.apply_async(args=[str(novo_envio.id)], queue='email')
            total += 1

        self.message_user(request, f'{total} reenvio(s) criado(s) e enfileirado(s).', messages.SUCCESS)