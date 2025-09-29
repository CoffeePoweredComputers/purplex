"""
Settings router for Purplex.
Automatically selects the appropriate settings module based on PURPLEX_ENV.
"""
import os
import sys

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import environment configuration
from config.environment import config

# Select and import the appropriate settings module
if config.is_production:
    from .production import *
elif config.is_staging:
    # Create staging settings if needed, for now use production
    from .production import *
else:
    from .development import *

# Validate critical settings
def validate_settings():
    """
    Ensure all required settings are properly configured.
    This runs after the environment-specific settings are loaded.
    """
    errors = []
    
    # Check SECRET_KEY
    if not SECRET_KEY or SECRET_KEY == 'development-key-change-in-production':
        if not config.is_development:
            errors.append("DJANGO_SECRET_KEY must be set to a secure value")
    
    # Check DEBUG setting matches environment
    if config.is_production and DEBUG:
        errors.append("DEBUG must be False in production")
    elif config.is_development and not DEBUG:
        print("Warning: DEBUG is False in development environment")
    
    # Check database configuration
    if not DATABASES.get('default'):
        errors.append("Database is not configured")
    
    # Check authentication classes
    auth_classes = REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', [])
    if not auth_classes:
        errors.append("No authentication classes configured")
    
    # Check Firebase configuration if not using mock
    if not config.use_mock_firebase:
        # Check if Firebase is properly configured
        firebase_path = config.firebase_credentials_path
        if not firebase_path or not os.path.exists(firebase_path):
            errors.append("Firebase credentials not configured for production")
    
    # Check OpenAI configuration if not using mock
    if not config.use_mock_openai:
        if not OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY not configured")
    
    # Check allowed hosts in production
    if config.is_production:
        if '*' in ALLOWED_HOSTS:
            errors.append("ALLOWED_HOSTS cannot contain '*' in production")
    
    # Check CORS configuration
    if config.is_production:
        if 'corsheaders' in INSTALLED_APPS:
            if not CORS_ALLOWED_ORIGINS and CORS_ALLOW_ALL_ORIGINS:
                errors.append("CORS_ALLOW_ALL_ORIGINS should not be True in production")
    
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