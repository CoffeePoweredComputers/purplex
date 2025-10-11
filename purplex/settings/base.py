"""
Base Django settings for Purplex.
These settings are shared by all environments (development, staging, production).
Environment-specific settings are in their respective files.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.environment import config

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: Secret key is set from environment
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'development-key-change-in-production')

# Debug is controlled by environment
DEBUG = config.debug

# Allowed hosts from environment configuration
ALLOWED_HOSTS = config.allowed_hosts

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    
    # Our apps
    'purplex.problems_app',
    'purplex.users_app',
    'purplex.submissions',  # New clean submission system
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'purplex.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

# Database configuration from environment
import dj_database_url

# Parse base database configuration
db_config = dj_database_url.parse(
    config.database_url,
    conn_max_age=600 if config.is_production else 60  # Increased connection lifetime
)

# Add enhanced connection pool settings for high concurrency (1000+ users)
db_config.update({
    'OPTIONS': {
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000',  # 30 second statement timeout
        # Note: psycopg2 doesn't support built-in pooling, but these help with connection management
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
    },
    # CRITICAL: Connection lifetime and health checks for production scale
    # Reuse connections for 10 min in prod, 1 min in dev (prevents connection leaks)
    'CONN_MAX_AGE': 600 if config.is_production else 60,

    # CRITICAL: Enable connection health checks (Django 4.1+)
    # Validates connections before use to prevent stale connection errors at scale
    'CONN_HEALTH_CHECKS': True,
})

DATABASES = {
    'default': db_config
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
] if (BASE_DIR / 'static').exists() else []

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'purplex.users_app.authentication.PurplexAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'purplex.users_app.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}

# CORS configuration from environment
CORS_ALLOWED_ORIGINS = config.cors_allowed_origins
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-service-key',  # For service account authentication
]

# Redis Configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis' if 'docker' in os.environ.get('HOSTNAME', '') else 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))

# Celery Configuration
CELERY_BROKER_URL = config.redis_url
CELERY_RESULT_BACKEND = config.redis_url
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = config.celery_task_time_limit
CELERY_TASK_SOFT_TIME_LIMIT = config.celery_task_soft_time_limit

# Celery task routing
CELERY_TASK_ROUTES = {
    'purplex.problems_app.tasks.pipeline.*': {'queue': 'ai_operations'},
    'purplex.problems_app.tasks.execution.*': {'queue': 'code_execution'},
    'purplex.problems_app.tasks.analytics.*': {'queue': 'analytics'},
}

# AI Provider Configuration
AI_PROVIDER = config.ai_provider

# OpenAI Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
GPT_MODEL = os.environ.get('GPT_MODEL', 'gpt-4o-mini')

# Llama Configuration
LLAMA_API_KEY = config.llama_api_key
LLAMA_MODEL = config.llama_model

# Firebase Configuration (handled by environment config)
# Firebase configuration is handled directly via environment variables
FIREBASE_CREDENTIALS_PATH = config.firebase_credentials_path

# Firebase Token Settings
# Cache TTL: How long to cache verified Firebase tokens (55 minutes)
# Aligns with frontend refresh schedule (frontend refreshes at T=55min before 1-hour expiry)
FIREBASE_TOKEN_CACHE_TTL = 3300  # 55 minutes in seconds

# Grace Period: Accept recently expired tokens during Firebase API outages (10 minutes)
# Enables graceful degradation when Firebase is temporarily unavailable
# Must match frontend grace period in useTokenRefresh.ts
FIREBASE_GRACE_PERIOD_SECONDS = 600  # 10 minutes in seconds

# Feature Flags
ENABLE_EIPL = config.enable_eipl
ENABLE_HINTS = config.enable_hints
ENABLE_COURSES = config.enable_courses

# Custom settings from environment config
USE_MOCK_FIREBASE = config.use_mock_firebase
USE_MOCK_OPENAI = config.use_mock_openai
PURPLEX_ENVIRONMENT = config.env.value

# Import security configuration
from purplex.settings.security import CODE_EXECUTION, RATE_LIMITS