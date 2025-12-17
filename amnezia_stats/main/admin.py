from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, WgClient


admin.site.register(User, UserAdmin)

@admin.register(WgClient)
class WgClientAdmin(admin.ModelAdmin):
    pass