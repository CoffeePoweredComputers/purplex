"""
Production-optimized Celery configuration.
"""
import os
from celery import Celery
from kombu import Queue, Exchange

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purplex.settings')

app = Celery('purplex')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Production-optimized settings
app.conf.update(
    # Performance optimizations
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Worker configuration
    worker_prefetch_multiplier=4,  # Prefetch more tasks for better throughput
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks to prevent memory leaks
    worker_disable_rate_limits=False,

    # Task execution limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit

    # Result backend optimization
    result_expires=3600,  # Results expire after 1 hour
    result_compression='gzip',  # Compress results

    # Task routing for different priorities
    task_routes={
        'purplex.problems_app.tasks.pipeline.execute_eipl_pipeline': {
            'queue': 'ai_generation',
            'routing_key': 'ai.generation',
        },
        'purplex.problems_app.tasks.pipeline.execute_code': {
            'queue': 'code_execution',
            'routing_key': 'code.execution',
        },
        'purplex.problems_app.tasks.progress.*': {
            'queue': 'progress_updates',
            'routing_key': 'progress.update',
        },
    },

    # Queue configuration
    task_default_queue='default',
    task_default_exchange='default',
    task_default_exchange_type='direct',
    task_default_routing_key='default',

    # Define queues with different priorities
    task_queues=(
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('code_execution', Exchange('code_execution'), routing_key='code.execution',
              queue_arguments={'x-max-priority': 10}),
        Queue('ai_generation', Exchange('ai_generation'), routing_key='ai.generation',
              queue_arguments={'x-max-priority': 5}),
        Queue('progress_updates', Exchange('progress_updates'), routing_key='progress.update',
              queue_arguments={'x-max-priority': 3}),
    ),

    # Task acknowledgment
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Reject task if worker dies

    # Monitoring
    worker_send_task_events=True,  # Send task events for monitoring
    task_send_sent_event=True,  # Include sent events

    # Connection pooling
    broker_pool_limit=50,  # Connection pool size
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,

    # Result backend pooling
    result_backend_pool_limit=50,
)

# Auto-discover tasks from all registered Django app configs.
app.autodiscover_tasks()

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'cleanup-old-submissions': {
        'task': 'purplex.problems_app.tasks.cleanup.cleanup_old_submissions',
        'schedule': 86400.0,  # Daily
    },
    'update-progress-snapshots': {
        'task': 'purplex.problems_app.tasks.progress.create_progress_snapshots',
        'schedule': 3600.0,  # Hourly
    },
    'health-check-docker-pool': {
        'task': 'purplex.problems_app.tasks.monitoring.check_docker_pool_health',
        'schedule': 300.0,  # Every 5 minutes
    },
}