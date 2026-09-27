from django_filters import rest_framework as df

from .models import Job


class JobFilter(df.FilterSet):
    completed_after = df.IsoDateTimeFilter(field_name="completed_at", lookup_expr="gte")
    completed_before = df.IsoDateTimeFilter(field_name="completed_at", lookup_expr="lte")
    min_amount = df.NumberFilter(field_name="base_amount", lookup_expr="gte")
    max_amount = df.NumberFilter(field_name="base_amount", lookup_expr="lte")

    class Meta:
        model = Job
        fields = ["creator", "status", "completed_after", "completed_before",
                  "min_amount", "max_amount"]
