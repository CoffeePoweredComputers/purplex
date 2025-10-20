"""
Simplified Celery configuration for Purplex.

This is a clean, minimal configuration that removes all the unnecessary
complexity from the original implementation.
"""

# CRITICAL: Import gevent_setup FIRST to enable monkey-patching
# This MUST happen before any other imports
from purplex.gevent_setup import *  # noqa: F401, F403

import os
from celery import Celery

# Set default Django settings module for Celery
# This will use the environment variable if it's already set (e.g., from start.sh)
# Otherwise falls back to the default settings
os.environ.setdefault('PURPLEX_ENV', 'development')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purplex.settings')

# Note: Django setup is handled differently to avoid circular imports
# django.setup() is called when the Celery worker starts, not during import

# Create Celery app instance
app = Celery('purplex')

# Configure Celery using Django settings
# All CELERY_* settings in settings.py will be read
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# CRITICAL: Patch psycopg2 for greenlet-aware database connections
# This makes PostgreSQL connections work properly with gevent greenlets
try:
    from psycogreen.gevent import patch_psycopg
    patch_psycopg()
    print("✓ psycopg2 patched with psycogreen for greenlet-aware DB connections")
except ImportError:
    print("⚠ psycogreen not installed - using gevent monkey-patch only")
    print("  Install with: pip install psycogreen")

# Minimal configuration - everything else goes in settings.py
app.conf.update(
    # Core settings
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    task_acks_late=True,
    worker_prefetch_multiplier=4,
    
    # Simple retry policy
    task_default_retry_delay=30,
    task_max_retries=3,
)

# Periodic tasks schedule
app.conf.beat_schedule = {
    'prune-orphaned-containers': {
        'task': 'cleanup.prune_orphaned_containers',
        'schedule': 3600.0,  # Every hour
    },
    'log-pool-metrics': {
        'task': 'cleanup.log_pool_metrics',
        'schedule': 900.0,  # Every 15 minutes
    },
}