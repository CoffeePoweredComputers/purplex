"""
Async task wrappers for long-running operations.

This module provides async wrappers for operations that should not block the main thread.
In production, these should be replaced with proper Celery tasks.
"""

import asyncio
import concurrent.futures
import functools
import logging
from typing import Any, Callable, Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound tasks
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def run_async(func: Callable) -> Callable:
    """
    Decorator to run a function asynchronously in a thread pool.
    
    This is a temporary solution until Celery is implemented.
    In production, this should be replaced with @celery_app.task
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # In DEBUG mode, run synchronously for easier debugging
        if settings.DEBUG:
            return func(*args, **kwargs)
        
        # Run in thread pool
        future = executor.submit(func, *args, **kwargs)
        return future
    
    return wrapper


def run_async_with_timeout(timeout_seconds: int = 30):
    """
    Decorator to run a function asynchronously with a timeout.
    
    Args:
        timeout_seconds: Maximum time to wait for the function to complete
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # In DEBUG mode, run synchronously
            if settings.DEBUG:
                return func(*args, **kwargs)
            
            future = executor.submit(func, *args, **kwargs)
            try:
                result = future.result(timeout=timeout_seconds)
                return result
            except concurrent.futures.TimeoutError:
                future.cancel()
                logger.error(f"Task {func.__name__} timed out after {timeout_seconds} seconds")
                raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
            except Exception as e:
                logger.error(f"Task {func.__name__} failed: {str(e)}")
                raise
        
        return wrapper
    return decorator


class AsyncAIService:
    """
    Async wrapper for AI service calls.
    
    This provides a non-blocking interface for AI operations.
    """
    
    @staticmethod
    @run_async_with_timeout(timeout_seconds=60)
    def generate_eipl_variations(problem: 'Problem', user_prompt: str) -> Dict[str, Any]:
        """
        Generate EiPL variations asynchronously.
        
        Args:
            problem: The Problem instance
            user_prompt: User's explanation prompt
            
        Returns:
            Dict containing success status and variations
        """
        from .services import AITestGenerationService
        
        try:
            ai_service = AITestGenerationService()
            result = ai_service.generate_eipl_variations(problem, user_prompt)
            return result
        except Exception as e:
            logger.error(f"AI generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'variations': []
            }
    
    @staticmethod  
    @run_async_with_timeout(timeout_seconds=30)
    def test_code_variations(code_variations: list, function_name: str, test_data: list) -> list:
        """
        Test multiple code variations asynchronously.
        
        Args:
            code_variations: List of code strings to test
            function_name: Name of the function to test
            test_data: List of test case data
            
        Returns:
            List of test results
        """
        from .services import CodeExecutionService
        
        results = []
        code_service = CodeExecutionService()
        
        for code in code_variations:
            try:
                result = code_service.test_solution(code, function_name, test_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Testing variation failed: {str(e)}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'passed': 0,
                    'total': len(test_data),
                    'results': []
                })
        
        return results


# Celery implementation notes for future
"""
CELERY IMPLEMENTATION GUIDE
==========================

To properly implement async tasks with Celery:

1. Install dependencies:
   pip install celery[redis] django-celery-results django-celery-beat

2. Add to settings.py:
   CELERY_BROKER_URL = 'redis://localhost:6379/0'
   CELERY_RESULT_BACKEND = 'django-db'
   CELERY_ACCEPT_CONTENT = ['json']
   CELERY_TASK_SERIALIZER = 'json'
   CELERY_RESULT_SERIALIZER = 'json'
   CELERY_TIMEZONE = TIME_ZONE
   
   INSTALLED_APPS += [
       'django_celery_results',
       'django_celery_beat',
   ]

3. Create celery.py in project root:
   ```python
   import os
   from celery import Celery
   
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purplex.settings')
   
   app = Celery('purplex')
   app.config_from_object('django.conf:settings', namespace='CELERY')
   app.autodiscover_tasks()
   ```

4. Create tasks.py in this app:
   ```python
   from celery import shared_task
   from .services import AITestGenerationService
   
   @shared_task(bind=True, max_retries=3)
   def generate_eipl_variations_task(self, problem_id: int, user_prompt: str):
       try:
           problem = Problem.objects.get(id=problem_id)
           ai_service = AITestGenerationService()
           return ai_service.generate_eipl_variations(problem, user_prompt)
       except Exception as exc:
           self.retry(exc=exc, countdown=60)
   ```

5. Update views to use async tasks:
   ```python
   from .tasks import generate_eipl_variations_task
   
   # In view:
   task = generate_eipl_variations_task.delay(problem.id, user_prompt)
   result = task.get(timeout=60)  # Or use AsyncResult for non-blocking
   ```

6. Run Celery worker:
   celery -A purplex worker -l info

7. For production, use supervisor or systemd to manage Celery workers.
"""