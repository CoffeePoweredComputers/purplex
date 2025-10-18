"""
Enhanced environment configuration with comprehensive validation.
This module provides a single source of truth for all configuration with:
- Type validation and coercion
- Required variable enforcement
- Security checks
- Fail-fast validation
"""
import os
import sys
from enum import Enum
from typing import Dict, Optional, Any, List, Union
from pathlib import Path


class Environment(Enum):
    """Supported environments for Purplex"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigurationError(Exception):
    """Raised when configuration validation fails"""
    pass


class ConfigValidator:
    """Validates and coerces configuration values"""
    
    @staticmethod
    def to_bool(value: Any) -> bool:
        """Convert various representations to boolean"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 't', 'y')
        return bool(value)
    
    @staticmethod
    def to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
        """Convert to integer with optional default"""
        if value is None or value == '':
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            if default is not None:
                return default
            raise ConfigurationError(f"Invalid integer value: {value}")
    
    @staticmethod
    def to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        """Convert to float with optional default"""
        if value is None or value == '':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            if default is not None:
                return default
            raise ConfigurationError(f"Invalid float value: {value}")
    
    @staticmethod
    def to_list(value: Any, separator: str = ',') -> List[str]:
        """Convert comma-separated string to list"""
        if isinstance(value, list):
            return value
        if not value:
            return []
        return [item.strip() for item in str(value).split(separator) if item.strip()]
    
    @staticmethod
    def validate_path(path: str, must_exist: bool = False) -> str:
        """Validate file system path"""
        if not path:
            raise ConfigurationError("Path cannot be empty")
        
        path_obj = Path(path)
        if must_exist and not path_obj.exists():
            raise ConfigurationError(f"Path does not exist: {path}")
        
        return str(path_obj)
    
    @staticmethod
    def validate_url(url: str) -> str:
        """Validate URL format"""
        if not url:
            raise ConfigurationError("URL cannot be empty")
        
        valid_schemes = ('http://', 'https://', 'postgresql://', 'redis://', 'amqp://')
        if not any(url.startswith(scheme) for scheme in valid_schemes):
            raise ConfigurationError(f"Invalid URL scheme: {url}")
        
        return url


class Config:
    """
    Central configuration class with comprehensive validation.
    
    This class provides:
    - Environment detection
    - Type-safe configuration access
    - Validation of all required settings
    - Security enforcement
    """
    
    def __init__(self):
        """Initialize and validate configuration"""
        self.validator = ConfigValidator()
        
        # Load environment
        env_value = os.environ.get('PURPLEX_ENV', 'development').lower()
        try:
            self.env = Environment(env_value)
        except ValueError:
            raise ConfigurationError(
                f"Invalid PURPLEX_ENV value: '{env_value}'. "
                f"Must be one of: development, staging, production"
            )
        
        # Cache for validated values
        self._cache: Dict[str, Any] = {}
        
        # Perform initial validation
        self._initial_validation()
    
    def _initial_validation(self) -> None:
        """Perform initial configuration validation"""
        # In production, certain settings are mandatory
        if self.is_production:
            # Check for development/test values
            secret_key = os.environ.get('DJANGO_SECRET_KEY', '')
            if 'development' in secret_key.lower() or 'test' in secret_key.lower():
                raise ConfigurationError(
                    "Production cannot use development/test secret key"
                )
            
            # Ensure mock services are disabled
            if self.get_bool('USE_MOCK_FIREBASE', False):
                raise ConfigurationError("Mock Firebase cannot be used in production")
            if self.get_bool('USE_MOCK_OPENAI', False):
                raise ConfigurationError("Mock OpenAI cannot be used in production")
            
            # Ensure debug is off
            if self.get_bool('DJANGO_DEBUG', False):
                raise ConfigurationError("DEBUG must be False in production")
    
    # =====================================================================
    # Environment Properties
    # =====================================================================
    
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
    
    # =====================================================================
    # Configuration Getters with Type Validation
    # =====================================================================
    
    def get(self, key: str, default: Any = None, required: bool = False) -> Any:
        """Get configuration value with optional requirement check"""
        value = os.environ.get(key, default)
        if required and value is None:
            raise ConfigurationError(f"Required configuration missing: {key}")
        return value
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value"""
        if key in self._cache:
            return self._cache[key]
        
        value = os.environ.get(key)
        if value is None:
            result = default
        else:
            result = self.validator.to_bool(value)
        
        self._cache[key] = result
        return result
    
    def get_int(self, key: str, default: Optional[int] = None, required: bool = False) -> Optional[int]:
        """Get integer configuration value"""
        if key in self._cache:
            return self._cache[key]
        
        value = os.environ.get(key)
        if value is None and required:
            raise ConfigurationError(f"Required configuration missing: {key}")
        
        result = self.validator.to_int(value, default)
        self._cache[key] = result
        return result
    
    def get_float(self, key: str, default: Optional[float] = None, required: bool = False) -> Optional[float]:
        """Get float configuration value"""
        if key in self._cache:
            return self._cache[key]
        
        value = os.environ.get(key)
        if value is None and required:
            raise ConfigurationError(f"Required configuration missing: {key}")
        
        result = self.validator.to_float(value, default)
        self._cache[key] = result
        return result
    
    def get_list(self, key: str, default: Optional[List[str]] = None, separator: str = ',') -> List[str]:
        """Get list configuration value from comma-separated string"""
        if key in self._cache:
            return self._cache[key]
        
        value = os.environ.get(key)
        if value is None:
            result = default or []
        else:
            result = self.validator.to_list(value, separator)
        
        self._cache[key] = result
        return result
    
    def get_path(self, key: str, default: Optional[str] = None, must_exist: bool = False) -> Optional[str]:
        """Get and validate file system path"""
        value = os.environ.get(key, default)
        if value is None:
            return None
        return self.validator.validate_path(value, must_exist)
    
    def get_url(self, key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """Get and validate URL"""
        value = os.environ.get(key, default)
        if value is None:
            if required:
                raise ConfigurationError(f"Required URL configuration missing: {key}")
            return None
        return self.validator.validate_url(value)
    
    # =====================================================================
    # Django Core Settings
    # =====================================================================
    
    @property
    def debug(self) -> bool:
        """Django DEBUG setting"""
        return self.get_bool('DJANGO_DEBUG', default=self.is_development)
    
    @property
    def secret_key(self) -> str:
        """Django SECRET_KEY"""
        if self.is_development:
            return self.get('DJANGO_SECRET_KEY', 'development-secret-key-do-not-use-in-production')
        return self.get('DJANGO_SECRET_KEY', required=True)
    
    @property
    def allowed_hosts(self) -> List[str]:
        """Django ALLOWED_HOSTS"""
        if self.is_development:
            return self.get_list('DJANGO_ALLOWED_HOSTS', ['localhost', '127.0.0.1', '[::1]', '*'])
        
        hosts = self.get_list('DJANGO_ALLOWED_HOSTS')
        if not hosts or hosts == ['*']:
            raise ConfigurationError("Production requires DJANGO_ALLOWED_HOSTS environment variable with specific IPs/domains (not wildcard '*'). Example: DJANGO_ALLOWED_HOSTS=54.123.45.67,mydomain.com,localhost,127.0.0.1")
        return hosts
    
    @property
    def server_url(self) -> str:
        """Internal server URL"""
        default = 'http://localhost:8000' if self.is_development else 'https://purplex.com'
        return self.get('SERVER_URL', default)
    
    # =====================================================================
    # Database Configuration
    # =====================================================================
    
    @property
    def database_url(self) -> str:
        """Primary database URL"""
        if self.is_development:
            default = 'postgresql://purplex_user:devpass@localhost:5432/purplex_dev'
            return self.get_url('DATABASE_URL', default)
        return self.get_url('DATABASE_URL', required=True)
    
    @property
    def db_conn_max_age(self) -> int:
        """Database connection max age"""
        default = 0 if self.is_development else 600
        return self.get_int('DB_CONN_MAX_AGE', default)
    
    @property
    def db_pool_size(self) -> int:
        """Database connection pool size"""
        # Increased for beta test: (4 gevent workers × 50 connections) + (12 celery workers × 2) = ~224
        # Using 75 as safe middle ground with buffer
        default = 5 if self.is_development else 75
        return self.get_int('DB_POOL_SIZE', default)
    
    # =====================================================================
    # Redis Configuration
    # =====================================================================
    
    @property
    def redis_url(self) -> str:
        """Redis connection URL"""
        if self.is_development:
            return self.get_url('REDIS_URL', 'redis://localhost:6379/0')
        return self.get_url('REDIS_URL', required=True)
    
    @property
    def redis_max_memory(self) -> str:
        """Redis max memory setting"""
        default = '512mb' if self.is_development else '2gb'
        return self.get('REDIS_MAX_MEMORY', default)
    
    # =====================================================================
    # Celery Configuration
    # =====================================================================
    
    @property
    def celery_broker_url(self) -> str:
        """Celery broker URL"""
        return self.get('CELERY_BROKER_URL', self.redis_url)
    
    @property
    def celery_result_backend(self) -> str:
        """Celery result backend URL"""
        default = self.redis_url.replace('/0', '/1')
        return self.get('CELERY_RESULT_BACKEND', default)
    
    @property
    def celery_task_time_limit(self) -> int:
        """Celery task hard time limit in seconds"""
        default = 300 if self.is_development else 1800
        return self.get_int('CELERY_TASK_TIME_LIMIT', default)
    
    @property
    def celery_task_soft_time_limit(self) -> int:
        """Celery task soft time limit in seconds"""
        default = 240 if self.is_development else 1500
        return self.get_int('CELERY_TASK_SOFT_TIME_LIMIT', default)
    
    # =====================================================================
    # External Services
    # =====================================================================
    
    @property
    def use_mock_firebase(self) -> bool:
        """Check if mock Firebase should be used"""
        if not self.is_development:
            return False
        return self.get_bool('USE_MOCK_FIREBASE', True)
    
    @property
    def use_mock_openai(self) -> bool:
        """Check if mock OpenAI should be used"""
        if not self.is_development:
            return False
        return self.get_bool('USE_MOCK_OPENAI', False)
    
    @property
    def ai_provider(self) -> str:
        """Primary AI provider: 'openai' or 'llama'"""
        return self.get('AI_PROVIDER', 'openai').lower()

    @property
    def openai_api_key(self) -> Optional[str]:
        """OpenAI API key"""
        if self.use_mock_openai:
            return None

        # In production, require OpenAI key if it's the configured provider
        if not self.is_development and self.ai_provider == 'openai':
            return self.get('OPENAI_API_KEY', required=True)

        return self.get('OPENAI_API_KEY')

    @property
    def llama_api_key(self) -> Optional[str]:
        """Llama API key"""
        # In production, require Llama key if it's the configured provider
        if not self.is_development and self.ai_provider == 'llama':
            return self.get('LLAMA_API_KEY', required=True)

        return self.get('LLAMA_API_KEY')

    @property
    def llama_model(self) -> str:
        """Llama model name"""
        default = 'meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8'
        return self.get('LLAMA_MODEL', default)
    
    @property
    def firebase_credentials_path(self) -> Optional[str]:
        """Firebase credentials file path"""
        if self.use_mock_firebase:
            return None
        
        path = self.get_path('FIREBASE_CREDENTIALS_PATH')
        if not self.is_development and not path:
            raise ConfigurationError("Firebase credentials required in production")
        return path
    
    # =====================================================================
    # Security Configuration
    # =====================================================================
    
    @property
    def secure_ssl_redirect(self) -> bool:
        """HTTPS redirect setting"""
        return self.get_bool('SECURE_SSL_REDIRECT', not self.is_development)
    
    @property
    def session_cookie_secure(self) -> bool:
        """Secure session cookies"""
        return self.get_bool('SESSION_COOKIE_SECURE', not self.is_development)
    
    @property
    def csrf_cookie_secure(self) -> bool:
        """Secure CSRF cookies"""
        return self.get_bool('CSRF_COOKIE_SECURE', not self.is_development)
    
    @property
    def x_frame_options(self) -> str:
        """X-Frame-Options header value"""
        default = 'SAMEORIGIN' if self.is_development else 'DENY'
        return self.get('X_FRAME_OPTIONS', default)
    
    # =====================================================================
    # Network Configuration
    # =====================================================================
    
    @property
    def cors_allowed_origins(self) -> List[str]:
        """CORS allowed origins"""
        if self.is_development:
            default = [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://localhost:8000",
            ]
            return self.get_list('CORS_ALLOWED_ORIGINS', default)
        return self.get_list('CORS_ALLOWED_ORIGINS', [])
    
    # =====================================================================
    # Resource Limits
    # =====================================================================
    
    @property
    def file_upload_max_memory_size(self) -> int:
        """Max file upload size in bytes"""
        default = 10485760 if self.is_development else 5242880  # 10MB dev, 5MB prod
        return self.get_int('FILE_UPLOAD_MAX_MEMORY_SIZE', default)
    
    @property
    def max_prompt_length(self) -> int:
        """Maximum prompt length for validation"""
        default = 5000 if self.is_development else 2000
        return self.get_int('MAX_PROMPT_LENGTH', default)
    
    @property
    def max_code_length(self) -> int:
        """Maximum code length for validation"""
        default = 100000 if self.is_development else 50000
        return self.get_int('MAX_CODE_LENGTH', default)
    
    # =====================================================================
    # Code Execution Security
    # =====================================================================
    
    @property
    def code_exec_max_time(self) -> int:
        """Max code execution time in seconds"""
        default = 10 if self.is_development else 5
        return self.get_int('CODE_EXEC_MAX_TIME', default)
    
    @property
    def code_exec_max_memory(self) -> str:
        """Max memory for code execution"""
        default = '512m' if self.is_development else '256m'
        return self.get('CODE_EXEC_MAX_MEMORY', default)
    
    @property
    def code_exec_max_cpu(self) -> int:
        """Max CPU percentage for code execution"""
        default = 100 if self.is_development else 50
        return self.get_int('CODE_EXEC_MAX_CPU', default)

    @property
    def docker_pool_size(self) -> int:
        """Docker container pool size - environment specific"""
        # Development: Small pool (3) - faster startup, less memory
        # Production: Larger pool (15) - handles concurrent users
        default = 3 if self.is_development else 15
        return self.get_int('DOCKER_POOL_SIZE', default)
    
    # =====================================================================
    # Logging Configuration
    # =====================================================================
    
    @property
    def log_level(self) -> str:
        """Application log level"""
        default = 'DEBUG' if self.is_development else 'INFO'
        return self.get('LOG_LEVEL', default)
    
    @property
    def django_log_level(self) -> str:
        """Django log level"""
        default = 'DEBUG' if self.is_development else 'WARNING'
        return self.get('DJANGO_LOG_LEVEL', default)
    
    @property
    def log_file_paths(self) -> Dict[str, str]:
        """Log file paths"""
        if self.is_development:
            return {
                'django': self.get('DJANGO_LOG_FILE', 'logs/django.log'),
                'error': self.get('ERROR_LOG_FILE', 'logs/errors.log'),
                'access': self.get('ACCESS_LOG_FILE', 'logs/access.log'),
            }
        return {
            'django': self.get('DJANGO_LOG_FILE', '/app/logs/django.log'),
            'error': self.get('ERROR_LOG_FILE', '/app/logs/errors.log'),
            'access': self.get('ACCESS_LOG_FILE', '/app/logs/access.log'),
        }
    
    # =====================================================================
    # Feature Flags
    # =====================================================================
    
    @property
    def enable_eipl(self) -> bool:
        """Enable EiPL feature"""
        return self.get_bool('ENABLE_EIPL', True)
    
    @property
    def enable_hints(self) -> bool:
        """Enable hints feature"""
        return self.get_bool('ENABLE_HINTS', True)
    
    @property
    def enable_courses(self) -> bool:
        """Enable courses feature"""
        return self.get_bool('ENABLE_COURSES', True)
    
    @property
    def enable_debug_toolbar(self) -> bool:
        """Enable Django debug toolbar"""
        if self.is_production:
            return False  # Never in production
        return self.get_bool('ENABLE_DEBUG_TOOLBAR', self.is_development)
    
    # =====================================================================
    # Rate Limiting
    # =====================================================================
    
    @property
    def rate_limit_enabled(self) -> bool:
        """Check if rate limiting is enabled"""
        default = not self.is_development
        return self.get_bool('RATE_LIMIT_ENABLED', default)
    
    @property
    def rate_limit_per_minute(self) -> int:
        """Global rate limit per minute"""
        default = 1000 if self.is_development else 60
        return self.get_int('RATE_LIMIT_PER_MINUTE', default)
    
    @property
    def rate_limit_auth_per_minute(self) -> int:
        """Authentication rate limit per minute"""
        default = 100 if self.is_development else 5
        return self.get_int('RATE_LIMIT_AUTH_PER_MINUTE', default)
    
    # =====================================================================
    # Validation Methods
    # =====================================================================
    
    def validate_configuration(self) -> None:
        """
        Comprehensive configuration validation.
        Raises ConfigurationError if validation fails.
        """
        errors = []
        
        # Core Django settings
        try:
            if not self.secret_key:
                errors.append("Django SECRET_KEY is required")
        except ConfigurationError as e:
            errors.append(str(e))
        
        # Database validation
        try:
            if not self.database_url:
                errors.append("DATABASE_URL is required")
        except ConfigurationError as e:
            errors.append(str(e))
        
        # Redis validation
        try:
            if not self.redis_url:
                errors.append("REDIS_URL is required")
        except ConfigurationError as e:
            errors.append(str(e))
        
        # Production-specific checks
        if self.is_production:
            # Check allowed hosts
            try:
                hosts = self.allowed_hosts
                if not hosts or hosts == ['*']:
                    errors.append("Production requires DJANGO_ALLOWED_HOSTS (not ALLOWED_HOSTS) with specific IPs/domains")
            except ConfigurationError as e:
                errors.append(str(e))
            
            # Check Firebase
            if not self.use_mock_firebase and not self.firebase_credentials_path:
                errors.append("Firebase credentials required in production")
            
            # Check OpenAI
            if not self.use_mock_openai and not self.openai_api_key:
                errors.append("OpenAI API key required in production")
            
            # Security checks - only enforce if HTTPS is being used
            # Allow disabling SSL for HTTP deployments
            if self.get_bool('ENFORCE_SSL_IN_PRODUCTION', False):
                if not self.secure_ssl_redirect:
                    errors.append("SSL redirect must be enabled in production")
                if not self.session_cookie_secure:
                    errors.append("Secure session cookies must be enabled in production")
                if not self.csrf_cookie_secure:
                    errors.append("Secure CSRF cookies must be enabled in production")
            if self.debug:
                errors.append("DEBUG must be False in production")
            
            # Check for test/dev values
            secret = self.secret_key.lower()
            if 'test' in secret or 'development' in secret or 'dev' in secret:
                errors.append("Production cannot use development/test secret key")
        
        # Check log file paths are writable (if they exist)
        for log_type, path in self.log_file_paths.items():
            path_obj = Path(path)
            if path_obj.exists() and not os.access(path_obj.parent, os.W_OK):
                errors.append(f"Log directory not writable: {path_obj.parent}")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ConfigurationError(error_msg)
    
    def validate_security(self) -> None:
        """
        Validate security-specific configuration.
        This is a subset of validate_configuration focused on security.
        """
        if self.is_production:
            # Check for exposed secrets in common places
            # Skip path-related variables as they may legitimately contain 'test', 'demo', etc.
            sensitive_vars = ['PASSWORD', 'SECRET', 'KEY', 'TOKEN']
            path_vars = ['PATH', 'FILE', 'DIR', 'URL']
            
            for key in os.environ:
                # Skip if this is a path/file/directory variable
                if any(path in key.upper() for path in path_vars):
                    continue
                    
                for sensitive in sensitive_vars:
                    if sensitive in key.upper():
                        value = os.environ[key]
                        # Check for common weak values
                        weak_values = ['password', 'secret', 'admin', 'test', 'demo', '123']
                        if any(weak in value.lower() for weak in weak_values):
                            raise ConfigurationError(
                                f"Weak value detected for {key}"
                            )
    
    def get_config_summary(self) -> str:
        """Get a summary of current configuration (safe for logging)"""
        return (
            f"Purplex Configuration Summary:\n"
            f"  Environment: {self.env.value}\n"
            f"  Debug: {self.debug}\n"
            f"  Mock Firebase: {self.use_mock_firebase}\n"
            f"  Mock OpenAI: {self.use_mock_openai}\n"
            f"  SSL Redirect: {self.secure_ssl_redirect}\n"
            f"  Rate Limiting: {self.rate_limit_enabled}\n"
            f"  Features: EiPL={self.enable_eipl}, Hints={self.enable_hints}, Courses={self.enable_courses}\n"
            f"  Database: {'Configured' if self.database_url else 'Not configured'}\n"
            f"  Redis: {'Configured' if self.redis_url else 'Not configured'}"
        )


# Create singleton instance
config = Config()

# Perform validation
try:
    config.validate_configuration()
    config.validate_security()
    
    # Log configuration summary in development
    if config.is_development:
        print(config.get_config_summary())
        
except ConfigurationError as e:
    # In development, show warning but continue
    if config.is_development:
        print(f"⚠️  Configuration Warning (Development Mode):\n{e}")
    else:
        # In production/staging, fail fast
        print(f"❌ Configuration Error:\n{e}", file=sys.stderr)
        sys.exit(1)

# Export commonly used settings for convenience
DEBUG = config.debug
SECRET_KEY = config.secret_key
ALLOWED_HOSTS = config.allowed_hosts
DATABASE_URL = config.database_url