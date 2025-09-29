"""
Health check endpoint for monitoring and load balancer health checks.
"""
from django.http import JsonResponse
from django.views import View
from django.core.cache import cache
from django.db import connection
import redis
import time
from django.conf import settings


class HealthCheckView(View):
    """Simple health check for load balancers."""

    def get(self, request):
        """Return 200 OK if service is healthy."""
        return JsonResponse({'status': 'healthy', 'service': 'purplex'})


class DetailedHealthCheckView(View):
    """Detailed health check for monitoring systems."""

    def get(self, request):
        """Check all critical dependencies and return detailed status."""
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'checks': {}
        }

        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            health_status['checks']['database'] = {
                'status': 'healthy',
                'message': 'Database connection successful'
            }
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['checks']['database'] = {
                'status': 'unhealthy',
                'message': str(e)
            }

        # Check Redis
        try:
            redis_url = settings.CELERY_BROKER_URL.replace('redis://', '')
            host, port = redis_url.split(':')
            r = redis.Redis(host=host, port=int(port), socket_connect_timeout=1)
            r.ping()
            health_status['checks']['redis'] = {
                'status': 'healthy',
                'message': 'Redis connection successful'
            }
        except Exception as e:
            health_status['status'] = 'degraded'  # Redis failure is less critical
            health_status['checks']['redis'] = {
                'status': 'unhealthy',
                'message': str(e)
            }

        # Check cache
        try:
            cache.set('health_check', 'ok', 1)
            if cache.get('health_check') == 'ok':
                health_status['checks']['cache'] = {
                    'status': 'healthy',
                    'message': 'Cache working'
                }
            else:
                raise Exception('Cache write/read failed')
        except Exception as e:
            health_status['status'] = 'degraded'
            health_status['checks']['cache'] = {
                'status': 'unhealthy',
                'message': str(e)
            }

        # Determine HTTP status code
        if health_status['status'] == 'healthy':
            status_code = 200
        elif health_status['status'] == 'degraded':
            status_code = 200  # Still return 200 for degraded (non-critical failures)
        else:
            status_code = 503  # Service unavailable

        return JsonResponse(health_status, status=status_code)