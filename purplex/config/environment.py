"""
Single source of truth for environment configuration.
This module handles all environment detection and configuration for Purplex.
"""
import os
from enum import Enum
from typing import Dict, Optional


class Environment(Enum):
    """Supported environments for Purplex"""
    DEVELOPMENT = "development"
    STAGING = "staging" 
    PRODUCTION = "production"


class Config:
    """
    Central configuration class for environment-specific settings.
    
    This class provides a single source of truth for:
    - Environment detection
    - Feature flags
    - Service configuration
    - Security settings
    """
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        env_value = os.environ.get('PURPLEX_ENV', 'development').lower()
        
        # Validate environment value
        try:
            self.env = Environment(env_value)
        except ValueError:
            raise ValueError(
                f"Invalid PURPLEX_ENV value: '{env_value}'. "
                f"Must be one of: development, staging, production"
            )
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.env == Environment.DEVELOPMENT
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment"""
        return self.env == Environment.STAGING
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.env == Environment.PRODUCTION
    
    @property
    def debug(self) -> bool:
        """
        Debug mode should only be enabled in development.
        This replaces Django's DEBUG setting.
        """
        return self.is_development
    
    @property
    def use_mock_services(self) -> bool:
        """
        Determine if mock services should be used.
        Only in development environment.
        """
        return self.is_development
    
    @property
    def use_mock_firebase(self) -> bool:
        """Check if mock Firebase should be used"""
        if not self.is_development:
            return False
        # Allow override via environment variable
        return os.environ.get('USE_MOCK_FIREBASE', 'true').lower() == 'true'
    
    @property
    def use_mock_openai(self) -> bool:
        """Check if mock OpenAI should be used"""
        if not self.is_development:
            return False
        # Default to False - use real OpenAI even in dev for better testing
        return os.environ.get('USE_MOCK_OPENAI', 'false').lower() == 'true'
    
    def get_firebase_config(self) -> Optional[Dict[str, str]]:
        """
        Returns environment-specific Firebase configuration.
        Returns None if using mock Firebase.
        """
        if self.use_mock_firebase:
            return None  # Mock service doesn't need Firebase config
        
        return {
            'credentials_path': os.environ.get('FIREBASE_CREDENTIALS_PATH'),
            'project_id': os.environ.get('FIREBASE_PROJECT_ID'),
        }
    
    def get_database_url(self) -> str:
        """
        Returns environment-specific database configuration.
        Development has a default, others require explicit configuration.
        """
        if self.is_development:
            # Development default - local PostgreSQL
            return os.environ.get(
                'DATABASE_URL',
                'postgresql://purplex_user:devpass@localhost:5432/purplex_dev'
            )
        
        # Staging and Production must have DATABASE_URL set
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise ValueError(
                f"DATABASE_URL must be set in {self.env.value} environment"
            )
        return db_url
    
    def get_redis_url(self) -> str:
        """
        Returns environment-specific Redis configuration.
        """
        if self.is_development:
            # Development default - local Redis
            return os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        
        # Staging and Production must have REDIS_URL set
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            raise ValueError(
                f"REDIS_URL must be set in {self.env.value} environment"
            )
        return redis_url
    
    def get_allowed_hosts(self) -> list:
        """
        Returns list of allowed hosts for Django.
        """
        if self.is_development:
            return ['localhost', '127.0.0.1', '[::1]', '*']
        
        # Production/Staging from environment
        hosts_str = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
        if not hosts_str:
            raise ValueError(
                f"DJANGO_ALLOWED_HOSTS must be set in {self.env.value} environment"
            )
        return [h.strip() for h in hosts_str.split(',') if h.strip()]
    
    def get_cors_origins(self) -> list:
        """
        Returns list of allowed CORS origins.
        """
        if self.is_development:
            return [
                "http://localhost:5173",  # Vite dev server
                "http://localhost:3000",  # Alternative port
                "http://localhost:8000",  # Django
            ]
        
        # Production/Staging from environment
        origins_str = os.environ.get('CORS_ALLOWED_ORIGINS', '')
        if not origins_str:
            return []  # No CORS in production by default
        return [o.strip() for o in origins_str.split(',') if o.strip()]
    
    @property
    def require_https(self) -> bool:
        """Check if HTTPS should be enforced"""
        return self.is_production or self.is_staging
    
    @property
    def secure_cookies(self) -> bool:
        """Check if secure cookies should be used"""
        return self.is_production or self.is_staging
    
    def validate_configuration(self) -> None:
        """
        Validate that all required configuration is present for the current environment.
        Raises ValueError if configuration is invalid.
        """
        errors = []
        
        # Check Django secret key
        if not os.environ.get('DJANGO_SECRET_KEY'):
            if not self.is_development:
                errors.append("DJANGO_SECRET_KEY must be set")
        
        # Check database configuration
        try:
            self.get_database_url()
        except ValueError as e:
            errors.append(str(e))
        
        # Check Redis configuration
        try:
            self.get_redis_url()
        except ValueError as e:
            errors.append(str(e))
        
        # Check allowed hosts in production
        if self.is_production:
            try:
                hosts = self.get_allowed_hosts()
                if not hosts or hosts == ['*']:
                    errors.append("DJANGO_ALLOWED_HOSTS must be properly configured in production")
            except ValueError as e:
                errors.append(str(e))
        
        # Check Firebase configuration if not using mock
        if not self.use_mock_firebase:
            firebase_config = self.get_firebase_config()
            if not firebase_config or not firebase_config.get('credentials_path'):
                errors.append("Firebase credentials must be configured when not using mock")
        
        # Check OpenAI configuration
        if not self.use_mock_openai:
            if not os.environ.get('OPENAI_API_KEY'):
                errors.append("OPENAI_API_KEY must be set when not using mock OpenAI")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
    
    def __str__(self) -> str:
        """String representation of current configuration"""
        return (
            f"Purplex Configuration:\n"
            f"  Environment: {self.env.value}\n"
            f"  Debug: {self.debug}\n"
            f"  Mock Services: {self.use_mock_services}\n"
            f"  Mock Firebase: {self.use_mock_firebase}\n"
            f"  Mock OpenAI: {self.use_mock_openai}\n"
            f"  Require HTTPS: {self.require_https}\n"
            f"  Secure Cookies: {self.secure_cookies}"
        )


# Create singleton instance
config = Config()

# Validate on import (fail fast)
try:
    config.validate_configuration()
except ValueError as e:
    # Log the error but don't fail import in development
    if config.is_development:
        print(f"Warning: {e}")
    else:
        raise