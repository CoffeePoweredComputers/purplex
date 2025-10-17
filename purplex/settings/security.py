"""Security configuration for code execution and other security-sensitive features."""
import os
from purplex.config.environment import config

# Code Execution Security Settings
CODE_EXECUTION = {
    # Execution limits
    'MAX_EXECUTION_TIME': config.code_exec_max_time,
    'MAX_MEMORY': config.code_exec_max_memory,
    'MAX_CPU_PERCENT': config.code_exec_max_cpu,
    'MAX_PROCESSES': config.get_int('CODE_EXEC_MAX_PROCESSES', 50),
    'MAX_FILE_DESCRIPTORS': config.get_int('CODE_EXEC_MAX_FILE_DESC', 64),
    'MAX_FILE_SIZE': config.get('CODE_EXEC_MAX_FILE_SIZE', '1m'),
    
    # Rate limiting
    'RATE_LIMIT_PER_MINUTE': config.get_int('RATE_LIMIT_SUBMIT_PER_MINUTE', 10),
    'RATE_LIMIT_PER_HOUR': config.get_int('CODE_EXEC_RATE_LIMIT_PER_HOUR', 100),
    
    # Docker configuration
    'DOCKER_IMAGE': os.environ.get('DOCKER_SANDBOX_IMAGE', 'purplex/python-sandbox:latest'),
    'DOCKER_NETWORK': 'none',  # No network access
    'DOCKER_USER': os.environ.get('DOCKER_USER', '1000:1000'),  # Non-root user
    'DOCKER_READ_ONLY': True,  # Read-only root filesystem
    'DOCKER_TMPFS_SIZE': os.environ.get('DOCKER_TMPFS_SIZE', '10m'),  # Temporary filesystem size
    
    # Container pooling configuration
    'POOL_ENABLED': config.get_bool('DOCKER_POOL_ENABLED', True),  # Enable container pooling for better performance
    'POOL_SIZE': config.docker_pool_size,  # Environment-specific: 3 (dev) / 15 (prod)

    # Container pool health monitoring
    'POOL_HEALTH_CHECK_INTERVAL': config.get_int('DOCKER_POOL_HEALTH_CHECK_INTERVAL', 60),  # Check every 60 seconds
    'POOL_CONTAINER_MAX_AGE': config.get_int('DOCKER_POOL_CONTAINER_MAX_AGE', 3600),  # Rotate containers after 1 hour
    'POOL_MAX_RESTART_ATTEMPTS': config.get_int('DOCKER_POOL_MAX_RESTART_ATTEMPTS', 3),  # Max restarts before removal

    # Security restrictions
    'ENABLE_NETWORK': False,
    'RUN_AS_ROOT': False,
    'ALLOW_FILE_WRITE': False,
    
    # Forbidden patterns in code
    'FORBIDDEN_IMPORTS': [
        'os', 'sys', 'subprocess', 'socket', 'requests',
        'urllib', 'http', 'ftplib', 'telnetlib', 'ssl',
        'pickle', 'shelve', 'marshal', 'importlib',
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input', 'raw_input'
    ],
    
    'FORBIDDEN_BUILTINS': [
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input', 'raw_input',
        'globals', 'locals', 'vars', 'dir',
        'getattr', 'setattr', 'delattr', 'hasattr',  # Prevent attribute access bypasses
        'chr', 'ord', 'hex', 'oct', 'bin',  # Prevent character encoding bypasses
        'bytes', 'bytearray', 'memoryview',  # Prevent byte manipulation
    ],
    
    # Logging
    'LOG_EXECUTIONS': config.get_bool('LOG_CODE_EXECUTIONS', True),
    'LOG_SUSPICIOUS_PATTERNS': config.get_bool('LOG_SUSPICIOUS_PATTERNS', True),
    'ALERT_ON_VIOLATIONS': config.get_bool('ALERT_ON_SECURITY_VIOLATIONS', True),
}

# Rate limiting for various endpoints
RATE_LIMITS = {
    'code_execution': {
        'per_minute': config.get_int('RATE_LIMIT_SUBMIT_PER_MINUTE', 10),
        'per_hour': config.get_int('CODE_EXEC_RATE_LIMIT_PER_HOUR', 100),
        'per_day': config.get_int('CODE_EXEC_RATE_LIMIT_PER_DAY', 500),
    },
    'ai_generation': {
        'per_minute': config.get_int('AI_RATE_LIMIT_PER_MINUTE', 5),
        'per_hour': config.get_int('AI_RATE_LIMIT_PER_HOUR', 30),
        'per_day': config.get_int('AI_RATE_LIMIT_PER_DAY', 100),
    },
    'authentication': {
        'login_per_hour': config.rate_limit_auth_per_minute * 60,  # Convert from per-minute to per-hour
        'register_per_day': config.get_int('REGISTER_RATE_LIMIT_PER_DAY', 5),
    }
}