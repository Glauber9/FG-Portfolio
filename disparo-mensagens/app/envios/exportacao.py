import csv

from django.http import HttpResponse

from .relatorio import montar_relatorio_agrupado


def exportar_csv(campanha):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    nome_arquivo = f'relatorio_{campanha.nome}'.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Contato', 'Telefone', 'E-mail', 'Status WhatsApp', 'Status E-mail'])

    for linha in montar_relatorio_agrupado(campanha):
        writer.writerow([
            linha['contato'].nome,
            linha['contato'].telefone,
            linha['contato'].email,
            linha['whatsapp_titulo'],
            linha['email_titulo'],
        ])

    return response


def exportar_pdf(campanha):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    response = HttpResponse(content_type='application/pdf')
    nome_arquivo = f'relatorio_{campanha.nome}'.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}.pdf"'

    doc = SimpleDocTemplate(
        response, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )
    estilos = getSampleStyleSheet()
    titulo_estilo = ParagraphStyle('TituloRelatorio', parent=estilos['Title'], fontSize=16, spaceAfter=4)
    subtitulo_estilo = ParagraphStyle('SubtituloRelatorio', parent=estilos['Normal'], fontSize=10, textColor=colors.grey)

    elementos = [
        Paragraph(f'Relatório de Envios — {campanha.nome}', titulo_estilo),
        Paragraph(f'Status da campanha: {campanha.get_status_display()}', subtitulo_estilo),
        Spacer(1, 0.6 * cm),
    ]

    linhas_dados = montar_relatorio_agrupado(campanha)

    cabecalho = ['Contato', 'Telefone', 'WhatsApp', 'E-mail']
    tabela_dados = [cabecalho]

    total_whatsapp_ok = 0
    total_email_ok = 0

    for linha in linhas_dados:
        tabela_dados.append([
            linha['contato'].nome,
            linha['contato'].telefone,
            linha['whatsapp_simbolo'],
            linha['email_simbolo'],
        ])
        if linha['whatsapp_envio'] and linha['whatsapp_envio'].status in ('enviado', 'entregue', 'lido'):
            total_whatsapp_ok += 1
        if linha['email_envio'] and linha['email_envio'].status in ('enviado', 'entregue', 'lido'):
            total_email_ok += 1

    tabela = Table(tabela_dados, colWidths=[7 * cm, 4 * cm, 3 * cm, 3 * cm], repeatRows=1)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#161b26')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 0), (3, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabela)

    elementos.append(Spacer(1, 0.5 * cm))
    resumo_estilo = ParagraphStyle('Resumo', parent=estilos['Normal'], fontSize=9, textColor=colors.grey)
    elementos.append(Paragraph(
        f'Total de contatos: {len(linhas_dados)} · '
        f'WhatsApp enviado/entregue/lido: {total_whatsapp_ok} · '
        f'E-mail enviado: {total_email_ok}',
        resumo_estilo
    ))

    doc.build(elementos)
    return response
