import functools
from datetime import timedelta

from django import forms
from django.contrib import admin
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.urls import path
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import Campanha, TemplateMensagem


STATUS_PERMITIDOS_OPERADOR = ['rascunho', 'agendada']


class CampanhaAdminForm(forms.ModelForm):
    class Meta:
        model = Campanha
        fields = '__all__'

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

        if 'status' not in self.fields:
            return

        if self.request and self.request.user.is_superuser:
            return

        status_labels = dict(Campanha.STATUS_CHOICES)
        status_atual = self.instance.status if self.instance and self.instance.pk else None

        if status_atual and status_atual not in STATUS_PERMITIDOS_OPERADOR:
            self.fields['status'].choices = [(status_atual, status_labels[status_atual])]
            self.fields['status'].disabled = True
        else:
            self.fields['status'].choices = [
                (valor, status_labels[valor]) for valor in STATUS_PERMITIDOS_OPERADOR
            ]


@admin.register(TemplateMensagem)
class TemplateMensagemAdmin(ModelAdmin):
    list_display = ['nome', 'canal', 'midia_canais', 'ativo', 'criado_em']
    list_filter = ['canal', 'midia_canais', 'ativo']
    search_fields = ['nome', 'corpo']
    readonly_fields = ['id', 'criado_em', 'atualizado_em']

    fieldsets = (
        ('Informações', {
            'fields': ('id', 'nome', 'canal', 'ativo')
        }),
        ('Conteúdo', {
            'fields': ('assunto_email', 'corpo', 'media', 'media_tipo', 'midia_canais')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Campanha)
class CampanhaAdmin(ModelAdmin):
    form = CampanhaAdminForm
    list_display = ['nome', 'template', 'status', 'envios_inicio_em', 'envios_fim_em', 'criado_em']
    list_filter = ['status', 'envios_inicio_em', 'envios_fim_em']
    search_fields = ['nome']
    readonly_fields = ['id', 'iniciada_em', 'concluida_em', 'criado_em', 'atualizado_em']
    filter_horizontal = ['grupos', 'contatos_extras']
    actions = ['disparar_campanha', 'cancelar_campanha']

    fieldsets = (
        ('Informações', {
            'fields': ('id', 'nome', 'template', 'status')
        }),
        ('Destinatários', {
            'fields': ('grupos', 'contatos_extras')
        }),
        ('Agendamento', {
            'fields': ('envios_inicio_em', 'envios_fim_em', 'iniciada_em', 'concluida_em')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    class Media:
        js = ('campanhas/js/autorefresh_campanhas.js',)

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super().get_form(request, obj, **kwargs)
        return functools.partial(FormClass, request=request)

    def get_urls(self):
        urls_customizadas = [
            path(
                'status-atualizacao/',
                self.admin_site.admin_view(self.status_ultima_atualizacao_view),
                name='campanhas_campanha_status_atualizacao',
            ),
            path(
                'dashboard-dados/',
                self.admin_site.admin_view(self.dashboard_dados_view),
                name='campanhas_campanha_dashboard_dados',
            ),
        ]
        return urls_customizadas + super().get_urls()

    def status_ultima_atualizacao_view(self, request):
        ultima = (
            Campanha.objects
            .order_by('-atualizado_em')
            .values_list('atualizado_em', flat=True)
            .first()
        )
        return JsonResponse({
            'ultima_atualizacao': ultima.isoformat() if ultima else None,
        })

    def _intervalo(self, periodo):
        hoje = timezone.now().date()
        if periodo == 'hoje':
            return hoje, hoje
        if periodo == '7d':
            return hoje - timedelta(days=6), hoje
        if periodo == '30d':
            return hoje - timedelta(days=29), hoje
        return None, hoje

    def _dados_grafico_canal(self, periodo):
        from envios.models import Envio

        inicio, fim = self._intervalo(periodo)
        qs = Envio.objects.filter(criado_em__date__lte=fim)
        if inicio:
            qs = qs.filter(criado_em__date__gte=inicio)

        serie_qs = (
            qs.annotate(dia=TruncDate('criado_em'))
            .values('dia', 'canal')
            .annotate(total=Count('id'))
        )
        mapa = {}
        for item in serie_qs:
            mapa.setdefault(item['dia'], {})[item['canal']] = item['total']

        if inicio:
            inicio_real = inicio
        else:
            primeiro = Envio.objects.order_by('criado_em').values_list('criado_em', flat=True).first()
            inicio_real = primeiro.date() if primeiro else fim

        dias = [inicio_real + timedelta(days=i) for i in range((fim - inicio_real).days + 1)]

        return {
            'labels': [d.strftime('%d/%m') for d in dias],
            'whatsapp': [mapa.get(d, {}).get('whatsapp', 0) for d in dias],
            'email': [mapa.get(d, {}).get('email', 0) for d in dias],
        }

    def _dados_grafico_status(self, periodo):
        from envios.models import Envio

        inicio, fim = self._intervalo(periodo)
        qs = Envio.objects.filter(criado_em__date__lte=fim)
        if inicio:
            qs = qs.filter(criado_em__date__gte=inicio)

        status_labels_map = dict(Envio.STATUS_CHOICES)
        status_qs = qs.values('status').annotate(total=Count('id')).order_by('-total')

        return {
            'labels': [status_labels_map.get(item['status'], item['status']) for item in status_qs],
            'data': [item['total'] for item in status_qs],
        }

    def dashboard_dados_view(self, request):
        tipo = request.GET.get('tipo')
        periodo = request.GET.get('periodo', '7d')

        if tipo == 'canal':
            return JsonResponse(self._dados_grafico_canal(periodo))
        if tipo == 'status':
            return JsonResponse(self._dados_grafico_status(periodo))
        return JsonResponse({'detail': 'tipo inválido'}, status=400)

    @admin.action(description='Disparar campanhas selecionadas')
    def disparar_campanha(self, request, queryset):
        from django.utils import timezone as tz
        from .tasks import iniciar_campanha
        for campanha in queryset.filter(status__in=['rascunho', 'agendada']):
            iniciar_campanha.delay(str(campanha.id))
            campanha.status = 'em_andamento'
            campanha.iniciada_em = tz.now()
            campanha.save(update_fields=['status', 'iniciada_em', 'atualizado_em'])
        self.message_user(request, f'{queryset.count()} campanha(s) disparada(s).')

    @admin.action(description='Cancelar campanhas selecionadas')
    def cancelar_campanha(self, request, queryset):
        queryset.filter(status__in=['rascunho', 'agendada']).update(status='cancelada')
        self.message_user(request, f'{queryset.count()} campanha(s) cancelada(s).')