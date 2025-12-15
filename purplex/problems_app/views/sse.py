"""
Clean SSE implementation for real-time task updates.

Simple, maintainable Server-Sent Events streaming.
No authentication code - uses standard Django authentication.
"""

import json
import logging
import time
from typing import Generator

import redis
from celery.result import AsyncResult
from django.conf import settings
from django.http import HttpResponseForbidden, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from purplex.users_app.authentication import PurplexAuthentication

logger = logging.getLogger(__name__)


class CleanTaskSSEView(View):
    """
    Stream task status updates via Server-Sent Events.

    Simple implementation that:
    1. Authenticates using standard authentication
    2. Subscribes to Redis pub/sub for the task
    3. Streams events to the client
    4. Handles reconnection gracefully
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Authenticate before dispatching to get/post methods.
        """
        task_id = kwargs.get("task_id", "unknown")
        logger.info(f"🔌 SSE connection attempt for task {task_id}")
        logger.info(f"📋 Request headers: {dict(request.headers)}")
        logger.info(f"📋 Request GET params: {dict(request.GET)}")
        logger.info(f"📋 Request path: {request.path}")

        # Use standard PurplexAuthentication
        auth = PurplexAuthentication()
        auth_result = auth.authenticate(request)

        if not auth_result:
            logger.error(f"❌ SSE authentication FAILED for task {task_id}")
            logger.error(f"   Request path: {request.path}")
            logger.error(
                f"   Auth header: {request.headers.get('Authorization', 'MISSING')}"
            )
            logger.error(
                f"   SSE token param: {request.GET.get('sse_token', 'MISSING')}"
            )
            logger.error(f"   All headers: {dict(request.headers)}")
            return HttpResponseForbidden("Authentication required")

        request.user, request.auth = auth_result
        logger.info(
            f"✅ SSE authentication successful for task {task_id}, user: {request.user.username}"
        )
        return super().dispatch(request, *args, **kwargs)

    @method_decorator(never_cache)
    def get(self, request, task_id):
        """
        Stream SSE events for a specific task.

        Args:
            task_id: Celery task ID to monitor
        """
        # Authentication already handled in dispatch()
        # User is available in request.user

        # Create SSE response
        response = StreamingHttpResponse(
            self._event_stream(task_id), content_type="text/event-stream"
        )

        # Disable buffering for real-time streaming
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    def _event_stream(self, task_id: str) -> Generator[str, None, None]:
        """
        Generate SSE events for the task.

        Args:
            task_id: Task ID to monitor

        Yields:
            SSE-formatted event strings
        """
        # Setup Redis connection (per-request for SSE pub/sub)
        # Note: Can't use centralized client due to socket_keepalive_options conflicting with gevent
        redis_client = redis.Redis(
            host=getattr(settings, "REDIS_HOST", "localhost"),
            port=getattr(settings, "REDIS_PORT", 6379),
            password=getattr(settings, "REDIS_PASSWORD", None),
            db=0,
            decode_responses=True,
            socket_timeout=None,  # SSE needs indefinite timeout
            socket_connect_timeout=5,
        )

        # Subscribe to task channel
        pubsub = redis_client.pubsub()
        channel = f"task:{task_id}"
        pubsub.subscribe(channel)

        logger.info(f"SSE client connected for task {task_id}")

        try:
            # Send initial status
            yield self._format_sse_event(
                "connected", {"task_id": task_id, "message": "Connected to task stream"}
            )

            # Check current task status
            result = AsyncResult(task_id)
            if result.ready():
                # Task already completed
                if result.successful():
                    yield self._format_sse_event(
                        "completed", {"task_id": task_id, "result": result.result}
                    )
                else:
                    yield self._format_sse_event(
                        "failed", {"task_id": task_id, "error": str(result.info)}
                    )
                return

            # Stream events from Redis pub/sub
            for message in pubsub.listen():
                # Handle different message types
                if message["type"] == "message":
                    try:
                        # Parse and forward the event
                        event_data = json.loads(message["data"])
                        event_type = event_data.pop("type", "update")

                        yield self._format_sse_event(event_type, event_data)

                        # Stop streaming if task completed
                        if event_type in ["completed", "failed"]:
                            break

                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in message: {message['data']}")

                # Send periodic heartbeat to keep connection alive
                elif message["type"] == "subscribe":
                    yield self._format_sse_event(
                        "subscribed",
                        {"channel": channel, "message": "Subscribed to task updates"},
                    )

        except GeneratorExit:
            # Client disconnected
            logger.info(f"SSE client disconnected for task {task_id}")
        except Exception as e:
            logger.error(f"SSE streaming error for task {task_id}: {e}")
            yield self._format_sse_event(
                "error", {"message": "Streaming error occurred", "error": str(e)}
            )
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
        if "timestamp" not in data:
            data["timestamp"] = time.time()

        # Format as SSE
        lines = [
            f"event: {event_type}",
            f"data: {json.dumps(data)}",
            "",  # Empty line to end event
            "",  # Extra newline for compatibility
        ]

        return "\n".join(lines)


class CleanBatchSSEView(View):
    """
    Stream status updates for multiple tasks via Server-Sent Events.

    Clean implementation for batch task monitoring.
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Authenticate before dispatching to get/post methods.
        """
        # Use standard PurplexAuthentication
        auth = PurplexAuthentication()
        auth_result = auth.authenticate(request)

        if not auth_result:
            return HttpResponseForbidden("Authentication required")

        request.user, request.auth = auth_result
        return super().dispatch(request, *args, **kwargs)

    @method_decorator(never_cache)
    def get(self, request):
        """
        Stream SSE events for multiple tasks.

        Expects task_ids as comma-separated query parameter.
        """
        # Get task IDs from query params
        task_ids_param = request.GET.get("task_ids", "")
        if not task_ids_param:
            return HttpResponseForbidden("No task IDs provided")

        task_ids = [tid.strip() for tid in task_ids_param.split(",") if tid.strip()]
        if not task_ids:
            return HttpResponseForbidden("Invalid task IDs")

        # Create SSE response
        response = StreamingHttpResponse(
            self._batch_event_stream(task_ids), content_type="text/event-stream"
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    def _batch_event_stream(self, task_ids: list) -> Generator[str, None, None]:
        """
        Generate SSE events for multiple tasks.

        Args:
            task_ids: List of task IDs to monitor

        Yields:
            SSE-formatted event strings
        """
        # Setup Redis connection (per-request for SSE pub/sub)
        # Note: Can't use centralized client due to socket_keepalive_options conflicting with gevent
        redis_client = redis.Redis(
            host=getattr(settings, "REDIS_HOST", "localhost"),
            port=getattr(settings, "REDIS_PORT", 6379),
            password=getattr(settings, "REDIS_PASSWORD", None),
            db=0,
            decode_responses=True,
            socket_timeout=None,  # SSE needs indefinite timeout
            socket_connect_timeout=5,
        )

        # Subscribe to all task channels
        pubsub = redis_client.pubsub()
        channels = [f"task:{task_id}" for task_id in task_ids]
        for channel in channels:
            pubsub.subscribe(channel)

        logger.info(f"Batch SSE client connected for {len(task_ids)} tasks")

        try:
            # Send initial status for all tasks
            for task_id in task_ids:
                result = AsyncResult(task_id)
                status_data = {
                    "task_id": task_id,
                    "status": result.status,
                    "ready": result.ready(),
                }

                if result.ready():
                    if result.successful():
                        status_data["result"] = result.result
                    else:
                        status_data["error"] = str(result.info)

                yield self._format_sse_event("status", status_data)

            # Stream events from Redis pub/sub
            completed_tasks = set()

            for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        task_id = event_data.get("task_id")

                        if task_id:
                            yield self._format_sse_event("update", event_data)

                            # Track completed tasks
                            if event_data.get("type") in ["completed", "failed"]:
                                completed_tasks.add(task_id)

                                # Stop if all tasks completed
                                if len(completed_tasks) >= len(task_ids):
                                    yield self._format_sse_event(
                                        "all_complete",
                                        {"message": "All tasks completed"},
                                    )
                                    break

                    except json.JSONDecodeError:
                        logger.warning(
                            f"Invalid JSON in batch message: {message['data']}"
                        )

        except GeneratorExit:
            logger.info("Batch SSE client disconnected")
        except Exception as e:
            logger.error(f"Batch SSE streaming error: {e}")
            yield self._format_sse_event(
                "error", {"message": "Streaming error occurred", "error": str(e)}
            )
        finally:
            # Clean up
            for channel in channels:
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
        if "timestamp" not in data:
            data["timestamp"] = time.time()

        lines = [f"event: {event_type}", f"data: {json.dumps(data)}", "", ""]

        return "\n".join(lines)
