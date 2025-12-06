"""
Django management command to show Docker container pool status.

Usage:
    python manage.py pool_status              # One-time check
    python manage.py pool_status --watch      # Continuous monitoring (refresh every 5s)
    python manage.py pool_status --json       # JSON output for scripts
"""

from django.core.management.base import BaseCommand
import time
import json
import sys

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

try:
    import psutil  # noqa: F401 - availability check pattern
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class Command(BaseCommand):
    help = 'Show Docker container pool status and health metrics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Refresh every 5 seconds (press Ctrl+C to exit)',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output as JSON',
        )
        parser.add_argument(
            '--compact',
            action='store_true',
            help='Compact output (one line)',
        )

    def handle(self, *args, **options):
        if not DOCKER_AVAILABLE:
            self.stdout.write(self.style.ERROR('Docker SDK not available. Install: pip install docker'))
            return

        watch_mode = options['watch']
        json_output = options['json']
        compact = options['compact']

        if watch_mode:
            try:
                while True:
                    self.show_status(json_output, compact)
                    if not json_output and not compact:
                        self.stdout.write("\n(Press Ctrl+C to exit)\n")
                    time.sleep(5)
            except KeyboardInterrupt:
                self.stdout.write("\nMonitoring stopped.")
                sys.exit(0)
        else:
            self.show_status(json_output, compact)

    def show_status(self, json_output=False, compact=False):
        """Collect and display pool status"""
        try:
            client = docker.from_env()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to connect to Docker: {e}'))
            return

        # Get all sandbox containers
        try:
            all_containers = client.containers.list(
                filters={'ancestor': 'purplex/python-sandbox:latest'}
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to list containers: {e}'))
            return

        # Get pool containers (labeled)
        pool_containers = [c for c in all_containers if c.labels.get('purplex-pool') == 'true']

        total = len(all_containers)
        pool = len(pool_containers)
        orphans = total - pool

        # Get service metrics from shared service if available
        metrics = {}
        try:
            from purplex.problems_app.services.docker_execution_service import SharedDockerServiceContext
            with SharedDockerServiceContext() as service:
                metrics = service.get_pool_metrics()
        except Exception:
            # Service not available or failed - that's okay
            pass

        # Memory info
        if PSUTIL_AVAILABLE:
            import psutil
            mem = psutil.virtual_memory()
            mem_info = {
                'free_gb': round(mem.available / (1024**3), 2),
                'used_gb': round(mem.used / (1024**3), 2),
                'percent': mem.percent,
            }
        else:
            mem_info = {'error': 'psutil not available'}

        # Container ages
        container_ages = []
        for container in all_containers:
            try:
                # Get container age
                created = container.attrs['Created']
                container_ages.append(created)
            except:
                pass

        # Determine health status
        if orphans > 10 or total > 30:
            health = 'CRITICAL'
        elif orphans > 0 or total > 20:
            health = 'WARNING'
        else:
            health = 'HEALTHY'

        status_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'containers': {
                'total': total,
                'pool': pool,
                'orphaned': orphans,
                'max_allowed': metrics.get('pool_max_size', 30),
            },
            'metrics': metrics,
            'memory': mem_info,
            'health': health
        }

        if json_output:
            self.stdout.write(json.dumps(status_data, indent=2))
        elif compact:
            self.print_compact(status_data)
        else:
            self.print_formatted(status_data)

    def print_compact(self, data):
        """Print one-line compact status"""
        containers = data['containers']
        mem = data['memory']
        health_symbol = '✅' if data['health'] == 'HEALTHY' else '⚠️' if data['health'] == 'WARNING' else '🚨'

        mem_str = f"{mem.get('free_gb', '?')}GB free" if 'free_gb' in mem else 'mem: N/A'

        self.stdout.write(
            f"{data['timestamp']} | {health_symbol} {data['health']} | "
            f"containers: {containers['total']} (pool: {containers['pool']}, orphans: {containers['orphaned']}) | "
            f"{mem_str}"
        )

    def print_formatted(self, data):
        """Print full formatted status"""
        # Clear screen for watch mode
        self.stdout.write("\033[2J\033[H")

        self.stdout.write(self.style.SUCCESS("=== Docker Container Pool Status ==="))
        self.stdout.write(f"Time: {data['timestamp']}\n")

        containers = data['containers']
        metrics = data['metrics']
        mem = data['memory']

        self.stdout.write(self.style.HTTP_INFO("CONTAINERS:"))
        self.stdout.write(f"  Total running:         {containers['total']} containers")
        self.stdout.write(f"  Pool (warm):           {containers['pool']} containers")

        orphan_status = '✅' if containers['orphaned'] == 0 else '⚠️'
        orphan_style = self.style.SUCCESS if containers['orphaned'] == 0 else self.style.WARNING
        self.stdout.write(f"  Orphaned:              {orphan_style(str(containers['orphaned']))} containers {orphan_status}")
        self.stdout.write(f"  Max allowed:           {containers['max_allowed']} containers\n")

        # Pool metrics if available
        if metrics:
            self.stdout.write(self.style.HTTP_INFO("POOL HEALTH:"))
            pool_size = metrics.get('pool_size', 0)
            pool_max = metrics.get('pool_max_size', 30)

            if pool_max > 0:
                utilization = (pool_max - pool_size) / pool_max * 100
                self.stdout.write(f"  Pool utilization:      {utilization:.1f}% ({pool_max - pool_size}/{pool_max} in use)")

            total_created = metrics.get('total_created', 0)
            if total_created > 0:
                self.stdout.write(f"  Containers created:    {total_created}")
                self.stdout.write(f"  Containers removed:    {metrics.get('total_removed', 0)}")

            health_checks = metrics.get('health_checks_performed', 0)
            if health_checks > 0:
                self.stdout.write(f"  Health checks:         {health_checks}")
                self.stdout.write(f"  Unhealthy removed:     {metrics.get('unhealthy_containers_removed', 0)}")

            self.stdout.write("")

        # Memory info
        if 'free_gb' in mem:
            self.stdout.write(self.style.HTTP_INFO("MEMORY:"))
            self.stdout.write(f"  System free:           {mem['free_gb']} GB")
            self.stdout.write(f"  System used:           {mem['used_gb']} GB")

            mem_status = '✅' if mem['percent'] < 75 else '⚠️'
            mem_style = self.style.SUCCESS if mem['percent'] < 75 else self.style.WARNING
            mem_percent = f"{mem['percent']}%"
            self.stdout.write(f"  Usage:                 {mem_style(mem_percent)} {mem_status}\n")

        # Overall status
        status_style = {
            'HEALTHY': self.style.SUCCESS,
            'WARNING': self.style.WARNING,
            'CRITICAL': self.style.ERROR,
        }.get(data['health'], self.style.NOTICE)

        status_symbol = {
            'HEALTHY': '✅',
            'WARNING': '⚠️',
            'CRITICAL': '🚨',
        }.get(data['health'], '?')

        self.stdout.write(f"STATUS: {status_style(data['health'])} {status_symbol}")
