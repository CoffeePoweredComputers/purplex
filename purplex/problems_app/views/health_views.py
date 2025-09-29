"""
Health check endpoint for container orchestration and monitoring.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health check endpoint for container orchestration.
    Checks database and cache connectivity.
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
            'checks': {}
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

        # Return appropriate status code based on health
        status_code = (
            status.HTTP_200_OK
            if health_status['status'] == 'healthy'
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return Response(health_status, status=status_code)