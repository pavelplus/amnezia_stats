from django.core.management.base import BaseCommand

from ...stats import process_wg_stats_files


class Command(BaseCommand):
    help = "Processes statistics files collected by cron task"
    
    def handle(self, *args, **options):
        num_files = process_wg_stats_files()
        return f'Processed {num_files} statistics files.'