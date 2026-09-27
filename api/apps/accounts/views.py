from __future__ import annotations

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.audit.services import AuditAction, record_audit
from apps.core.error_codes import ErrorCode
from apps.core.exceptions import BusinessError

from .serializers import LoginSerializer, ProfileUpdateSerializer, UserSerializer

logger = logging.getLogger("payoutflow.auth")


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ — rate limited (scope: ``login``)."""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, AuthenticationFailed) as exc:
            logger.warning(
                "Failed login attempt for email=%s ip=%s",
                request.data.get("email"),
                request.META.get("REMOTE_ADDR"),
            )
            raise BusinessError(
                "Invalid email or password.",
                code=ErrorCode.INVALID_CREDENTIALS,
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from exc
        record_audit(serializer.user, AuditAction.LOGIN, entity_type="User",
                     entity_id=str(serializer.user.id))
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RefreshView(TokenRefreshView):
    """POST /api/auth/refresh/ — rotates the refresh token."""

    permission_classes = [AllowAny]
    throttle_scope = "login"


@extend_schema(request=OpenApiTypes.NONE, responses=OpenApiTypes.OBJECT, tags=["auth"])
class LogoutView(APIView):
    """
    POST /api/auth/logout/

    Revokes the refresh token so logout is not merely cosmetic. Pass ``refresh``
    to revoke that one session; omit it and every outstanding refresh token for
    the user is revoked, which is the only option open to a client that cannot
    read its own HttpOnly cookie.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        presented = (request.data or {}).get("refresh")
        if presented:
            try:
                RefreshToken(presented).blacklist()
                revoked = 1
            except TokenError:
                revoked = 0
        else:
            revoked = 0
            for outstanding in OutstandingToken.objects.filter(user=request.user):
                _, created = BlacklistedToken.objects.get_or_create(token=outstanding)
                revoked += int(created)

        record_audit(request.user, AuditAction.LOGOUT, entity_type="User",
                     entity_id=str(request.user.id),
                     metadata={"scope": "session" if presented else "all_sessions"})
        return Response({"success": True, "message": "Logged out.",
                         "data": {"revoked_tokens": revoked}})


@extend_schema_view(
    get=extend_schema(responses=OpenApiTypes.OBJECT),
    patch=extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT),
)
class MeView(APIView):
    """GET/PATCH /api/auth/me/ — current user profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"success": True, "data": UserSerializer(request.user).data})

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        record_audit(user, AuditAction.USER_UPDATED, entity_type="User",
                     entity_id=str(user.id), metadata={"fields": list(request.data.keys())})
        return Response({"success": True, "data": UserSerializer(user).data})
