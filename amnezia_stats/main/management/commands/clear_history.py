from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...models import WgClient, WgStatsRecord


class Command(BaseCommand):
    help = (
        'Deletes WgStatsRecord elements older than the specified number of days '
        'and then removes WgClient elements that have no stats records left.'
    )
    
    def add_arguments(self, parser):
        parser.add_argument(
            'days',
            type=int,
            help='Delete WgStatsRecord elements older than this number of days (0 - delete all records).',
        )
        
    def handle(self, *args, **options):
        days = options['days']
        if days < 0:
            raise CommandError('Number of days must be 0 or greater.')
        
        if days == 0:
            deleted_records_count = WgStatsRecord.objects.all().delete()[0]
        else:
            cutoff_time = timezone.now() - timedelta(days=days)
            deleted_records_count = WgStatsRecord.objects.filter(stat_time__lt=cutoff_time).delete()[0]
        
        self.stdout.write(f'Deleted {deleted_records_count} stats records.')
        
        deleted_clients_count = WgClient.objects.filter(wgstatsrecord__isnull=True).delete()[0]
        
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_clients_count} clients with no stats records left.'))
        return f'Deleted {deleted_records_count} stats records and {deleted_clients_count} clients with no stats records left.'
