"""
Health check endpoint for container orchestration and monitoring.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
from celery import current_app
import logging

logger = logging.getLogger(__name__)

# Try to import sentry_sdk, but don't fail if not configured
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


class HealthCheckView(APIView):
    """
    Health check endpoint for container orchestration.
    Checks database, cache, and Celery connectivity.
    """
    authentication_classes = []  # No authentication required for health checks
    permission_classes = []  # No permissions required for health checks

    def get(self, request):
        """
        Perform health checks on critical services.

        Returns:
            Response with health status and individual service checks.
        """
        health_status = {
            'status': 'healthy',
            'checks': {},
            'version': request.GET.get('v', '1')  # Support versioning
        }

        # Check database connectivity
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            health_status['checks']['database'] = 'ok'
        except Exception as e:
            logger.error(f"Health check - Database failed: {e}")
            health_status['checks']['database'] = 'failed'
            health_status['status'] = 'unhealthy'
            # Report to Sentry with low severity
            if SENTRY_AVAILABLE:
                sentry_sdk.capture_message(
                    "Health check: Database connectivity failed",
                    level="warning"
                )

        # Check cache connectivity
        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') == 'ok':
                health_status['checks']['cache'] = 'ok'
                cache.delete('health_check')
            else:
                health_status['checks']['cache'] = 'failed'
                health_status['status'] = 'unhealthy'
        except Exception as e:
            logger.error(f"Health check - Cache failed: {e}")
            health_status['checks']['cache'] = 'failed'
            health_status['status'] = 'unhealthy'
            if SENTRY_AVAILABLE:
                sentry_sdk.capture_message(
                    "Health check: Cache connectivity failed",
                    level="warning"
                )

        # Check Celery connectivity (optional - don't fail health check)
        try:
            # Ping Celery workers
            inspect = current_app.control.inspect()
            active_workers = inspect.active()

            if active_workers:
                health_status['checks']['celery'] = 'ok'
                health_status['checks']['celery_workers'] = len(active_workers)
            else:
                health_status['checks']['celery'] = 'degraded'
                health_status['checks']['celery_workers'] = 0
                # Don't fail overall health, but log warning
                logger.warning("Health check - No active Celery workers found")

        except Exception as e:
            logger.error(f"Health check - Celery check failed: {e}")
            health_status['checks']['celery'] = 'unknown'
            # Don't fail health check for Celery issues

        # Return appropriate status code based on health
        status_code = (
            status.HTTP_200_OK
            if health_status['status'] == 'healthy'
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return Response(health_status, status=status_code)


class ReadinessCheckView(APIView):
    """
    Readiness check for Kubernetes-style orchestration.
    Returns 200 only if ready to accept traffic.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """Check if application is ready to serve traffic."""
        # Quick check - just verify we can respond
        # More thorough checks can be added as needed
        return Response({'status': 'ready'}, status=status.HTTP_200_OK)


class LivenessCheckView(APIView):
    """
    Liveness check for Kubernetes-style orchestration.
    Returns 200 if application is alive (not deadlocked).
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """Check if application is alive."""
        return Response({'status': 'alive'}, status=status.HTTP_200_OK)