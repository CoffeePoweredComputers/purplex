"""
Periodic cleanup tasks for Docker containers and system resources.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name='cleanup.prune_orphaned_containers',
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3
)
def prune_orphaned_containers():
    """
    Periodic task to clean up orphaned Docker sandbox containers.

    This task runs every hour to remove:
    - Exited containers with label purplex-pool=true
    - Created but never started containers
    - Old containers (> 24 hours)

    Prevents disk space accumulation from failed cleanups.
    """
    try:
        import docker
        client = docker.from_env()

        removed_count = 0
        error_count = 0

        # Remove exited pool containers
        exited_containers = client.containers.list(
            all=True,
            filters={
                'status': 'exited',
                'label': 'purplex-pool=true'
            }
        )

        for container in exited_containers:
            try:
                container.remove(force=True)
                removed_count += 1
                logger.debug(f"Removed exited pool container {container.id[:12]}")
            except Exception as e:
                error_count += 1
                logger.warning(f"Failed to remove container {container.id[:12]}: {e}")

        # Remove created-but-never-started containers
        created_containers = client.containers.list(
            all=True,
            filters={
                'status': 'created',
                'label': 'purplex-pool=true'
            }
        )

        for container in created_containers:
            try:
                # Only remove if older than 1 hour
                created_at = container.attrs['Created']
                # Docker timestamps are ISO format
                from datetime import datetime, timedelta
                created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if (timezone.now() - created_time) > timedelta(hours=1):
                    container.remove(force=True)
                    removed_count += 1
                    logger.debug(f"Removed stale created container {container.id[:12]}")
            except Exception as e:
                error_count += 1
                logger.warning(f"Failed to remove created container {container.id[:12]}: {e}")

        client.close()

        if removed_count > 0:
            logger.info(f"Cleanup task: removed {removed_count} orphaned containers, {error_count} errors")
        else:
            logger.debug(f"Cleanup task: no orphaned containers found")

        return {
            'removed': removed_count,
            'errors': error_count,
            'timestamp': timezone.now().isoformat()
        }

    except ImportError:
        logger.error("Docker SDK not available, cannot perform cleanup")
        return {'error': 'Docker SDK not installed'}
    except Exception as e:
        logger.error(f"Unexpected error during container cleanup: {e}")
        return {'error': str(e)}


@shared_task(
    name='cleanup.log_pool_metrics',
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2
)
def log_pool_metrics():
    """
    Periodic task to log Docker pool metrics for monitoring.
    Runs every 15 minutes.
    """
    from purplex.problems_app.services.docker_execution_service import DockerExecutionService

    try:
        service = DockerExecutionService()
        metrics = service.get_pool_metrics()
        logger.info(f"Docker pool metrics: {metrics}")
        return metrics
    except Exception as e:
        logger.error(f"Error getting pool metrics: {e}")
        return {'error': str(e)}
