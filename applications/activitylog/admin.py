from django.contrib import admin
from .models import ActivityLog

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp', 'is_deleted')
    list_filter = ('timestamp', 'is_deleted')
    search_fields = ('user__username', 'action')
    readonly_fields = ('timestamp',)