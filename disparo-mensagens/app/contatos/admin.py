from django.contrib import admin, messages
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from unfold.admin import ModelAdmin
from unfold.decorators import action

from .forms import ImportarContatosForm
from .importers import importar_contatos
from .models import Contato, GrupoContatos


@admin.register(Contato)
class ContatoAdmin(ModelAdmin):
    list_display = ['nome', 'telefone', 'email', 'ativo', 'opt_out', 'criado_em']
    list_filter = ['ativo', 'opt_out', 'criado_em']
    search_fields = ['nome', 'telefone', 'email']
    readonly_fields = ['id', 'token_opt_out', 'token_opt_out_expira_em', 'opt_out_em', 'criado_em', 'atualizado_em']
    ordering = ['-criado_em']
    actions = ['realizar_opt_out', 'reativar_contatos']

    actions_list = ['abrir_importacao']

    class Media:
        js = ('contatos/js/autorefresh_contatos.js',)

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('id', 'nome', 'telefone', 'email')
        }),
        ('Status', {
            'fields': ('ativo', 'opt_out', 'opt_out_em')
        }),
        ('Opt-out', {
            'fields': ('token_opt_out', 'token_opt_out_expira_em'),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'importar/',
                self.admin_site.admin_view(self.importar_contatos),
                name='contato_importar',
            ),
            path(
                'status-atualizacao/',
                self.admin_site.admin_view(self.status_ultima_atualizacao_view),
                name='contatos_contato_status_atualizacao',
            ),
        ]
        return custom_urls + urls

    def status_ultima_atualizacao_view(self, request):
        ultima = (
            Contato.objects
            .order_by('-atualizado_em')
            .values_list('atualizado_em', flat=True)
            .first()
        )
        return JsonResponse({
            'ultima_atualizacao': ultima.isoformat() if ultima else None,
        })

    @action(description='Importar Contatos', url_path='ir-para-importacao')
    def abrir_importacao(self, request):
        return redirect(reverse('admin:contato_importar'))

    def importar_contatos(self, request):
        if request.method == 'POST':
            form = ImportarContatosForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    resumo = importar_contatos(form.cleaned_data['arquivo'])
                except ValueError as exc:
                    form.add_error('arquivo', str(exc))
                    resumo = None

                if resumo is not None:
                    mensagens = [
                        f"{resumo['criados']} contato(s) criado(s)",
                        f"{resumo['atualizados']} contato(s) atualizado(s)",
                        f"{resumo['ignorados']} linha(s) ignorada(s)",
                    ]
                    if resumo['erros']:
                        messages.warning(request, 'Importação concluída com avisos. ' + ' | '.join(mensagens))
                        for erro in resumo['erros'][:10]:
                            messages.warning(request, erro)
                    else:
                        messages.success(request, 'Importação concluída. ' + ' | '.join(mensagens))
                    return HttpResponseRedirect(reverse('admin:contatos_contato_changelist'))
        else:
            form = ImportarContatosForm()

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': 'Importar contatos',
            'form': form,
        }
        return TemplateResponse(request, 'admin/contatos/contato/importar_contatos.html', context)

    @admin.action(description='Realizar opt-out dos contatos selecionados')
    def realizar_opt_out(self, request, queryset):
        for contato in queryset:
            contato.realizar_opt_out()
        self.message_user(request, f'{queryset.count()} contato(s) removido(s) com sucesso.')

    @admin.action(description='Reativar contatos selecionados')
    def reativar_contatos(self, request, queryset):
        queryset.update(ativo=True, opt_out=False, opt_out_em=None)
        self.message_user(request, f'{queryset.count()} contato(s) reativado(s) com sucesso.')


@admin.register(GrupoContatos)
class GrupoContatosAdmin(ModelAdmin):
    list_display = ['nome', 'total_contatos_ativos', 'criado_em']
    search_fields = ['nome']
    readonly_fields = ['id', 'criado_em', 'atualizado_em']
    filter_horizontal = ['contatos']

    fieldsets = (
        ('Informações', {
            'fields': ('id', 'nome', 'descricao')
        }),
        ('Contatos', {
            'fields': ('contatos',)
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )