from django_filters import rest_framework as df

from .models import CreatorPayout, PayoutBatch


class PayoutBatchFilter(df.FilterSet):
    period_start_after = df.DateFilter(field_name="period_start", lookup_expr="gte")
    period_end_before = df.DateFilter(field_name="period_end", lookup_expr="lte")

    class Meta:
        model = PayoutBatch
        fields = ["status", "period_start_after", "period_end_before"]


class CreatorPayoutFilter(df.FilterSet):
    class Meta:
        model = CreatorPayout
        fields = ["status", "payout_batch", "creator"]
