"""Shared Docker execution service factory for optimal resource management."""

import logging
import os
from typing import Optional

from gevent import lock as gevent_lock

from .docker_execution_service import DockerExecutionService

logger = logging.getLogger(__name__)


class DockerServiceFactory:
    """Factory for managing shared DockerExecutionService instances."""

    _instance: Optional["DockerServiceFactory"] = None
    # CRITICAL FIX: Use gevent RLock instead of threading.Lock
    # This factory is called from both Celery greenlets and potentially background threads
    _lock = gevent_lock.RLock()

    def __new__(cls):
        """Singleton pattern for the factory."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._service = None
                    # CRITICAL FIX: Use gevent RLock for service-level lock
                    cls._instance._service_lock = gevent_lock.RLock()
                    cls._instance._worker_id = (
                        os.getpid()
                    )  # Track which worker owns the service
        return cls._instance

    def get_service(self) -> DockerExecutionService:
        """Get a shared DockerExecutionService instance per worker process."""
        current_pid = os.getpid()

        with self._service_lock:
            # Check if we need a new service (different worker or closed service)
            if (
                self._service is None
                or self._service._closed
                or self._worker_id != current_pid
            ):

                # Clean up old service if switching workers
                if self._service and not self._service._closed:
                    logger.info(f"Cleaning up service from worker {self._worker_id}")
                    try:
                        self._service.close()
                    except Exception as e:
                        logger.warning(f"Error closing old service: {e}")

                logger.info(
                    f"Creating shared DockerExecutionService for worker {current_pid}"
                )
                self._service = DockerExecutionService()
                self._worker_id = current_pid

            return self._service

    def cleanup(self):
        """Clean up the shared service."""
        with self._service_lock:
            if self._service and not self._service._closed:
                logger.info("Cleaning up shared DockerExecutionService")
                try:
                    self._service.close()
                except Exception as e:
                    logger.warning(f"Error during cleanup: {e}")
                finally:
                    self._service = None


# Global factory instance
_factory = DockerServiceFactory()


def get_shared_docker_service() -> DockerExecutionService:
    """Get a shared Docker execution service instance for the current worker."""
    return _factory.get_service()


def cleanup_shared_service():
    """Clean up the shared service (for testing or shutdown)."""
    _factory.cleanup()


class SharedDockerServiceContext:
    """Context manager that uses the shared service without closing it."""

    def __enter__(self) -> DockerExecutionService:
        self.service = get_shared_docker_service()
        return self.service

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't close the shared service, it's managed globally
        pass
