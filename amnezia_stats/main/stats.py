import os, json
from datetime import datetime, timezone, timedelta

from django.db import transaction

from config.settings import STATS_DIR, SERVER_TIME_ZONE_OFFSET, AMNEZIA_MAIN_CLIENT_TIME_ZONE_OFFSET
from .models import WgClient, WgStatsRecord


SERVER_TZ = timezone(timedelta(hours=SERVER_TIME_ZONE_OFFSET))
AMNEZIA_TZ = timezone(timedelta(hours=AMNEZIA_MAIN_CLIENT_TIME_ZONE_OFFSET))


def get_files_list(dirpath, pattern = None) -> list[str]:
    filenames =  [f for f in os.listdir(dirpath) if os.path.isfile(os.path.join(dirpath, f))]
    
    if pattern:
        import fnmatch
        filenames = [f for f in filenames if fnmatch.fnmatch(f, pattern)]
    
    filenames.sort()
    
    return filenames


def read_file_content(dirpath, filename) -> str | None:
    filepath = os.path.join(dirpath, filename)
    try:
        with open(filepath) as file:
            content = file.read()
            return content
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        return None
    except PermissionError:
        print(f"Error: Permission denied for '{filepath}'.")
        return None
    except UnicodeDecodeError as e:
        print(f"Error: Could not decode file '{filepath}'. {e}")
        return None
    except Exception as e:
        print(f"Unexpected error reading '{filepath}': {e}")
        return None


def process_wg_clients():
    """Update clients in DB"""
    
    clients_file_content = read_file_content(STATS_DIR, 'clientsTable.txt')
    
    if not clients_file_content:
        raise RuntimeError('Failed to retrieve clients list!')
    
    clients_list = json.loads(clients_file_content)
    
    with transaction.atomic():
        
        WgClient.objects.update(is_deleted=True)
    
        for client_dict in clients_list:
            try:
                client = WgClient.objects.get(pk=client_dict['clientId'])
            except:
                client = WgClient()
                client.client_id = client_dict['clientId']

            client.client_name = client_dict['userData']['clientName']
            
            # "Thu Dec 11 21:41:03 2025"
            # "%a %b %d %H:%M:%S %Y"
            client.creation_date = datetime.strptime(client_dict['userData']['creationDate'], '%a %b %d %H:%M:%S %Y').replace(tzinfo=AMNEZIA_TZ)

            client.is_deleted = False
            
            client.save()
    


def process_wg_stats_files():
    DUMP_KEYS = ['public_key', 'preshared_key', 'endpoint', 'allowed_ips', 'latest_handshake_timestamp', 'transfer_rx', 'transfer_tx', 'persistent-keepalive']
    
    filenames = get_files_list(STATS_DIR, 'wg-stats-*.txt')
    
    if not filenames:
        return 0
    
    process_wg_clients()
    
    prev_stats = {}
    
    for f in filenames:
        
        print(f'Processing file: {f}')
        
        filename_time = f.replace('wg-stats-', '').replace('.txt', '') # wg-stats-2025-12-11_19-57-53.txt
        stat_time = datetime.strptime(filename_time, '%Y-%m-%d_%H-%M-%S').replace(tzinfo=SERVER_TZ)
        
        file_content = read_file_content(STATS_DIR, f)
        lines = file_content.splitlines()[1:]
        for line in lines:
            # <public_key> <preshared_key> <endpoint> <allowed_ips> <latest_handshake_timestamp> <transfer_rx> <transfer_tx> <persistent-keepalive>
            stat_vals = dict(zip(DUMP_KEYS, line.split('\t')))
            
            try:
                client = WgClient.objects.get(pk=stat_vals['public_key'])
            except:
                client = WgClient()
                client.client_id = stat_vals['public_key']
                client.client_name = 'UNKNOWN'
                client.save()
            
            try:
                stats_record = WgStatsRecord.objects.get(client=client, stat_time=stat_time)
                print(f'Updating existing stats record: {stats_record}')
                stats_record.seconds_delta = None
                stats_record.transfer_rx_delta = 0
                stats_record.transfer_tx_delta = 0
                stats_record.transfer_rx_avg = 0
                stats_record.transfer_tx_avg = 0
            except:
                stats_record = WgStatsRecord()
                stats_record.client = client
                stats_record.stat_time = stat_time
            
            stats_record.preshared_key = stat_vals['preshared_key']
            stats_record.endpoint = stat_vals['endpoint']
            stats_record.allowed_ips = stat_vals['allowed_ips']
            stats_record.latest_handshake = datetime.fromtimestamp(int(stat_vals['latest_handshake_timestamp'])).replace(tzinfo=AMNEZIA_TZ) if int(stat_vals['latest_handshake_timestamp']) else None
            stats_record.transfer_rx = int(stat_vals['transfer_rx'])
            stats_record.transfer_tx = int(stat_vals['transfer_tx'])
            stats_record.persistent_keepalive = stat_vals['persistent-keepalive'] != 'off'
            
            if client.client_id in prev_stats:
                prev_stat = prev_stats[client.client_id]
            else:
                prev_stat = WgStatsRecord.objects.filter(client=client, stat_time__lt=stat_time).order_by('-stat_time').first()
            
            if prev_stat is not None:
                stats_record.seconds_delta = (stats_record.stat_time - prev_stat.stat_time).total_seconds()
                stats_record.transfer_rx_delta = stats_record.transfer_rx - prev_stat.transfer_rx if prev_stat.transfer_rx <= stats_record.transfer_rx else stats_record.transfer_rx
                stats_record.transfer_tx_delta = stats_record.transfer_tx - prev_stat.transfer_tx if prev_stat.transfer_tx <= stats_record.transfer_tx else stats_record.transfer_tx
                if stats_record.seconds_delta:
                    stats_record.transfer_rx_avg = round(stats_record.transfer_rx_delta / stats_record.seconds_delta)
                    stats_record.transfer_tx_avg = round(stats_record.transfer_tx_delta / stats_record.seconds_delta)
            
            stats_record.save()
            prev_stats[client.client_id] = stats_record
            
        os.rename(os.path.join(STATS_DIR, f), os.path.join(STATS_DIR, 'processed', f))
            
    return len(filenames)