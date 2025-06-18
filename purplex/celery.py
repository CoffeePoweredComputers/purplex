"""
Celery configuration for Purplex
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purplex.settings')

# Create Celery instance
app = Celery('purplex')

# Configure Celery from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Configure task routing for different queues
app.conf.task_routes = {
    'problems_app.tasks.execute_code_async': {'queue': 'code_execution'},
    'problems_app.tasks.generate_ai_content_async': {'queue': 'ai_generation'},
    'problems_app.tasks.update_user_progress_async': {'queue': 'progress_updates'},
    'problems_app.tasks.cleanup_docker_containers': {'queue': 'maintenance'},
}

# Configure queue priorities
app.conf.task_queue_max_priority = 10
app.conf.task_default_priority = 5

# Task execution limits
app.conf.task_annotations = {
    'problems_app.tasks.execute_code_async': {
        'rate_limit': '100/m',  # 100 executions per minute
        'time_limit': 30,  # 30 seconds hard limit
        'soft_time_limit': 25,  # 25 seconds soft limit
    },
    'problems_app.tasks.generate_ai_content_async': {
        'rate_limit': '50/m',  # 50 AI generations per minute
        'time_limit': 60,
        'soft_time_limit': 50,
    },
}

# Beat schedule for periodic tasks
from celery.schedules import crontab

app.conf.beat_schedule = {
    'cleanup-docker-containers': {
        'task': 'problems_app.tasks.cleanup_docker_containers',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'update-progress-cache': {
        'task': 'problems_app.tasks.update_progress_cache',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'generate-progress-snapshots': {
        'task': 'problems_app.tasks.generate_progress_snapshots',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')