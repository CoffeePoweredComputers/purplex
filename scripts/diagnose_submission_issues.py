#!/usr/bin/env python3
"""
Diagnostic script to identify submission pipeline issues.

This script checks all critical components of the EiPL submission pipeline:
1. Redis connectivity and pub/sub
2. Celery worker status
3. Django database connectivity
4. Recent submission logs

Usage:
    python scripts/diagnose_submission_issues.py
"""

import os
import subprocess
import sys
from datetime import datetime, timedelta

import redis

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Colors for terminal output
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def check_redis():
    """Check if Redis is running and test pub/sub."""
    print_header("Checking Redis Connection")

    try:
        # Connect to Redis
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True,
        )

        # Test connection
        if r.ping():
            print_success("Redis is running and responding to PING")
        else:
            print_error("Redis PING failed")
            return False

        # Test pub/sub
        print_info("Testing Redis pub/sub functionality...")
        pubsub = r.pubsub()
        test_channel = "test:diagnostic"
        pubsub.subscribe(test_channel)

        # Publish a test message
        r.publish(test_channel, "diagnostic_test")

        # Try to receive it
        received = False
        for message in pubsub.listen():
            if message["type"] == "message" and message["data"] == "diagnostic_test":
                print_success("Redis pub/sub is working correctly")
                received = True
                break
            elif message["type"] == "subscribe":
                continue

        pubsub.unsubscribe(test_channel)
        pubsub.close()

        if not received:
            print_warning("Redis pub/sub test message not received")

        return True

    except redis.ConnectionError as e:
        print_error(f"Cannot connect to Redis: {e}")
        print_info("Make sure Redis is running: redis-server")
        return False
    except Exception as e:
        print_error(f"Redis check failed: {e}")
        return False


def check_celery():
    """Check if Celery workers are running."""
    print_header("Checking Celery Workers")

    try:
        # Try to run celery inspect active
        result = subprocess.run(
            ["celery", "-A", "purplex.celery_simple", "inspect", "active"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print_success("Celery workers are running")
            print_info("Active tasks:")
            print(result.stdout)
            return True
        else:
            print_error("Celery workers not responding")
            print_info(
                "Start workers with: celery -A purplex.celery_simple worker -l info"
            )
            return False

    except FileNotFoundError:
        print_error("Celery command not found")
        print_info("Install celery: pip install celery[redis]")
        return False
    except subprocess.TimeoutExpired:
        print_error("Celery inspect timed out (workers may be stuck)")
        return False
    except Exception as e:
        print_error(f"Celery check failed: {e}")
        return False


def check_django():
    """Check Django database connectivity."""
    print_header("Checking Django Database")

    try:
        # Set up Django
        import django

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "purplex.settings")
        django.setup()

        from django.db import connection
        from django.db.utils import OperationalError

        try:
            # Test database connection
            connection.ensure_connection()
            print_success("Django database connection successful")

            # Check recent submissions
            from purplex.submissions.models import Submission

            recent_count = Submission.objects.filter(
                submitted_at__gte=datetime.now() - timedelta(hours=24)
            ).count()

            print_info(f"Submissions in last 24 hours: {recent_count}")

            # Check for failed submissions
            failed_count = Submission.objects.filter(
                submitted_at__gte=datetime.now() - timedelta(hours=24),
                execution_status="failed",
            ).count()

            if failed_count > 0:
                print_warning(f"Failed submissions in last 24 hours: {failed_count}")
            else:
                print_success("No failed submissions in last 24 hours")

            return True

        except OperationalError as e:
            print_error(f"Database connection failed: {e}")
            return False

    except ImportError as e:
        print_error(f"Cannot import Django: {e}")
        return False
    except Exception as e:
        print_error(f"Django check failed: {e}")
        return False


def check_environment():
    """Check environment variables."""
    print_header("Checking Environment Variables")

    required_vars = [
        "DJANGO_SECRET_KEY",
        "DATABASE_URL",
        "REDIS_HOST",
        "REDIS_PORT",
    ]

    optional_vars = [
        "OPENAI_API_KEY",
        "SENTRY_DSN",
        "FIREBASE_CREDENTIALS_PATH",
    ]

    all_ok = True

    print_info("Required variables:")
    for var in required_vars:
        if os.getenv(var):
            print_success(f"{var} is set")
        else:
            print_error(f"{var} is NOT set")
            all_ok = False

    print_info("\nOptional variables:")
    for var in optional_vars:
        if os.getenv(var):
            print_success(f"{var} is set")
        else:
            print_warning(f"{var} is not set (optional)")

    return all_ok


def run_diagnostics():
    """Run all diagnostic checks."""
    print(f"\n{Colors.BOLD}Purplex Submission Pipeline Diagnostics{Colors.ENDC}")
    print(
        f"{Colors.BOLD}Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}"
    )

    results = {
        "environment": check_environment(),
        "redis": check_redis(),
        "celery": check_celery(),
        "django": check_django(),
    }

    # Summary
    print_header("Diagnostic Summary")

    all_passed = all(results.values())

    if all_passed:
        print_success("All checks passed! Your submission pipeline should be working.")
    else:
        print_error("Some checks failed. Please fix the issues above.")

        print_info("\nCommon fixes:")
        if not results["redis"]:
            print("  - Start Redis: redis-server")
            print("  - Or with Docker: docker run -d -p 6379:6379 redis:7")

        if not results["celery"]:
            print(
                "  - Start Celery worker: celery -A purplex.celery_simple worker -l info"
            )
            print("  - Or use start.sh script: ./start.sh")

        if not results["django"]:
            print("  - Check database connection settings")
            print("  - Run migrations: python manage.py migrate")

        if not results["environment"]:
            print("  - Set missing environment variables in .env file")

    return all_passed


if __name__ == "__main__":
    try:
        success = run_diagnostics()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Diagnostic interrupted by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
