import logging
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .importers import importar_contatos, importar_contatos_de_linhas
from .models import Contato
from django.shortcuts import get_object_or_404, render
logger = logging.getLogger(__name__)


def _carregar_arquivo_remoto(url: str):
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {'http', 'https'}:
        raise ValueError('A URL deve usar http ou https.')

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    nome_arquivo = Path(parsed_url.path).name
    if not nome_arquivo:
        content_type = response.headers.get('Content-Type', '').lower()
        if 'csv' in content_type:
            nome_arquivo = 'importacao.csv'
        elif 'spreadsheetml' in content_type or 'xlsx' in content_type:
            nome_arquivo = 'importacao.xlsx'
        else:
            nome_arquivo = 'importacao.csv'

    arquivo = BytesIO(response.content)
    arquivo.name = nome_arquivo
    return arquivo


@require_GET
@ratelimit(key='ip', rate='5/h', block=True)
def opt_out(request, token):
    contato = get_object_or_404(Contato, token_opt_out=token)

    if contato.opt_out:
        return render(
            request,
            "admin/contatos/contato/opt_out_confirmado.html",
            {
                "titulo": "Você já estava descadastrado",
                "mensagem": "Seu contato já havia sido removido da nossa lista.",
                "contato": contato,
            },
        )

    if contato.token_opt_out_expira_em and contato.token_opt_out_expira_em < timezone.now():
        return render(
            request,
            "admin/contatos/contato/opt_out_confirmado.html",
            {
                "titulo": "Link expirado",
                "mensagem": "Este link de descadastro expirou. Entre em contato conosco diretamente.",
                "contato": contato,
            },
        )

    contato.realizar_opt_out()
    logger.info("Opt-out realizado para contato %s", contato.id)

    return render(
        request,
        "admin/contatos/contato/opt_out_confirmado.html",
        {
            "titulo": "Descadastro realizado",
            "mensagem": f"Olá {contato.nome}, você foi removido da nossa lista com sucesso.",
            "contato": contato,
        },
    )

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def importar_contatos_api(request):
    arquivo = request.FILES.get('arquivo') or request.data.get('arquivo')
    contatos = request.data.get('contatos')
    url = request.data.get('url')

    if sum(bool(valor) for valor in (arquivo, contatos, url)) > 1:
        return Response(
            {'detail': 'Envie apenas um formato por vez: arquivo, lista de contatos ou url.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if contatos is not None:
        if not isinstance(contatos, list):
            return Response(
                {'detail': 'O campo "contatos" deve ser uma lista de objetos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            resumo = importar_contatos_de_linhas(contatos)
        except Exception as exc:  # pragma: no cover - defensive API surface
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 'ok', 'resumo': resumo}, status=status.HTTP_200_OK)

    if not arquivo:
        if url:
            try:
                arquivo = _carregar_arquivo_remoto(url)
            except requests.RequestException as exc:
                return Response(
                    {'detail': f'Não foi possível baixar o arquivo remoto: {exc}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if not arquivo:
        return Response(
            {'detail': 'Envie um arquivo CSV ou XLSX no campo "arquivo", uma lista no campo "contatos" ou uma url no campo "url".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        resumo = importar_contatos(arquivo)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            'status': 'ok',
            'resumo': resumo,
        },
        status=status.HTTP_200_OK,
    )