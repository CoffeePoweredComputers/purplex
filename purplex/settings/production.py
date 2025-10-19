"""
Production settings for Purplex.
These settings extend base.py and are used for production deployment.
Security and performance optimizations are enabled.
"""
from .base import *

# Production must have DEBUG disabled
DEBUG = False

# Validate that we're really in production
if config.env.value != 'production':
    raise ValueError(f"Production settings loaded but PURPLEX_ENV is {config.env.value}")

# Security settings for production
# SSL settings - only enable if using HTTPS
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False').lower() == 'true'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'  # Changed from 'Strict' to allow OAuth redirects
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 86400  # 24 hours

# CSRF security
CSRF_COOKIE_HTTPONLY = False  # Must be False so JavaScript can read the token
CSRF_COOKIE_SAMESITE = 'Lax'  # Changed from 'Strict' to allow OAuth redirects
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')

# Ensure required production settings are set
if not os.environ.get('DJANGO_SECRET_KEY'):
    raise ValueError("DJANGO_SECRET_KEY must be set in production")

if ALLOWED_HOSTS == ['*'] or not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be properly configured in production")

# Static files - use WhiteNoise for serving
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_COMPRESS_OFFLINE = True
WHITENOISE_MANIFEST_STRICT = False

# Database connection pooling
# IMPORTANT: Set to 0 for gevent workers to avoid thread safety issues
# Gevent uses greenlets which are incompatible with persistent connections
DATABASES['default']['CONN_MAX_AGE'] = 0  # Disable persistent connections for gevent
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# Cache configuration for production (use Redis)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config.redis_url,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'purplex:cache:',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Session configuration - use Redis in production
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@purplex.com')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', 'server@purplex.com')

# Logging configuration for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config.log_file_paths['django'],
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config.log_file_paths['error'],
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'root': {
        'handlers': ['file', 'error_file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file', 'error_file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'purplex': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# File upload restrictions for production
FILE_UPLOAD_MAX_MEMORY_SIZE = config.file_upload_max_memory_size
DATA_UPLOAD_MAX_MEMORY_SIZE = config.get_int('DATA_UPLOAD_MAX_MEMORY_SIZE', config.file_upload_max_memory_size)
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Rate limiting for production
RATELIMIT_ENABLE = True
RATELIMIT_VIEW = '429.html'

# Admin configuration
ADMINS = [
    ('Admin', os.environ.get('ADMIN_EMAIL', 'admin@purplex.com')),
]
MANAGERS = ADMINS

# Sentry error tracking (optional but recommended)
if os.environ.get('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    def sentry_traces_sampler(sampling_context):
        """
        Custom sampling logic to prioritize critical paths within free tier limits.

        Strategy:
        - 100% sampling for critical user-facing operations (EiPL submissions, code execution)
        - 50% sampling for API endpoints
        - 10% sampling for admin pages
        - 5% sampling for static assets and health checks
        """
        try:
            # Get transaction context
            transaction_context = sampling_context.get('transaction_context', {})
            parent_sampled = sampling_context.get('parent_sampled')

            # Respect parent sampling decision for distributed traces
            if parent_sampled is not None:
                return parent_sampled

            # Extract transaction name and operation
            transaction_name = transaction_context.get('name', '')
            op = transaction_context.get('op', '')

            # Critical user operations - always sample
            critical_patterns = [
                '/api/submit-eipl',
                '/api/submit-solution',
                '/api/test-solution',
            ]
            if any(pattern in transaction_name for pattern in critical_patterns):
                return 1.0  # 100%

            # Health checks and static assets - minimal sampling
            if '/health' in transaction_name or '/static' in transaction_name:
                return 0.05  # 5%

            # Admin endpoints - low sampling
            if '/admin' in transaction_name or '/api/admin' in transaction_name:
                return 0.1  # 10%

            # API endpoints - moderate sampling
            if '/api/' in transaction_name:
                return 0.5  # 50%

            # Celery tasks - sample based on task name
            if op == 'celery.task':
                if 'execute_eipl_pipeline' in transaction_name:
                    return 1.0  # Critical pipeline
                return 0.3  # Other tasks

            # Default fallback
            return 0.1  # 10%

        except Exception as e:
            # If sampling logic fails, use conservative default
            logger.warning(f"Sentry sampling error: {e}")
            return 0.1

    def sentry_before_send(event, hint):
        """
        Filter and enrich events before sending to Sentry.
        Prevents noisy/expected errors from consuming quota.
        """
        try:
            # Filter out expected exceptions
            if 'exc_info' in hint:
                exc_type, exc_value, tb = hint['exc_info']

                # Don't send validation errors (user mistakes, not bugs)
                if exc_type.__name__ in ['ValidationError', 'PermissionDenied', 'Http404']:
                    return None

                # Don't send client-side errors
                if 'SuspiciousOperation' in exc_type.__name__:
                    return None

                # Don't send expected timeouts during high load
                if 'TimeoutError' in exc_type.__name__ and 'redis' in str(exc_value).lower():
                    # Log but don't send to Sentry
                    logger.warning(f"Redis timeout (expected during load): {exc_value}")
                    return None

            # Enrich event with custom context
            if 'request' in event:
                request_data = event['request']

                # Add custom tags for better grouping
                event['tags'] = event.get('tags', {})
                event['tags']['request_method'] = request_data.get('method', 'unknown')

                # Add user context if available (without PII)
                if 'user' in event and event['user']:
                    user = event['user']
                    # Remove PII, keep only aggregate info
                    if 'email' in user:
                        del user['email']
                    if 'username' in user:
                        user['username'] = 'redacted'

            return event

        except Exception as e:
            # If filtering fails, send the event anyway
            logger.error(f"Sentry before_send error: {e}")
            return event

    # Configure logging integration to capture logs as breadcrumbs
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )

    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[
            DjangoIntegration(
                transaction_style='url',  # Group by URL pattern, not individual URLs
                middleware_spans=True,    # Track middleware execution
                signals_spans=False,      # Disable signal tracing (too noisy)
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,  # Monitor scheduled tasks
                propagate_traces=True,    # Connect web requests to Celery tasks
            ),
            RedisIntegration(),
            logging_integration,
        ],

        # Environment and release tracking
        environment=os.environ.get('SENTRY_ENVIRONMENT', 'production'),
        release=os.environ.get('SENTRY_RELEASE', None),  # Set via CI/CD

        # Performance monitoring - Conservative sampling for free tier
        traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),

        # Profiling - Disabled by default to conserve quota
        profiles_sample_rate=float(os.environ.get('SENTRY_PROFILES_SAMPLE_RATE', '0.0')),

        # Privacy and security
        send_default_pii=False,
        attach_stacktrace=True,  # Include stack traces in messages

        # Custom trace sampling for critical paths
        traces_sampler=sentry_traces_sampler,

        # Custom error filtering
        before_send=sentry_before_send,

        # Request body handling
        max_request_body_size='medium',  # Capture limited request bodies

        # Breadcrumbs configuration
        max_breadcrumbs=50,
    )

# Performance optimizations
# Note: CONN_MAX_AGE is set to 0 in DATABASES config for gevent compatibility
ATOMIC_REQUESTS = True  # Wrap each request in a transaction

# Celery production optimizations
CELERY_TASK_COMPRESSION = 'gzip'
CELERY_MESSAGE_COMPRESSION = 'gzip'
CELERY_TASK_RESULT_EXPIRES = 3600  # 1 hour
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = config.get_int('CELERY_MAX_TASKS_PER_CHILD', 1000)

# Security headers
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
PERMISSIONS_POLICY = {
    'accelerometer': [],
    'camera': [],
    'geolocation': [],
    'microphone': [],
}

# Content Security Policy (CSP)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-eval'",  # Needed for Ace Editor and Vue
    "'unsafe-inline'",  # Needed for Firebase SDK inline scripts
    "https://apis.google.com",  # Firebase/Google APIs
    "https://accounts.google.com",  # Google Sign-In
    "https://*.googleapis.com",  # Google services
    "https://www.gstatic.com",  # Google static resources
    "https://static.cloudflareinsights.com",  # Cloudflare monitoring
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",  # Needed for Vue dynamic styles
    "https://fonts.googleapis.com",  # Google Fonts
)
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_CONNECT_SRC = (
    "'self'",
    "https://apis.google.com",  # Firebase API calls
    "https://accounts.google.com",  # Google Auth
    "https://*.googleapis.com",  # Google services
    "https://identitytoolkit.googleapis.com",  # Firebase Auth
    "https://securetoken.googleapis.com",  # Firebase tokens
    "https://www.google.com",  # Google tracking/analytics
    "https://*.purplex.org",  # Firebase auth subdomain
)
CSP_FONT_SRC = (
    "'self'",
    "https://fonts.gstatic.com",  # Google Fonts
)
CSP_FRAME_SRC = (
    "'self'",
    "https://accounts.google.com",  # Google Sign-In iframe
    "https://*.purplex.org",  # Firebase auth subdomain (auth.purplex.org)
    "https://pythontutor.com",  # Python Tutor debugger for hint visualization
)
CSP_OBJECT_SRC = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)