from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "creator", "status", "base_amount", "surge_multiplier",
                    "tip_amount", "completed_at")
    list_filter = ("status",)
    search_fields = ("title", "creator__display_name")
