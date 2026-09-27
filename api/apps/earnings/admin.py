from django.contrib import admin

from .models import Adjustment, Earning


@admin.register(Earning)
class EarningAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "creator", "gross_amount", "platform_fee",
                    "net_amount", "payout_status")
    list_filter = ("payout_status",)
    search_fields = ("job__title", "creator__display_name")


@admin.register(Adjustment)
class AdjustmentAdmin(admin.ModelAdmin):
    list_display = ("id", "earning", "amount", "reason", "created_by", "created_at")
