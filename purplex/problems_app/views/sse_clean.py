"""
Clean SSE implementation for real-time task updates.

Simple, maintainable Server-Sent Events streaming.
"""

import json
import time
import redis
import logging
from typing import Generator
from django.http import StreamingHttpResponse
from django.views import View
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from celery.result import AsyncResult
from django.conf import settings

logger = logging.getLogger(__name__)


class CleanTaskSSEView(View):
    """
    Stream task status updates via Server-Sent Events.
    
    Simple implementation that:
    1. Subscribes to Redis pub/sub for the task
    2. Streams events to the client
    3. Handles reconnection gracefully
    """
    
    @method_decorator(never_cache)
    def get(self, request, task_id):
        """
        Stream SSE events for a specific task.
        
        Args:
            task_id: Celery task ID to monitor
        """
        # Create SSE response
        response = StreamingHttpResponse(
            self._event_stream(task_id),
            content_type='text/event-stream'
        )
        
        # Disable buffering for real-time streaming
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        
        return response
    
    def _event_stream(self, task_id: str) -> Generator[str, None, None]:
        """
        Generate SSE events for the task.
        
        Args:
            task_id: Task ID to monitor
            
        Yields:
            SSE-formatted event strings
        """
        # Setup Redis connection
        redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=0,
            decode_responses=True
        )
        
        # Subscribe to task channel
        pubsub = redis_client.pubsub()
        channel = f'task:{task_id}'
        pubsub.subscribe(channel)
        
        logger.info(f"SSE client connected for task {task_id}")
        
        try:
            # Send initial status
            yield self._format_sse_event('connected', {
                'task_id': task_id,
                'message': 'Connected to task stream'
            })
            
            # Check current task status
            result = AsyncResult(task_id)
            if result.ready():
                # Task already completed
                if result.successful():
                    yield self._format_sse_event('completed', {
                        'task_id': task_id,
                        'result': result.result
                    })
                else:
                    yield self._format_sse_event('failed', {
                        'task_id': task_id,
                        'error': str(result.info)
                    })
                return
            
            # Stream events from Redis pub/sub
            for message in pubsub.listen():
                # Handle different message types
                if message['type'] == 'message':
                    try:
                        # Parse and forward the event
                        event_data = json.loads(message['data'])
                        event_type = event_data.pop('type', 'update')
                        
                        yield self._format_sse_event(event_type, event_data)
                        
                        # Stop streaming if task completed
                        if event_type in ['completed', 'failed']:
                            break
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in message: {message['data']}")
                
                # Send periodic heartbeat to keep connection alive
                elif message['type'] == 'subscribe':
                    yield self._format_sse_event('subscribed', {
                        'channel': channel,
                        'message': 'Subscribed to task updates'
                    })
                
        except GeneratorExit:
            # Client disconnected
            logger.info(f"SSE client disconnected for task {task_id}")
        except Exception as e:
            logger.error(f"SSE streaming error for task {task_id}: {e}")
            yield self._format_sse_event('error', {
                'message': 'Streaming error occurred',
                'error': str(e)
            })
        finally:
            # Clean up
            pubsub.unsubscribe(channel)
            pubsub.close()
    
    def _format_sse_event(self, event_type: str, data: dict) -> str:
        """
        Format data as SSE event.
        
        Args:
            event_type: Type of event
            data: Event data
            
        Returns:
            SSE-formatted string
        """
        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = time.time()
        
        # Format as SSE
        lines = [
            f'event: {event_type}',
            f'data: {json.dumps(data)}',
            '',  # Empty line to end event
            ''   # Extra newline for compatibility
        ]
        
        return '\n'.join(lines)


class CleanTaskStatusView(View):
    """
    Simple REST endpoint for task status.
    
    No Redis manipulation, just Celery's result backend.
    """
    
    def get(self, request, task_id):
        """
        Get current status of a task.
        
        Args:
            task_id: Celery task ID
        """
        from django.http import JsonResponse
        
        result = AsyncResult(task_id)
        
        # Build response
        response_data = {
            'task_id': task_id,
            'status': result.status,
            'ready': result.ready()
        }
        
        # Add result or error if ready
        if result.ready():
            if result.successful():
                response_data['successful'] = True
                response_data['result'] = result.result
            else:
                response_data['successful'] = False
                response_data['error'] = str(result.info)
        else:
            # Task still running
            response_data['successful'] = None
            
            # Try to get progress info from result backend
            if hasattr(result, 'info') and isinstance(result.info, dict):
                response_data['progress'] = result.info.get('progress')
        
        return JsonResponse(response_data)