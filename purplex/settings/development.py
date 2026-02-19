"""
Development settings for Purplex.
These settings extend base.py and are used for local development.
"""

from .base import *

# Development-specific settings
DEBUG = True

# More permissive hosts for development
ALLOWED_HOSTS = ["*"]

# CORS - allow all origins in development for easier testing
CORS_ALLOW_ALL_ORIGINS = True

# Development-specific installed apps
INSTALLED_APPS += [
    # Add development tools here if needed
]

# Development middleware
if os.environ.get("ENABLE_DEBUG_TOOLBAR", "false").lower() == "true":
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1", "localhost"]
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
    }

# Development database configuration
# Already configured in base.py via environment.py

# Email backend for development (console output)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Logging configuration for development
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "development.log",
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": (
                "DEBUG"
                if os.environ.get("LOG_SQL_QUERIES", "false").lower() == "true"
                else "INFO"
            ),
            "propagate": False,
        },
        "purplex": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Create logs directory if it doesn't exist
import os

os.makedirs(BASE_DIR / "logs", exist_ok=True)

# Development-specific security settings (less restrictive)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
X_FRAME_OPTIONS = "SAMEORIGIN"

# Celery development settings
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_EAGER", "false").lower() == "true"
CELERY_TASK_EAGER_PROPAGATES = True

# Cache configuration for development (use local memory)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# File upload settings for development
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Development-specific feature flags
SHOW_DEBUG_TOOLBAR = os.environ.get("SHOW_DEBUG_TOOLBAR", "false").lower() == "true"
ENABLE_QUERY_LOGGING = os.environ.get("LOG_SQL_QUERIES", "false").lower() == "true"
ENABLE_REQUEST_LOGGING = os.environ.get("LOG_REQUESTS", "true").lower() == "true"

# Test user configuration for development
TEST_USER_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "testpass123")

print(
    f"""
========================================
Purplex Development Server
========================================
Environment: {PURPLEX_ENVIRONMENT}
Debug: {DEBUG}
Mock Firebase: {USE_MOCK_FIREBASE}
Mock OpenAI: {USE_MOCK_OPENAI}
Database: {DATABASES["default"]["NAME"]}
========================================
"""
)
