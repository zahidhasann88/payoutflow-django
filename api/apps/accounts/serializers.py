from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.creators.serializers import CreatorSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Public representation of a user — never exposes the password hash."""

    creator = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "name", "email", "role", "status",
            "created_at", "updated_at", "creator",
        ]
        read_only_fields = fields

    def get_creator(self, obj: User):
        profile = getattr(obj, "creator_profile", None)
        return CreatorSerializer(profile).data if profile else None


class LoginSerializer(TokenObtainPairSerializer):
    """
    Email + password login. Suspended accounts are rejected; successful
    logins are recorded in the audit log by the view.
    """

    username_field = "email"

    @classmethod
    def get_token(cls, user: User) -> RefreshToken:
        token = super().get_token(user)
        token["role"] = user.role
        token["name"] = user.name
        return token

    def validate(self, attrs):
        attrs[self.username_field] = (attrs.get(self.username_field) or "").strip().lower()
        data = super().validate(attrs)
        if self.user.status == User.Status.SUSPENDED:
            from apps.core.error_codes import ErrorCode
            from apps.core.exceptions import BusinessError

            raise BusinessError(
                "This account is suspended. Contact support.",
                code=ErrorCode.ACCOUNT_SUSPENDED,
                status_code=403,
            )
        data["user"] = UserSerializer(self.user).data
        return data


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Self-service profile update (name + optional password change)."""

    current_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["name", "current_password", "new_password"]

    def validate(self, attrs):
        new_password = attrs.get("new_password")
        current_password = attrs.pop("current_password", None)
        if new_password:
            user: User = self.context["request"].user
            if not current_password or not user.check_password(current_password):
                raise serializers.ValidationError(
                    {"current_password": "Current password is incorrect."}
                )
            validate_password(new_password, user)
            attrs["_new_password"] = new_password
        return attrs

    def update(self, instance: User, validated_data):
        new_password = validated_data.pop("_new_password", None)
        validated_data.pop("new_password", None)
        instance = super().update(instance, validated_data)
        if new_password:
            instance.set_password(new_password)
            instance.save(update_fields=["password", "updated_at"])
        return instance
