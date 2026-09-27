from django.db import connection
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(responses=OpenApiTypes.OBJECT, tags=["meta"])
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """
    Readiness probe for Docker / infrastructure.

    Verifies the database round-trips, because the container is only useful if it
    can serve queries. Returns 503 otherwise, so the Dockerfile HEALTHCHECK and
    Compose's ``condition: service_healthy`` gate on something real.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return Response(
            {"success": False, "status": "unavailable", "service": "payoutflow-api",
             "database": "unreachable"},
            status=503,
        )
    return Response({"success": True, "status": "ok", "service": "payoutflow-api",
                     "database": "ok"})
