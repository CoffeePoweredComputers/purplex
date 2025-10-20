"""
Gunicorn configuration for production deployment
Optimized for 10k concurrent users
"""

# CRITICAL: Import gevent_setup FIRST to enable monkey-patching
# This MUST happen before any other imports
from purplex.gevent_setup import *  # noqa: F401, F403

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('WEB_PORT', '8000')}"
backlog = int(os.environ.get('GUNICORN_BACKLOG', '2048'))

# Worker processes
# CRITICAL: Using gevent for async support (SSE + concurrent code execution)
# With gevent: 4 workers × 500 connections = 2000 concurrent connections
workers = int(os.environ.get('GUNICORN_WORKERS', '4'))  # Reduced for gevent (more efficient)
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gevent')  # Changed from 'sync' to 'gevent'
worker_connections = int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', '500'))  # Increased for concurrency
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '50'))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '30'))
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '30'))
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '2'))

# Restart workers after this many seconds to help prevent memory leaks
max_requests_per_child = int(os.environ.get('GUNICORN_MAX_REQUESTS_PER_CHILD', '1000'))

# Threading
threads = int(os.environ.get('GUNICORN_THREADS', '4'))

# Process naming
proc_name = os.environ.get('GUNICORN_PROC_NAME', 'purplex')

# Server mechanics
daemon = os.environ.get('GUNICORN_DAEMON', 'false').lower() == 'true'
pidfile = os.environ.get('GUNICORN_PID_FILE', '/var/run/gunicorn/purplex.pid')
user = os.environ.get('GUNICORN_USER', None)
group = os.environ.get('GUNICORN_GROUP', None)
tmp_upload_dir = os.environ.get('GUNICORN_TMP_UPLOAD_DIR', None)

# Logging
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')
access_log_format = os.environ.get(
    'GUNICORN_ACCESS_LOG_FORMAT',
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
)

# Server hooks
def on_starting(server):
    server.log.info("Starting Purplex workers...")

def on_reload(server):
    server.log.info("Reloading Purplex workers...")

def when_ready(server):
    server.log.info("Purplex server is ready. Listening at: %s", server.address)

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

# SSL (if needed)
keyfile = os.environ.get('GUNICORN_SSL_KEYFILE', None)
certfile = os.environ.get('GUNICORN_SSL_CERTFILE', None)

# Performance tuning
preload_app = os.environ.get('GUNICORN_PRELOAD_APP', 'true').lower() == 'true'  # Load app before forking workers