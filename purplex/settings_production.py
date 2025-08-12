"""
Production settings for Purplex - PostgreSQL optimized for 1000+ concurrent users
"""

import os
import sys
from pathlib import Path
import dj_database_url
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY - All from environment variables
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']  # Will fail if not set - good!
DEBUG = False
ALLOWED_HOSTS = os.environ['DJANGO_ALLOWED_HOSTS'].split(',')

# Database Router for read/write splitting
class PrimaryReplicaRouter:
    """
    Route reads to replicas, writes to primary
    """
    def db_for_read(self, model, **hints):
        """Route read queries to replica."""
        # Skip replica for auth and sessions to avoid lag issues
        if model._meta.app_label in ['auth', 'sessions', 'admin']:
            return 'primary'
        return 'replica1'
    
    def db_for_write(self, model, **hints):
        """Route writes to primary."""
        return 'primary'
    
    def allow_relation(self, obj1, obj2, **hints):
        """Relations between objects are allowed."""
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure migrations only run on primary."""
        return db == 'primary'


# PostgreSQL Configuration with connection pooling
DATABASES = {
    'default': {},  # Django requires this
    
    # Primary database for writes
    'primary': dj_database_url.config(
        default=os.environ['DATABASE_URL'],
        conn_max_age=0,  # Disable Django pooling, use PgBouncer
        ssl_require=True,
        options={
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30 second timeout
            'sslmode': 'require',
        }
    ),
    
    # Read replica 1 - for general queries
    'replica1': dj_database_url.config(
        default=os.environ.get('DATABASE_REPLICA1_URL', os.environ['DATABASE_URL']),
        conn_max_age=0,
        ssl_require=True,
        options={
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',
            'sslmode': 'require',
        }
    ),
    
    # Read replica 2 - for analytics/reporting
    'replica2': dj_database_url.config(
        default=os.environ.get('DATABASE_REPLICA2_URL', os.environ['DATABASE_URL']),
        conn_max_age=0,
        ssl_require=True,
        options={
            'connect_timeout': 10,
            'options': '-c statement_timeout=60000',  # 60s for analytics
            'sslmode': 'require',
        }
    ),
}

# Use the router
DATABASE_ROUTERS = ['purplex.settings_production.PrimaryReplicaRouter']

# Use PgBouncer if available
if os.environ.get('PGBOUNCER_URL'):
    DATABASES['primary'] = dj_database_url.config(
        default=os.environ['PGBOUNCER_URL'],
        conn_max_age=0,
    )

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'django_prometheus',  # Add prometheus metrics
    'purplex',
    'purplex.problems_app',
    'purplex.submissions_app',
    'purplex.users_app',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',  # First
    'corsheaders.middleware.CorsMiddleware',  
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',  # Last
]

ROOT_URLCONF = 'purplex.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'purplex.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files with WhiteNoise
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# WhiteNoise settings
WHITENOISE_COMPRESS_OFFLINE = True
WHITENOISE_COMPRESSION_QUALITY = 80

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Security Settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
SESSION_COOKIE_AGE = 86400 * 14  # 2 weeks
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'

# CORS settings
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
CORS_ALLOW_CREDENTIALS = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'purplex.users_app.authentication.FirebaseAuthentication',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# Firebase configuration
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    'FIREBASE_CREDENTIALS_PATH',
    os.path.join(BASE_DIR, 'firebase-credentials.json')
)

# OpenAI API Configuration
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

# Redis Configuration - Optimized for production
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')

redis_url_base = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}' if REDIS_PASSWORD else f'redis://{REDIS_HOST}:{REDIS_PORT}'

# Celery Configuration
CELERY_BROKER_URL = f'{redis_url_base}/0'
CELERY_RESULT_BACKEND = f'{redis_url_base}/1'

# Celery settings optimized for production
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Task execution settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes soft limit
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # Restart after 1000 tasks to prevent memory leaks

# Task routing for different queues
CELERY_TASK_ROUTES = {
    'pipeline.execute_eipl': {'queue': 'ai_generation'},
    'pipeline.generate_variations': {'queue': 'ai_generation'},
    'submissions.execute_code': {'queue': 'code_execution'},
    'progress.update_progress': {'queue': 'progress_updates'},
}

# Result backend settings  
CELERY_RESULT_EXPIRES = 3600  # 1 hour
CELERY_RESULT_COMPRESSION = 'gzip'
CELERY_RESULT_EXTENDED = True

# Django Cache Configuration with Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{redis_url_base}/2',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
        },
        'KEY_PREFIX': 'purplex',
        'TIMEOUT': 300,  # 5 minutes default
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{redis_url_base}/3',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
            }
        }
    },
    'rate_limit': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{redis_url_base}/4',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Rate limiting configuration
RATELIMIT_USE_CACHE = 'rate_limit'
RATELIMIT_ENABLE = True

# Sentry Error Tracking
sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(
            transaction_style='url',
            middleware_spans=True,
        ),
        CeleryIntegration(
            monitor_beat_tasks=True,
            propagate_traces=True,
        ),
        RedisIntegration(),
    ],
    
    # Performance monitoring
    traces_sample_rate=0.1,  # Capture 10% of transactions for performance
    profiles_sample_rate=0.1,  # Profile 10% of sampled transactions
    
    # Release tracking
    release=os.environ.get('SENTRY_RELEASE', 'purplex@1.0.0'),
    environment=os.environ.get('SENTRY_ENVIRONMENT', 'production'),
    
    # Session tracking
    auto_session_tracking=True,
    
    # Filtering
    ignore_errors=[
        KeyboardInterrupt,
        'django.security.DisallowedHost',
    ],
    
    # Additional options
    send_default_pii=False,  # Don't send personally identifiable information
    attach_stacktrace=True,
    max_breadcrumbs=50,
)

# Logging configuration - Production ready
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/purplex/django.log',
            'maxBytes': 1024 * 1024 * 100,  # 100 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'sentry_sdk.integrations.logging.EventHandler',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'sentry'],
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'level': 'ERROR',  # Only log database errors in production
            'handlers': ['console'],
            'propagate': False,
        },
        'purplex': {
            'handlers': ['console', 'file', 'sentry'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Performance optimizations
CONN_MAX_AGE = 0  # Let PgBouncer handle connection pooling
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB

# Admin site customization
ADMIN_SITE_HEADER = "Purplex Administration"
ADMIN_SITE_TITLE = "Purplex"
ADMIN_SITE_INDEX_TITLE = "Welcome to Purplex Administration"

print(f"Production settings loaded: PostgreSQL with replicas, Sentry enabled, PgBouncer ready")