from django.db import models
from django.contrib.auth.models import AbstractUser

from .utils import bytes_to_hrs


# Create your models here.
class User(AbstractUser):
    def get_display_name(self):
        return self.get_full_name() or self.get_username()
    

class WgClient(models.Model):
    client_id = models.CharField(max_length=44, primary_key=True)
    client_name = models.CharField()
    creation_date = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.client_name} ({self.client_id})'
    
    
# <private_key>   <public_key>      <listen_port>   <fwmark>
# <public_key>                                  <preshared_key>                                 <endpoint>          <allowed_ips>   <latest_handshake_timestamp>   <transfer_rx>   <transfer_tx>   <persistent-keepalive> 
# h8GoAFxVOhx6ydeHyg1ZwSLQyXd5rSzkOtPwPGWxAmM=	Pxpa7pmimoAHxb1Ex5eD0iLr6Vynv2VaN0x02JMF9tU=	31.28.246.107:39426	10.8.1.3/32	    1765483039	                   213536	       408992	       off   
class WgStatsRecord(models.Model):
    client = models.ForeignKey(WgClient, on_delete=models.CASCADE)
    stat_time = models.DateTimeField()
    
    preshared_key = models.CharField(max_length=44)
    endpoint = models.CharField()
    allowed_ips = models.CharField()
    latest_handshake = models.DateTimeField(null=True, blank=True)
    transfer_rx = models.BigIntegerField(default=0)
    transfer_tx = models.BigIntegerField(default=0)
    persistent_keepalive = models.BooleanField(default=False)
    
    seconds_delta = models.IntegerField(null=True, blank=True)
    transfer_rx_delta = models.BigIntegerField(default=0)
    transfer_tx_delta = models.BigIntegerField(default=0)
    transfer_rx_avg = models.IntegerField(default=0) # Bps
    transfer_tx_avg = models.IntegerField(default=0) # Bps
    
    def __str__(self):
        return f'{self.client} - { self.stat_time.strftime('%Y-%m-%d %H:%M:%S') }'
    
    @property
    def transfer_rx_hrs(self):
        return bytes_to_hrs(self.transfer_rx)
    
    @property
    def transfer_tx_hrs(self):
        return bytes_to_hrs(self.transfer_tx)
    
    @property
    def transfer_rx_delta_hrs(self):
        return bytes_to_hrs(self.transfer_rx_delta)
    
    @property
    def transfer_tx_delta_hrs(self):
        return bytes_to_hrs(self.transfer_tx_delta)
    
    @property
    def transfer_rx_avg_hrs(self):
        return bytes_to_hrs(self.transfer_rx_avg)
    
    @property
    def transfer_tx_avg_hrs(self):
        return bytes_to_hrs(self.transfer_tx_avg)