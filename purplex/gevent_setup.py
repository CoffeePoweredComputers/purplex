"""
CRITICAL: Gevent monkey-patching for greenlet-aware concurrency.

This module MUST be imported BEFORE any other imports in both Gunicorn and Celery.

Why this is needed:
- Both Gunicorn (worker_class='gevent') and Celery (--pool=gevent) use greenlets
- Without monkey-patching, standard library modules (socket, threading, time, etc.)
  make blocking calls that freeze ALL greenlets in the OS thread
- This causes connection leakage, deadlocks, and system hangs

What it does:
- Replaces blocking stdlib calls with greenlet-aware versions
- Makes psycopg2 (PostgreSQL), Redis, and all I/O cooperative
- Enables proper greenlet context switching
"""

from gevent import monkey

# Patch ALL standard library modules to be greenlet-aware
# This must happen before ANY other imports that might use these modules
monkey.patch_all()

# Verification logging (will appear in container startup logs)
import sys
if 'gevent.monkey' in sys.modules:
    # Verify specific modules are patched
    print("✓ Gevent monkey-patching ACTIVE")
    print(f"  - socket: {monkey.is_module_patched('socket')}")
    print(f"  - threading: {monkey.is_module_patched('threading')}")
    print(f"  - time: {monkey.is_module_patched('time')}")
    print(f"  - ssl: {monkey.is_module_patched('ssl')}")
else:
    print("✗ WARNING: Gevent monkey-patching FAILED - this will cause deadlocks!")
