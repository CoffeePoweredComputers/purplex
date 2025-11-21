"""
Clean Celery signal handlers for SSE updates.

This provides real-time task status updates via Redis pub/sub,
but in a simple, decoupled way.
"""

import json
import time
import redis
import logging
from celery.signals import (
    task_prerun,
    task_postrun,
    task_failure,
    task_retry,
    task_success
)
from django.conf import settings
from purplex.utils.redis_client import get_pubsub_client

logger = logging.getLogger(__name__)


def publish_task_event(task_id: str, event_type: str, data: dict = None):
    """
    Publish a task event to Redis pub/sub.
    
    Args:
        task_id: Celery task ID
        event_type: Type of event (started, progress, completed, failed)
        data: Additional event data
    """
    # Map event types to status values expected by frontend
    status_map = {
        'started': 'processing',
        'progress': 'processing', 
        'completed': 'completed',
        'failed': 'failed',
        'retrying': 'retrying'
    }
    
    event = {
        'task_id': task_id,
        'type': event_type,
        'status': status_map.get(event_type, event_type),  # Frontend expects 'status' field
        'timestamp': time.time(),
        **(data or {})
    }
    
    # For completed events with results, ensure frontend-compatible structure
    if event_type == 'completed' and 'result' in event:
        # The result should already have the right structure from save_submission
        pass
    
    # Publish to task-specific channel
    channel = f'task:{task_id}'
    
    try:
        client = get_pubsub_client()  # Use centralized client
        client.publish(channel, json.dumps(event))
        logger.debug(f"Published {event_type} event for task {task_id}")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        # Don't fail tasks if Redis is temporarily unavailable
        logger.warning(f"⚠️ Redis connection failed while publishing event for task {task_id}: {e}")
    except Exception as e:
        # Don't fail tasks if publishing fails for other reasons (serialization, etc.)
        logger.warning(f"Failed to publish event for task {task_id}: {e}")


@task_prerun.connect
def task_started_handler(sender=None, task_id=None, task=None, **kwargs):
    """Handle task start event."""
    if task_id and task:
        publish_task_event(
            task_id,
            'started',
            {
                'name': task.name,
                'message': f"Task {task.name.split('.')[-1]} started"
            }
        )


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Handle task success event."""
    task_id = sender.request.id if sender else None
    
    if task_id:
        # Extract key result data (don't send entire result)
        result_summary = {}
        if isinstance(result, dict):
            # Only send summary fields
            result_summary = {
                k: v for k, v in result.items()
                if k in ['score', 'submission_id', 'variation_count', 
                        'successful_variations', 'total_variations']
            }
        
        publish_task_event(
            task_id,
            'completed',
            {
                'name': sender.name if sender else 'unknown',
                'message': 'Task completed successfully',
                'result': result_summary
            }
        )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    """Handle task failure event."""
    if task_id:
        publish_task_event(
            task_id,
            'failed',
            {
                'name': sender.name if sender else 'unknown',
                'message': f"Task failed: {str(exception)}",
                'error': str(exception)
            }
        )


@task_retry.connect
def task_retry_handler(sender=None, reason=None, **kwargs):
    """Handle task retry event."""
    task_id = sender.request.id if sender else None
    
    if task_id:
        retry_count = sender.request.retries if sender else 0
        
        publish_task_event(
            task_id,
            'retrying',
            {
                'name': sender.name if sender else 'unknown',
                'message': f"Retrying task (attempt {retry_count + 1})",
                'reason': str(reason) if reason else 'Unknown'
            }
        )


# Custom progress tracking for our pipeline tasks
def publish_progress(task_id: str, current: int, total: int, message: str = None):
    """
    Publish progress update for a task.
    
    This can be called from within tasks to report progress.
    
    Args:
        task_id: Task ID
        current: Current progress value
        total: Total progress value
        message: Optional progress message
    """
    percentage = round((current / total * 100) if total > 0 else 0, 1)
    
    publish_task_event(
        task_id,
        'progress',
        {
            'progress': {
                'current': current,
                'total': total,
                'percentage': percentage,
                'message': message or f"Processing... {percentage}%"
            }
        }
    )