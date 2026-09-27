from django.contrib import admin

from .models import Creator


@admin.register(Creator)
class CreatorAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "payout_method", "tax_status", "minimum_payout")
    list_filter = ("payout_method", "tax_status")
    search_fields = ("display_name", "user__email")
