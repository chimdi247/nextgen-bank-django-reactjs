from django.core.cache import cache
from django.db import connection
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness + readiness for docker healthchecks and the blackbox uptime probe. No auth, never throttled."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        checks = {}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
        try:
            cache.set("health:ping", "1", 10)
            checks["cache"] = "ok" if cache.get("health:ping") == "1" else "degraded"
        except Exception:
            checks["cache"] = "degraded"
        healthy = checks["database"] == "ok"  # a cache outage degrades, it does not make the API unavailable
        return Response(
            {"status": "ok" if healthy else "unavailable", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
