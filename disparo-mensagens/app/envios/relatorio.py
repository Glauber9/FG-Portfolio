from .models import Envio


def _icone_status(envio):
    if envio is None:
        return ('—', '#4b5563', 'Não enviado por este canal')

    mapa = {
        'pendente': ('…', '#9ca3af', 'Pendente — aguardando envio'),
        'enviado': ('✓', '#9ca3af', f'Enviado em {_fmt(envio.enviado_em)}'),
        'entregue': ('✓✓', '#9ca3af', f'Entregue em {_fmt(envio.entregue_em)}'),
        'lido': ('✓✓', '#34b7f1', f'Lido em {_fmt(envio.lido_em)}'),
        'falha': ('✕', '#ef4444', envio.falha_motivo or 'Falha no envio'),
        'opt_out': ('⊘', '#6b7280', 'Contato optou por sair antes do envio'),
    }
    return mapa.get(envio.status, ('?', '#6b7280', envio.status))


def _fmt(dt):
    return dt.strftime('%d/%m/%Y %H:%M') if dt else '-'


def montar_relatorio_agrupado(campanha):

    envios = (
        Envio.objects
        .filter(campanha=campanha)
        .select_related('contato')
        .order_by('contato_id', 'canal', '-criado_em')
    )

    por_contato = {}
    for envio in envios:
        chave = envio.contato_id
        if chave not in por_contato:
            por_contato[chave] = {'contato': envio.contato, 'whatsapp': None, 'email': None}

        if por_contato[chave][envio.canal] is None:
            por_contato[chave][envio.canal] = envio

    linhas = []
    for item in por_contato.values():
        wpp_icone = _icone_status(item['whatsapp'])
        email_icone = _icone_status(item['email'])
        linhas.append({
            'contato': item['contato'],
            'whatsapp_envio': item['whatsapp'],
            'whatsapp_simbolo': wpp_icone[0],
            'whatsapp_cor': wpp_icone[1],
            'whatsapp_titulo': wpp_icone[2],
            'email_envio': item['email'],
            'email_simbolo': email_icone[0],
            'email_cor': email_icone[1],
            'email_titulo': email_icone[2],
        })

    linhas.sort(key=lambda linha: linha['contato'].nome.lower())
    return linhas
