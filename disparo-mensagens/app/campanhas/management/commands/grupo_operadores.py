from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db.utils import ProgrammingError


MODELS_PERMITIDOS = [
    ('campanhas', 'campanha'),
    ('campanhas', 'templatemensagem'),
    ('contatos', 'contato'),
    ('contatos', 'grupocontatos'),
    ('envios', 'envio'),
]

ACOES = ['add', 'change', 'delete', 'view']


class Command(BaseCommand):
    help = (
        'Cria (ou atualiza) o grupo "Operadores" com permissão de '
        'add/change/delete/view apenas em Campanhas, Templates, Contatos, '
        'Grupos de Contatos e Envios. Nenhum acesso a Users, Groups, '
        'Permissions, Task Results ou outras áreas técnicas.'
    )

    def handle(self, *args, **options):
        grupo, criado = Group.objects.get_or_create(name='Operadores')

        permissoes = []
        faltando = []

        for app_label, model_name in MODELS_PERMITIDOS:
            for acao in ACOES:
                codename = f'{acao}_{model_name}'
                try:
                    permissao = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                    permissoes.append(permissao)
                except Permission.DoesNotExist:
                    faltando.append(f'{app_label}.{codename}')

        grupo.permissions.set(permissoes)

        acao_texto = 'criado' if criado else 'atualizado'
        self.stdout.write(self.style.SUCCESS(
            f'Grupo "Operadores" {acao_texto} com {len(permissoes)} permissões.'
        ))

        if faltando:
            self.stdout.write(self.style.WARNING(
                'Atenção: as permissões abaixo não foram encontradas '
                '(rode as migrations antes, ou confira o nome do model):\n  '
                + '\n  '.join(faltando)
            ))
