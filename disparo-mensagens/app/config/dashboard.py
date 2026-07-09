from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone


def dashboard_callback(request, context):
    from campanhas.models import Campanha
    from envios.models import Envio

    hoje = timezone.now().date()
    campanhas_em_andamento = Campanha.objects.filter(status='em_andamento').count()
    campanhas_concluidas_hoje = Campanha.objects.filter(
        status='concluida', concluida_em__date=hoje
    ).count()

    envios_hoje = Envio.objects.filter(criado_em__date=hoje)
    total_envios_hoje = envios_hoje.count()
    envios_falha_hoje = envios_hoje.filter(status='falha').count()
    envios_entregues_hoje = envios_hoje.filter(status='entregue').count()

    taxa_sucesso = 0
    if total_envios_hoje:
        taxa_sucesso = round((envios_entregues_hoje / total_envios_hoje) * 100, 1)

    envios_whatsapp_hoje = envios_hoje.filter(canal='whatsapp').count()
    envios_email_hoje = envios_hoje.filter(canal='email').count()

    inicio_serie = hoje - timedelta(days=6)
    serie_qs = (
        Envio.objects.filter(criado_em__date__gte=inicio_serie)
        .annotate(dia=TruncDate('criado_em'))
        .values('dia', 'canal')
        .annotate(total=Count('id'))
    )

    mapa_serie = {}
    for item in serie_qs:
        mapa_serie.setdefault(item['dia'], {})[item['canal']] = item['total']

    dias = [inicio_serie + timedelta(days=i) for i in range(7)]
    serie_labels = [d.strftime('%d/%m') for d in dias]
    serie_whatsapp = [mapa_serie.get(d, {}).get('whatsapp', 0) for d in dias]
    serie_email = [mapa_serie.get(d, {}).get('email', 0) for d in dias]
    status_labels_map = dict(Envio.STATUS_CHOICES)
    status_qs = (
        envios_hoje.values('status')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    donut_labels = [status_labels_map.get(item['status'], item['status']) for item in status_qs]
    donut_data = [item['total'] for item in status_qs]
    campanhas_ativas_qs = Campanha.objects.filter(status='em_andamento')
    campanhas_ativas_progresso = []
    for c in campanhas_ativas_qs:
        total = c.total_destinatarios()
        processados = c.envios.exclude(status='pendente').count()
        pct = round((processados / total) * 100, 1) if total else 0
        campanhas_ativas_progresso.append({
            'nome': c.nome,
            'status': c.get_status_display(),
            'total': total,
            'processados': processados,
            'pct': pct,
        })

    ultimas_campanhas_qs = Campanha.objects.order_by('-criado_em')[:5]

    context.update({
        "kpis": [
            {"title": "Campanhas em andamento", "value": campanhas_em_andamento},
            {"title": "Campanhas concluídas hoje", "value": campanhas_concluidas_hoje},
            {"title": "Envios hoje", "value": total_envios_hoje},
            {"title": "Falhas hoje", "value": envios_falha_hoje},
            {"title": "Taxa de sucesso hoje", "value": f"{taxa_sucesso}%"},
        ],
        "envios_por_canal_hoje": [
            {"title": "WhatsApp", "value": envios_whatsapp_hoje},
            {"title": "E-mail", "value": envios_email_hoje},
        ],
        "serie_labels": serie_labels,
        "serie_whatsapp": serie_whatsapp,
        "serie_email": serie_email,
        "donut_labels": donut_labels,
        "donut_data": donut_data,
        "campanhas_ativas_progresso": campanhas_ativas_progresso,
        "tabela_ultimas_campanhas": {
            "headers": ["Nome", "Status", "Criada em"],
            "rows": [
                [
                    c.nome,
                    c.get_status_display(),
                    c.criado_em.strftime("%d/%m/%Y %H:%M"),
                ]
                for c in ultimas_campanhas_qs
            ] or [["Nenhuma campanha cadastrada", "-", "-"]],
        },
    })
    return context