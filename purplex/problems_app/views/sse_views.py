"""
Server-Sent Events (SSE) views for real-time task status updates.

This module provides SSE-based real-time updates for task status,
offering efficient streaming with lower server load and better UX.
"""

import json
import time
import redis
import logging
from typing import Generator, Optional
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from django.views import View
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from celery.result import AsyncResult
from django.conf import settings
from firebase_admin import auth as firebase_auth
from django.contrib.auth.models import User
from purplex.users_app.models import UserProfile

logger = logging.getLogger(__name__)


class TaskStatusSSEView(View):
    """
    Stream task status updates via Server-Sent Events.
    
    Provides real-time task updates using Redis PUBSUB for efficient
    streaming with automatic reconnection and heartbeat support.
    """
    
    @method_decorator(never_cache)
    @method_decorator(csrf_exempt)  # SSE endpoints are read-only
    def get(self, request, task_id: str):
        """
        Stream task status updates for a specific task.
        
        Args:
            request: HTTP request
            task_id: Celery task ID or request ID
            
        Returns:
            StreamingHttpResponse with SSE event stream
        """
        # Authenticate user from query parameter or session
        user = self._authenticate_sse_request(request)
        if not user and not settings.DEBUG:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Validate user has permission to view this task
        if not self._validate_task_access(request, task_id, user):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Set up SSE response with proper headers
        user_id = user.id if user else 0
        response = StreamingHttpResponse(
            self._event_generator(task_id, user_id),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable Nginx buffering
        # Remove Connection header - let Django handle it
        
        return response
    
    def _authenticate_sse_request(self, request) -> Optional[User]:
        """
        Authenticate SSE request using Firebase token from query parameter.
        
        Since EventSource doesn't support custom headers, we pass the token
        as a query parameter for SSE endpoints.
        
        Args:
            request: HTTP request
            
        Returns:
            Authenticated User object or None
        """
        # Try to get token from query parameter
        token = request.GET.get('token')
        
        if token:
            try:
                # Verify Firebase token
                decoded_token = firebase_auth.verify_id_token(token)
                firebase_uid = decoded_token['uid']
                
                # Get or create Django user
                try:
                    user_profile = UserProfile.objects.get(firebase_uid=firebase_uid)
                    return user_profile.user
                except UserProfile.DoesNotExist:
                    # Create user if doesn't exist (same logic as FirebaseAuthentication)
                    email = decoded_token.get('email', '')
                    display_name = decoded_token.get('name', '')
                    username = email.split('@')[0] if email else firebase_uid[:15]
                    
                    # Ensure unique username
                    existing_count = User.objects.filter(username__startswith=username).count()
                    if existing_count > 0:
                        username = f"{username}{existing_count}"
                    
                    user = User.objects.create(
                        username=username,
                        email=email or '',
                        first_name=display_name or ''
                    )
                    
                    UserProfile.objects.create(
                        user=user,
                        firebase_uid=firebase_uid,
                        role='user'
                    )
                    
                    return user
                    
            except Exception as e:
                logger.error(f"Firebase token verification failed: {e}")
                return None
        
        # Fallback to session auth for development
        if hasattr(request, 'user') and request.user.is_authenticated:
            return request.user
        
        # Debug mode - return a debug user
        if settings.DEBUG:
            try:
                return User.objects.get(username='anavarre')
            except User.DoesNotExist:
                return User.objects.first()
        
        return None
    
    def _validate_task_access(self, request, task_id: str, user: Optional[User] = None) -> bool:
        """
        Validate that the user has permission to view this task.
        
        Args:
            request: HTTP request
            task_id: Task ID to validate
            user: Authenticated user (optional)
            
        Returns:
            True if user can access this task
        """
        # Check session-based authentication for development
        session_tasks = request.session.get('user_tasks', [])
        if task_id in session_tasks:
            return True
            
        # Check if task exists in Redis with user context
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=7,  # Temporary storage DB
            decode_responses=True
        )
        
        # Check both EiPL context and general task context
        context_key = f"eipl:context:{task_id}"
        task_context = redis_client.get(context_key)
        
        if task_context:
            context_data = json.loads(task_context)
            # For development, allow any authenticated user
            if user:
                # Verify user owns this task
                return context_data.get('user_id') == user.id
            # Allow for session-based auth in debug mode
            return settings.DEBUG
        
        # For direct task IDs, check Celery result backend
        result = AsyncResult(task_id)
        if result.id:
            # Task exists, check if we have user info in metadata
            task_meta_key = f"task:metadata:{task_id}"
            task_meta = redis_client.get(task_meta_key)
            if task_meta:
                meta_data = json.loads(task_meta)
                if user:
                    return meta_data.get('user_id') == user.id
            
            # If no metadata, allow access in debug mode only
            return settings.DEBUG
        
        return False
    
    def _event_generator(self, task_id: str, user_id: int) -> Generator[str, None, None]:
        """
        Generate SSE events for task status updates.
        
        Subscribes to Redis PUBSUB channel for real-time updates
        and checks Celery task status as needed.
        
        Args:
            task_id: Task ID to monitor
            user_id: User ID for security context
            
        Yields:
            SSE formatted events
        """
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=5,  # Real-time PUBSUB database
            decode_responses=True
        )
        
        # Subscribe to task-specific channel
        pubsub = redis_client.pubsub()
        channel = f"task:progress:{task_id}"
        pubsub.subscribe(channel)
        
        logger.info(f"SSE connection established for task {task_id} by user {user_id}")
        
        # Send initial connection event
        yield self._format_sse_event({
            'type': 'connection',
            'status': 'connected',
            'task_id': task_id
        })
        
        # Send immediate status check
        current_status = self._get_task_status(task_id)
        yield self._format_sse_event(current_status)
        
        # If task is already complete, close connection
        if current_status.get('status') in ['completed', 'failed']:
            pubsub.unsubscribe(channel)
            pubsub.close()
            return
        
        # Set up timeout and heartbeat
        last_heartbeat = time.time()
        timeout = 300  # 5 minutes max connection time
        heartbeat_interval = 30  # Send heartbeat every 30 seconds
        start_time = time.time()
        
        try:
            while True:
                # Check for timeout
                if time.time() - start_time > timeout:
                    yield self._format_sse_event({
                        'type': 'timeout',
                        'message': 'Connection timeout, please reconnect'
                    })
                    break
                
                # Check for messages with timeout
                message = pubsub.get_message(timeout=1)
                
                if message and message['type'] == 'message':
                    # Parse and forward the update
                    try:
                        data = json.loads(message['data'])
                        yield self._format_sse_event(data)
                        
                        # Check if task is complete
                        if data.get('status') in ['completed', 'failed']:
                            logger.info(f"Task {task_id} finished with status: {data['status']}")
                            break
                            
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in PUBSUB message: {message['data']}")
                
                # Send heartbeat to keep connection alive
                if time.time() - last_heartbeat > heartbeat_interval:
                    yield self._format_sse_event({'type': 'heartbeat'})
                    last_heartbeat = time.time()
                    
                    # Also check task status directly in case we missed updates
                    current_status = self._get_task_status(task_id)
                    if current_status.get('status') in ['completed', 'failed']:
                        yield self._format_sse_event(current_status)
                        break
                        
        except GeneratorExit:
            logger.info(f"SSE connection closed by client for task {task_id}")
        except Exception as e:
            logger.error(f"SSE error for task {task_id}: {str(e)}")
            yield self._format_sse_event({
                'type': 'error',
                'error': str(e)
            })
        finally:
            # Clean up Redis subscription
            try:
                pubsub.unsubscribe(channel)
                pubsub.close()
            except:
                pass
            logger.info(f"SSE connection closed for task {task_id}")
    
    def _get_task_status(self, task_id: str) -> dict:
        """
        Get current task status from Celery and Redis.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            Status dictionary
        """
        # Check Celery result
        result = AsyncResult(task_id)
        
        # Build base status
        status_data = {
            'task_id': task_id,
            'status': self._normalize_celery_state(result.state),
            'timestamp': time.time()
        }
        
        # Add result data based on state
        if result.ready():
            if result.successful():
                status_data['status'] = 'completed'
                status_data['result'] = result.result
            else:
                status_data['status'] = 'failed'
                status_data['error'] = str(result.info) if result.info else 'Unknown error'
        elif result.state == 'PENDING':
            status_data['status'] = 'pending'
            status_data['message'] = 'Task is queued'
        elif result.state == 'RETRY':
            status_data['status'] = 'retrying'
            if isinstance(result.info, dict):
                status_data['retry_count'] = result.info.get('retries', 0)
        else:
            # Task is running, check for progress info
            if result.info and isinstance(result.info, dict):
                status_data['progress'] = {
                    'current': result.info.get('current', 0),
                    'total': result.info.get('total', 100),
                    'description': result.info.get('description', 'Processing...')
                }
        
        # Check Redis for additional context
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=7,
            decode_responses=True
        )
        
        # Try to get EiPL context for richer information
        context_key = f"eipl:context:{task_id}"
        context = redis_client.get(context_key)
        if context:
            context_data = json.loads(context)
            status_data['problem_slug'] = context_data.get('problem_slug')
            status_data['problem_set_slug'] = context_data.get('problem_set_slug')
        
        return status_data
    
    def _normalize_celery_state(self, state: str) -> str:
        """
        Normalize Celery state to our standard status values.
        
        Args:
            state: Celery task state
            
        Returns:
            Normalized status string
        """
        state_map = {
            'PENDING': 'pending',
            'STARTED': 'processing',
            'RETRY': 'retrying',
            'SUCCESS': 'completed',
            'FAILURE': 'failed',
            'REVOKED': 'cancelled'
        }
        return state_map.get(state, 'processing')
    
    def _format_sse_event(self, data: dict, event_type: str = 'message') -> str:
        """
        Format data as SSE event.
        
        Args:
            data: Data to send
            event_type: SSE event type
            
        Returns:
            SSE formatted string
        """
        # Add event ID for reconnection support
        event_id = data.get('timestamp', time.time())
        
        lines = []
        if event_type != 'message':
            lines.append(f'event: {event_type}')
        lines.append(f'id: {event_id}')
        lines.append(f'data: {json.dumps(data)}')
        lines.append('')  # Empty line to signal end of event
        
        return '\n'.join(lines) + '\n'


class TaskBatchStatusSSEView(View):
    """
    Stream status updates for multiple tasks (e.g., parallel test execution).
    
    Useful for monitoring chord/group task execution where multiple
    subtasks are running in parallel.
    """
    
    @method_decorator(never_cache)
    @method_decorator(csrf_exempt)  # SSE endpoints are read-only
    def get(self, request):
        """
        Stream batch task status updates.
        
        Query params:
            task_ids: Comma-separated list of task IDs
            
        Returns:
            StreamingHttpResponse with SSE event stream
        """
        task_ids = request.GET.get('task_ids', '').split(',')
        task_ids = [tid.strip() for tid in task_ids if tid.strip()]
        
        if not task_ids:
            return JsonResponse({'error': 'No task IDs provided'}, status=400)
        
        # Authenticate user
        user = self._authenticate_sse_request(request)
        if not user and not settings.DEBUG:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Validate access to all tasks
        for task_id in task_ids:
            if not self._validate_task_access(request, task_id, user):
                return JsonResponse({'error': f'Access denied for task {task_id}'}, status=403)
        
        # Set up SSE response
        user_id = user.id if user else 0
        response = StreamingHttpResponse(
            self._batch_event_generator(task_ids, user_id),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        # Remove Connection header - let Django handle it
        
        return response
    
    def _authenticate_sse_request(self, request) -> Optional[User]:
        """Reuse authentication from single task view."""
        view = TaskStatusSSEView()
        return view._authenticate_sse_request(request)
    
    def _validate_task_access(self, request, task_id: str, user: Optional[User] = None) -> bool:
        """Reuse validation from single task view."""
        view = TaskStatusSSEView()
        return view._validate_task_access(request, task_id, user)
    
    def _batch_event_generator(self, task_ids: list, user_id: int) -> Generator[str, None, None]:
        """
        Generate SSE events for multiple tasks.
        
        Args:
            task_ids: List of task IDs to monitor
            user_id: User ID for security context
            
        Yields:
            SSE formatted events
        """
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=5,
            decode_responses=True
        )
        
        # Subscribe to all task channels
        pubsub = redis_client.pubsub()
        channels = [f"task:progress:{tid}" for tid in task_ids]
        pubsub.subscribe(*channels)
        
        logger.info(f"Batch SSE connection for {len(task_ids)} tasks by user {user_id}")
        
        # Send initial status for all tasks
        task_statuses = {}
        for task_id in task_ids:
            status = self._get_task_status(task_id)
            task_statuses[task_id] = status
            yield self._format_sse_event({
                'type': 'batch_status',
                'task_id': task_id,
                **status
            })
        
        # Check if all tasks are already complete
        all_complete = all(
            status.get('status') in ['completed', 'failed']
            for status in task_statuses.values()
        )
        
        if all_complete:
            yield self._format_sse_event({
                'type': 'batch_complete',
                'summary': self._get_batch_summary(task_statuses)
            })
            pubsub.unsubscribe(*channels)
            pubsub.close()
            return
        
        # Monitor all tasks
        start_time = time.time()
        timeout = 300
        last_heartbeat = time.time()
        
        try:
            while True:
                if time.time() - start_time > timeout:
                    yield self._format_sse_event({'type': 'timeout'})
                    break
                
                message = pubsub.get_message(timeout=1)
                
                if message and message['type'] == 'message':
                    # Extract task ID from channel name
                    channel = message['channel']
                    task_id = channel.split(':')[-1]
                    
                    try:
                        data = json.loads(message['data'])
                        data['task_id'] = task_id
                        task_statuses[task_id] = data
                        yield self._format_sse_event(data)
                        
                        # Check if all tasks are complete
                        all_complete = all(
                            status.get('status') in ['completed', 'failed']
                            for status in task_statuses.values()
                        )
                        
                        if all_complete:
                            yield self._format_sse_event({
                                'type': 'batch_complete',
                                'summary': self._get_batch_summary(task_statuses)
                            })
                            break
                            
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in batch message: {message['data']}")
                
                # Heartbeat
                if time.time() - last_heartbeat > 30:
                    yield self._format_sse_event({'type': 'heartbeat'})
                    last_heartbeat = time.time()
                    
        finally:
            pubsub.unsubscribe(*channels)
            pubsub.close()
    
    def _get_task_status(self, task_id: str) -> dict:
        """Reuse from single task view."""
        view = TaskStatusSSEView()
        return view._get_task_status(task_id)
    
    def _format_sse_event(self, data: dict) -> str:
        """Reuse from single task view."""
        view = TaskStatusSSEView()
        return view._format_sse_event(data)
    
    def _get_batch_summary(self, task_statuses: dict) -> dict:
        """
        Generate summary of batch task execution.
        
        Args:
            task_statuses: Dictionary of task statuses
            
        Returns:
            Summary dictionary
        """
        total = len(task_statuses)
        completed = sum(1 for s in task_statuses.values() if s.get('status') == 'completed')
        failed = sum(1 for s in task_statuses.values() if s.get('status') == 'failed')
        
        return {
            'total_tasks': total,
            'completed': completed,
            'failed': failed,
            'success_rate': (completed / total * 100) if total > 0 else 0
        }