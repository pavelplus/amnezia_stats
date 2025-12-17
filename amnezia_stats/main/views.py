from datetime import datetime, timedelta, timezone

from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from .stats import process_wg_stats_files
from .models import WgClient, WgStatsRecord
from config.settings import SERVER_TIME_ZONE_OFFSET

SERVER_TZ = timezone(timedelta(hours=SERVER_TIME_ZONE_OFFSET))


def index(request):
    
    context = {}
    
    return TemplateResponse(request, "main/index.html", context)


@login_required
def stats(request):
    process_wg_stats_files()
    
    time_now = datetime.now(tz=SERVER_TZ)
    time_1d = time_now - timedelta(hours=24)
    time_7d = time_now - timedelta(days=7)
    
    last_stat_ids = WgStatsRecord.objects.filter(client=OuterRef('client')).order_by('-stat_time').values('id')[:1]
    
    totals_1d = WgStatsRecord.objects.filter(client=OuterRef('client'), stat_time__lte=time_now, stat_time__gte=time_1d).values('client')
    totals_7d = WgStatsRecord.objects.filter(client=OuterRef('client'), stat_time__lte=time_now, stat_time__gte=time_7d).values('client')
    
    last_stats = WgStatsRecord.objects.filter(id__in=Subquery(last_stat_ids)).select_related('client').order_by('client__creation_date')
    last_stats = last_stats.annotate(
        transfer_rx_1d=Subquery(totals_1d.annotate(transfer_rx_1d=Sum('transfer_rx_delta')).values('transfer_rx_1d')),
        transfer_tx_1d=Subquery(totals_1d.annotate(transfer_tx_1d=Sum('transfer_tx_delta')).values('transfer_tx_1d')),
        seconds_1d=Subquery(totals_1d.annotate(seconds_1d=Sum('seconds_delta')).values('seconds_1d')),
        transfer_rx_7d=Subquery(totals_7d.annotate(transfer_rx_7d=Sum('transfer_rx_delta')).values('transfer_rx_7d')),
        transfer_tx_7d=Subquery(totals_7d.annotate(transfer_tx_7d=Sum('transfer_tx_delta')).values('transfer_tx_7d')),
        seconds_7d=Subquery(totals_7d.annotate(seconds_7d=Sum('seconds_delta')).values('seconds_7d')),
    )
    
    chart_clients = {}
    
    labels = []
    rx_1d = []
    tx_1d = []
    rx_7d = []
    tx_7d = []
    
    for ls in last_stats:
        labels.append(ls.client.client_name)
        rx_1d.append(round(ls.transfer_rx_1d/1000/1000))
        tx_1d.append(round(ls.transfer_tx_1d/1000/1000))
        rx_7d.append(round(ls.transfer_rx_7d/1000/1000))
        tx_7d.append(round(ls.transfer_tx_7d/1000/1000))
    
    chart_clients = {
        'labels': labels,
        'rx_1d': rx_1d,
        'tx_1d': tx_1d,
        'rx_7d': rx_7d,
        'tx_7d': tx_7d,
        'height': f'{50+len(labels)*40}px',
    }
    
    client = None
    client_stats_1d = None
    client_stats_7d = None
    client_chart_1d = {}
    client_chart_7d = {}
    
    client_id = request.GET.get('client_id', 0)
    
    if client_id:
        client = get_object_or_404(WgClient, pk=client_id)
        client_stats_1d = WgStatsRecord.objects.filter(client=client, stat_time__gte=time_1d).order_by('-stat_time')
        client_stats_7d = WgStatsRecord.objects.filter(
            client=client,
            stat_time__gte=time_7d
        ).annotate(
            stat_date=TruncDate('stat_time')
        ).values('stat_date').annotate(
            transfer_rx_delta=Sum('transfer_rx_delta'),
            transfer_tx_delta=Sum('transfer_tx_delta'),
            seconds_delta=Sum('seconds_delta')
        ).order_by('-stat_date')
        
        labels = []
        rx = []
        tx = []
        
        for cs in client_stats_1d:
            labels.append(cs.stat_time.strftime('%d.%m %H:%M'))
            rx.append(round(cs.transfer_rx_delta/1000/1000))
            tx.append(round(cs.transfer_tx_delta/1000/1000))
        
        client_chart_1d = {
            'labels': labels[::-1],
            'rx': rx[::-1],
            'tx': tx[::-1],
        }
        
        labels = []
        rx = []
        tx = []
        
        for cs in client_stats_7d:
            labels.append(cs['stat_date'].strftime('%d.%m'))
            rx.append(round(cs['transfer_rx_delta']/1000/1000))
            tx.append(round(cs['transfer_tx_delta']/1000/1000))
        
        client_chart_7d = {
            'labels': labels[::-1],
            'rx': rx[::-1],
            'tx': tx[::-1],
        }
            
    context = {
        'last_stats': last_stats,
        'chart_clients': chart_clients,
        'client': client,
        'client_stats_1d': client_stats_1d,
        'client_stats_7d': client_stats_7d,
        'client_chart_1d': client_chart_1d,
        'client_chart_7d': client_chart_7d,
    }
    
    return TemplateResponse(request, "main/stats.html", context)