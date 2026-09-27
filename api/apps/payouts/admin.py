from django.contrib import admin

from .models import CreatorPayout, PayoutBatch, PayoutRule


@admin.register(PayoutRule)
class PayoutRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "platform_fee_percentage", "minimum_payout",
                    "payout_frequency", "is_active")
    list_filter = ("is_active",)


class CreatorPayoutInline(admin.TabularInline):
    model = CreatorPayout
    extra = 0
    fields = ("creator", "gross_amount", "platform_fee", "adjustments",
              "net_amount", "status", "failure_reason")
    readonly_fields = fields


@admin.register(PayoutBatch)
class PayoutBatchAdmin(admin.ModelAdmin):
    list_display = ("period_start", "period_end", "creator_count",
                    "gross_amount", "platform_fee", "net_amount", "status")
    list_filter = ("status",)
    inlines = [CreatorPayoutInline]


@admin.register(CreatorPayout)
class CreatorPayoutAdmin(admin.ModelAdmin):
    list_display = ("creator", "payout_batch", "net_amount", "status", "processed_at")
    list_filter = ("status",)
