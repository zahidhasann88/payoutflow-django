from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User

from .models import Creator


class CreatorSerializer(serializers.ModelSerializer):
    """Read representation of a creator profile + linked user info."""

    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    status = serializers.CharField(source="user.status", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = Creator
        fields = [
            "id", "user", "email", "name", "status", "role",
            "display_name", "phone", "payout_method", "payout_account",
            "tax_status", "minimum_payout", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]
        extra_kwargs = {"payout_account": {"write_only": False}}


class CreatorCreateSerializer(serializers.Serializer):
    """Admin creates a creator: user credentials + profile in one payload."""

    email = serializers.EmailField()
    name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    display_name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    payout_method = serializers.ChoiceField(choices=Creator.PayoutMethod.choices, required=False)
    payout_account = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )
    tax_status = serializers.ChoiceField(choices=Creator.TaxStatus.choices, required=False)
    minimum_payout = serializers.DecimalField(max_digits=12, decimal_places=2, required=False,
                                              allow_null=True, min_value=0)

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        from .models import Creator as CreatorModel

        phone = attrs.get("phone", "")
        if phone:
            field = CreatorModel._meta.get_field("phone")
            for validator in field.validators:
                validator(phone)
        return attrs

    @property
    def profile_fields(self):
        keys = ["display_name", "phone", "payout_method", "payout_account",
                "tax_status", "minimum_payout"]
        return {k: v for k, v in self.validated_data.items() if k in keys}


class CreatorUpdateSerializer(serializers.Serializer):
    """Admin/self update — all fields optional."""

    name = serializers.CharField(max_length=150, required=False)
    status = serializers.ChoiceField(choices=User.Status.choices, required=False)
    display_name = serializers.CharField(max_length=120, required=False)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    payout_method = serializers.ChoiceField(choices=Creator.PayoutMethod.choices, required=False)
    payout_account = serializers.CharField(max_length=120, required=False, allow_blank=True)
    tax_status = serializers.ChoiceField(choices=Creator.TaxStatus.choices, required=False)
    minimum_payout = serializers.DecimalField(max_digits=12, decimal_places=2, required=False,
                                              allow_null=True, min_value=0)

    @property
    def profile_fields(self):
        keys = ["display_name", "phone", "payout_method", "payout_account",
                "tax_status", "minimum_payout"]
        return {k: v for k, v in self.validated_data.items() if k in keys}

    @property
    def user_fields(self):
        keys = ["name", "status"]
        return {k: v for k, v in self.validated_data.items() if k in keys}
