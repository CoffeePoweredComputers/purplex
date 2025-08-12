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
ALLOWED_HOSTS = config.get_allowed_hosts()

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
    'purplex.submissions_app',
    'purplex.users_app',
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

DATABASES = {
    'default': dj_database_url.parse(
        config.get_database_url(),
        conn_max_age=60 if config.is_production else 0
    )
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
        'purplex.users_app.unified_authentication.UnifiedAuthentication',
        'purplex.users_app.unified_authentication.ServiceAccountAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
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
CORS_ALLOWED_ORIGINS = config.get_cors_origins()
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

# Celery Configuration
CELERY_BROKER_URL = config.get_redis_url()
CELERY_RESULT_BACKEND = config.get_redis_url()
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes

# Celery task routing
CELERY_TASK_ROUTES = {
    'purplex.problems_app.tasks.pipeline.*': {'queue': 'ai_operations'},
    'purplex.problems_app.tasks.execution.*': {'queue': 'code_execution'},
    'purplex.problems_app.tasks.analytics.*': {'queue': 'analytics'},
}

# OpenAI Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
GPT_MODEL = os.environ.get('GPT_MODEL', 'gpt-4o-mini')

# Firebase Configuration (handled by environment config)
FIREBASE_CONFIG = config.get_firebase_config()

# Feature Flags
ENABLE_EIPL = os.environ.get('ENABLE_EIPL', 'true').lower() == 'true'
ENABLE_HINTS = os.environ.get('ENABLE_HINTS', 'true').lower() == 'true'
ENABLE_COURSES = os.environ.get('ENABLE_COURSES', 'true').lower() == 'true'

# Custom settings from environment config
USE_MOCK_FIREBASE = config.use_mock_firebase
USE_MOCK_OPENAI = config.use_mock_openai
PURPLEX_ENVIRONMENT = config.env.value