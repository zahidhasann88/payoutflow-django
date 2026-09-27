from django_filters import rest_framework as df

from .models import Earning


class EarningFilter(df.FilterSet):
    created_after = df.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = df.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Earning
        fields = ["creator", "job", "payout_status", "payout", "created_after", "created_before"]
