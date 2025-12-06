"""
Django management command to clear rate limits for IP addresses.
Useful for development and debugging authentication issues.
"""

from django.core.management.base import BaseCommand
from purplex.users_app.services.rate_limit_service import RateLimitService


class Command(BaseCommand):
    help = 'Clear rate limits for specific IP addresses or all rate limits'

    def add_arguments(self, parser):
        parser.add_argument(
            'ip_addresses',
            nargs='*',
            type=str,
            help='IP addresses to clear rate limits for (optional)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Clear all rate limits (use with caution)'
        )

    def handle(self, *args, **options):
        if options['all']:
            self._clear_all_rate_limits()
        elif options['ip_addresses']:
            for ip in options['ip_addresses']:
                self._clear_ip_rate_limit(ip)
        else:
            # Default to clearing localhost if no arguments
            self._clear_ip_rate_limit('127.0.0.1')
            self._clear_ip_rate_limit('localhost')

    def _clear_ip_rate_limit(self, ip_address):
        """Clear rate limits for a specific IP address."""
        try:
            RateLimitService.reset_limits(ip_address)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleared rate limits for {ip_address}')
            )
            
            # Also clear any active rate limit keys
            redis_client = RateLimitService._get_redis_client()
            
            # Clear per-minute and per-hour rate limit keys
            pattern_keys = [
                f"auth_limit:minute:{ip_address}:*",
                f"auth_limit:hour:{ip_address}:*",
                f"service_auth_limit:{ip_address}:*"
            ]
            
            for pattern in pattern_keys:
                for key in redis_client.scan_iter(match=pattern):
                    redis_client.delete(key)
                    self.stdout.write(
                        self.style.SUCCESS(f'  Deleted key: {key}')
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error clearing rate limits for {ip_address}: {e}')
            )

    def _clear_all_rate_limits(self):
        """Clear all rate limits from Redis."""
        try:
            redis_client = RateLimitService._get_redis_client()
            
            # Pattern for all rate limit keys
            patterns = [
                "auth_failures:*",
                "auth_limit:*",
                "service_auth_limit:*",
                "sse_token_limit:*"
            ]
            
            total_deleted = 0
            for pattern in patterns:
                for key in redis_client.scan_iter(match=pattern):
                    redis_client.delete(key)
                    total_deleted += 1
                    self.stdout.write(self.style.WARNING(f'  Deleted: {key}'))
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleared {total_deleted} rate limit keys')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error clearing all rate limits: {e}')
            )