from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "user", "entity_type", "entity_id")
    list_filter = ("action", "entity_type")
    search_fields = ("user__email", "entity_id")
    readonly_fields = [f.name for f in AuditLog._meta.fields]
