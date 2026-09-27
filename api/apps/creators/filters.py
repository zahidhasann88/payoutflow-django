from django_filters import rest_framework as df

from .models import Creator


class CreatorFilter(df.FilterSet):
    class Meta:
        model = Creator
        fields = ["payout_method", "tax_status"]
