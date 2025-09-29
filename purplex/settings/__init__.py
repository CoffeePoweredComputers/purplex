"""
Settings initialization for Purplex.
Automatically selects the appropriate settings module based on PURPLEX_ENV.
"""
import os
import sys
from pathlib import Path

# Import configuration manager first
from purplex.config.environment import config

# Determine which settings module to use based on environment
environment = config.env.value

# Import the appropriate settings module
if environment == 'production':
    from .production import *
elif environment == 'development':
    from .development import *
elif environment == 'test':
    from .test import *
else:
    raise ValueError(f"Unknown environment: {environment}")

def validate_settings():
    """Validate critical settings for the current environment"""
    errors = []

    # Get settings from globals
    settings = globals()

    # Helper function to safely get settings
    def get_setting(name, default=None):
        return settings.get(name, default)

    # Check SECRET_KEY
    secret_key = get_setting('SECRET_KEY', '')
    if not secret_key or secret_key == 'development-key-change-in-production':
        if not config.is_development:
            errors.append("DJANGO_SECRET_KEY must be set to a secure value")

    # Check DEBUG setting matches environment
    debug_mode = get_setting('DEBUG', False)
    if config.is_production and debug_mode:
        errors.append("DEBUG must be False in production")
    elif config.is_development and not debug_mode:
        print("Warning: DEBUG is False in development environment")

    # Check database configuration
    databases = get_setting('DATABASES', {})
    if not databases.get('default'):
        errors.append("Database is not configured")

    # Check authentication classes
    rest_framework = get_setting('REST_FRAMEWORK', {})
    auth_classes = rest_framework.get('DEFAULT_AUTHENTICATION_CLASSES', [])
    if not auth_classes:
        errors.append("No authentication classes configured")

    # Check Firebase configuration if not using mock
    if not config.use_mock_firebase:
        # Check if Firebase is properly configured
        firebase_path = config.firebase_credentials_path
        if not firebase_path:
            errors.append("Firebase credentials path not configured for production")
        elif not os.path.exists(firebase_path):
            errors.append(f"Firebase credentials file not found at {firebase_path}")

    # Check OpenAI configuration if not using mock
    if not config.use_mock_openai:
        openai_key = get_setting('OPENAI_API_KEY', '')
        if not openai_key:
            errors.append("OPENAI_API_KEY not configured")

    # Check allowed hosts in production
    if config.is_production:
        allowed_hosts = get_setting('ALLOWED_HOSTS', [])
        if '*' in allowed_hosts:
            errors.append("ALLOWED_HOSTS cannot contain '*' in production")
        if not allowed_hosts:
            errors.append("ALLOWED_HOSTS must be configured in production")

    # Check CORS configuration in production
    if config.is_production:
        installed_apps = get_setting('INSTALLED_APPS', [])
        if 'corsheaders' in installed_apps:
            cors_allowed_origins = get_setting('CORS_ALLOWED_ORIGINS', [])
            cors_allow_all = get_setting('CORS_ALLOW_ALL_ORIGINS', False)
            if cors_allow_all:
                errors.append("CORS_ALLOW_ALL_ORIGINS should not be True in production")
            elif not cors_allowed_origins:
                print("Warning: No CORS_ALLOWED_ORIGINS configured in production")

    # Raise error if any critical issues found
    if errors:
        error_msg = "Settings validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        if config.is_production:
            raise ValueError(error_msg)
        else:
            print(f"Warning: {error_msg}")

# Run validation
try:
    validate_settings()
except ValueError as e:
    print(f"ERROR: {e}")
    if config.is_production:
        sys.exit(1)

# Print environment info
print(f"✓ Loaded {environment} settings")
print(f"✓ Database: {config.database_url.split('@')[-1] if config.database_url else 'Not configured'}")
print(f"✓ Firebase: {'Mock' if config.use_mock_firebase else 'Real'}")
print(f"✓ Debug: {DEBUG}")