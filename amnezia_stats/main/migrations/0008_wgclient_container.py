# Backfills existing clients with the first container from AMNEZIA_CONTAINERS

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_remove_wgstatsrecord_previous_stat_time_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='wgclient',
            name='container',
            field=models.CharField(db_index=True, default=getattr(settings, 'AMNEZIA_DEFAULT_CONTAINER', 'amnezia-awg'), max_length=64),
        ),
    ]
