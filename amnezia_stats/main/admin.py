from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, WgClient


admin.site.register(User, UserAdmin)

@admin.register(WgClient)
class WgClientAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'container', 'client_id', 'creation_date', 'is_deleted')
    list_filter = ('container', 'is_deleted')
    search_fields = ('client_name', 'client_id')