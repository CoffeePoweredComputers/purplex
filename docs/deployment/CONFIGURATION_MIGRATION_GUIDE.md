# Configuration Management Migration Guide

## Overview

This guide helps you migrate from the old configuration system to the new enhanced configuration management system for Purplex. The new system provides:

- ✅ Comprehensive validation at startup
- ✅ Type-safe configuration access
- ✅ Security enforcement
- ✅ Environment-specific defaults
- ✅ Fail-fast validation in production

## Migration Steps

### Step 1: Backup Existing Configuration

Before starting the migration, backup your existing configuration files:

```bash
# Backup existing .env files
cp .env .env.backup

# If you have a production environment file
cp .env.production .env.production.backup 2>/dev/null || true
```

**Note**: `.env.development` is now a committed template file with safe defaults.

### Step 2: Choose Your Environment

The new system uses a single `PURPLEX_ENV` variable to control the environment:

- `development` - Local development with relaxed security
- `staging` - Pre-production testing
- `production` - Live production environment

Set this in your shell or .env file:

```bash
export PURPLEX_ENV=production  # or development, staging
```

### Step 3: Use the New Configuration Templates

#### For Development

1. Use the consolidated `.env.development` file as your base
2. Create `.env` for any personal overrides (gitignored)
3. The system will use sensible defaults for most settings

```bash
# Option 1: Copy the development template
cp .env.development .env

# Option 2: Source the development file directly
export $(cat .env.development | grep -v '^#' | xargs)

# Edit with your specific values (especially API keys)
nano .env
```

**Key settings to customize in development**:
- `OPENAI_API_KEY` - Your OpenAI API key (or set `USE_MOCK_OPENAI=true`)
- `LLAMA_API_KEY` - Your Llama API key if using Llama as AI provider
- `AI_PROVIDER` - Set to `openai` or `llama`

#### For Production

1. Copy the production template:
```bash
cp .env.production.template .env.production
```

2. Fill in ALL required values:
   - Generate a new `DJANGO_SECRET_KEY`:
     ```bash
     python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
     ```
   - Set `DJANGO_ALLOWED_HOSTS` with your domain/IP (no wildcards)
   - Configure `DATABASE_URL` with PostgreSQL connection string
   - Configure `REDIS_URL` with Redis connection string
   - Set `REDIS_PASSWORD` for production Redis authentication
   - Add `OPENAI_API_KEY` or `LLAMA_API_KEY` based on your AI provider
   - Set `FIREBASE_CREDENTIALS_PATH` to your credentials JSON file
   - Configure `POSTGRES_PASSWORD` for the database container

3. Validate your configuration:
```bash
# Set environment and load config
export PURPLEX_ENV=production
export $(cat .env.production | grep -v '^#' | xargs)

# Run Django deployment checks
python manage.py check --deploy

# Test configuration loading
python manage.py shell -c "from purplex.config.environment import config; print(config.get_config_summary())"
```

### Step 4: Update Docker Compose Files

If using Docker, the compose files use profiles to separate development and production:

```bash
# Development profile (uses .env.docker.development)
COMPOSE_PROFILES=development docker-compose up -d

# Production profile (uses .env.production)
COMPOSE_PROFILES=production docker-compose up -d
```

The Docker Compose file automatically:
- Uses `.env.production` for production services
- Uses `.env.docker.development` for development services
- Overrides database and Redis URLs with container hostnames
- Sets up Docker-in-Docker for secure code execution

Example production service configuration from `docker-compose.yml`:
```yaml
services:
  web:
    profiles:
      - production
    env_file:
      - .env.production
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres-prod:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis-prod:6379/0
      - DOCKER_HOST=tcp://dind:2375
```

### Step 5: Update CI/CD Pipelines

Update your deployment scripts to set the new environment variables:

```bash
# Example GitHub Actions
env:
  PURPLEX_ENV: production
  DJANGO_SECRET_KEY: ${{ secrets.DJANGO_SECRET_KEY }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  # ... other required variables
```

## Configuration Changes Reference

### Renamed Variables

| Old Variable | New Variable | Notes |
|-------------|--------------|-------|
| `DEBUG` | `DJANGO_DEBUG` | Now validated in production |
| `SECRET_KEY` | `DJANGO_SECRET_KEY` | Required in production |
| `ALLOWED_HOSTS` | `DJANGO_ALLOWED_HOSTS` | No wildcards in production |
| `OPENAI_KEY` | `OPENAI_API_KEY` | Consistent naming |
| `FIREBASE_CREDS` | `FIREBASE_CREDENTIALS_PATH` | Full path required |
| `AI_PROVIDER` | `AI_PROVIDER` | New: Choose between `openai` or `llama` |
| `LLAMA_API_KEY` | `LLAMA_API_KEY` | New: Required if AI_PROVIDER=llama |

### New Required Variables (Production)

These variables MUST be set in production:

- `PURPLEX_ENV=production`
- `DJANGO_SECRET_KEY` (newly generated)
- `DJANGO_ALLOWED_HOSTS` (comma-separated list of domains/IPs, no wildcards)
- `DATABASE_URL` (PostgreSQL connection string)
- `REDIS_URL` (Redis connection string)
- `OPENAI_API_KEY` (required if `AI_PROVIDER=openai`)
- `LLAMA_API_KEY` (required if `AI_PROVIDER=llama`)
- `FIREBASE_CREDENTIALS_PATH` (path to credentials JSON file)

### New Optional Variables

These variables have sensible defaults but can be customized:

#### Resource Limits
- `FILE_UPLOAD_MAX_MEMORY_SIZE` (default: 5MB prod, 10MB dev)
- `MAX_PROMPT_LENGTH` (default: 2000 prod, 5000 dev)
- `MAX_CODE_LENGTH` (default: 50000 prod, 100000 dev)
- `CODE_EXEC_MAX_TIME` (default: 5s prod, 10s dev)
- `CODE_EXEC_MAX_MEMORY` (default: 256m prod, 512m dev)

#### Rate Limiting
- `RATE_LIMIT_ENABLED` (default: true in prod)
- `RATE_LIMIT_PER_MINUTE` (default: 60 prod, 1000 dev)
- `RATE_LIMIT_AUTH_PER_MINUTE` (default: 5 prod, 100 dev)

#### Logging
- `DJANGO_LOG_FILE` (default: `/app/logs/django.log` prod, `logs/django.log` dev)
- `ERROR_LOG_FILE` (default: `/app/logs/errors.log` prod, `logs/errors.log` dev)
- `ACCESS_LOG_FILE` (default: `/app/logs/access.log` prod, `logs/access.log` dev)
- `LOG_LEVEL` (default: INFO prod, DEBUG dev)
- `DJANGO_LOG_LEVEL` (default: WARNING prod, DEBUG dev)

#### Docker Pool Health Monitoring
- `DOCKER_POOL_SIZE` (default: 30 prod, 3 dev)
- `DOCKER_POOL_HEALTH_CHECK_INTERVAL` (default: 60s prod, 120s dev)
- `DOCKER_POOL_CONTAINER_MAX_AGE` (default: 3600s prod, 7200s dev)
- `DOCKER_POOL_MAX_RESTART_ATTEMPTS` (default: 3)

## Validation and Testing

### 1. Test Configuration Loading

```python
# Run in Django shell
from purplex.config.environment import config

# Check environment
print(f"Environment: {config.env.value}")
print(f"Debug: {config.debug}")
print(f"Database: {config.database_url}")

# Validate configuration
config.validate_configuration()
config.validate_security()
```

### 2. Test Environment-Specific Behavior

```bash
# Test development mode
export PURPLEX_ENV=development
python manage.py runserver

# Test production mode (will fail if not properly configured)
export PURPLEX_ENV=production
python manage.py check --deploy
```

### 3. Verify Security Settings

In production, the system will automatically:
- Reject development/test secret keys
- Require HTTPS/SSL settings (if `ENFORCE_SSL_IN_PRODUCTION=true`)
- Disable debug mode
- Enforce rate limiting
- Validate Firebase and AI provider credentials (OpenAI or Llama)
- Reject wildcard allowed hosts

## SSL/HTTPS Configuration

The new configuration system has flexible SSL settings. Configure based on your deployment:

### With HTTPS (Recommended)
```bash
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
ENFORCE_SSL_IN_PRODUCTION=true
```

### Without HTTPS (Not Recommended for Production)
If deploying with HTTP only (e.g., internal network or behind a load balancer handling SSL):
```bash
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
ENFORCE_SSL_IN_PRODUCTION=false
```

**Important**: The `ENFORCE_SSL_IN_PRODUCTION` flag controls whether SSL validation is strict. When set to `true`, configuration validation will fail if SSL settings are not enabled.

## Troubleshooting

### Common Issues

#### 1. "Configuration validation failed"

This means required variables are missing. Check the error message for specifics:

```
Configuration validation failed:
  - Django SECRET_KEY is required
  - DATABASE_URL is required
```

**Solution**: Set the missing environment variables.

#### 2. "Production cannot use development/test secret key"

You're using an insecure secret key in production.

**Solution**: Generate a new secret key:
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

#### 3. "Mock services cannot be used in production"

Mock Firebase or OpenAI is enabled in production.

**Solution**: Set `USE_MOCK_FIREBASE=false` and `USE_MOCK_OPENAI=false`

#### 4. "OpenAI/Llama API key required"

The configured AI provider requires an API key.

**Solution**: Either set the API key or switch providers:
```bash
# For OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=your-key-here

# For Llama
AI_PROVIDER=llama
LLAMA_API_KEY=your-key-here
```

#### 5. "ALLOWED_HOSTS must be properly configured"

Production requires explicit allowed hosts.

**Solution**: Set specific domains/IPs (no wildcards):
```bash
# Correct
DJANGO_ALLOWED_HOSTS=purplex.org,www.purplex.org,54.123.45.67

# Wrong - wildcards not allowed in production
DJANGO_ALLOWED_HOSTS=*
```

#### 6. Log directory not writable

The application cannot write to the configured log paths.

**Solution**: Create the directories and set permissions:
```bash
# For local development
mkdir -p logs

# For Docker production (logs are mounted from host)
mkdir -p logs
# In Docker, logs are written to /app/logs which maps to ./logs on host
```

### Rollback Procedure

If you need to rollback to the old configuration:

1. Restore your backup files:
```bash
cp .env.backup .env
cp .env.production.backup .env.production
```

2. Restart your application:
```bash
# For Docker
COMPOSE_PROFILES=production docker-compose down
COMPOSE_PROFILES=production docker-compose up -d

# For local development
# Stop and restart ./start.sh
```

## Best Practices

1. **Never commit real credentials** - Use `.env.production.template` as a template
2. **Use environment-specific files** - Keep development and production configs separate
3. **Validate before deploying** - Run `config.validate_configuration()` before deployment
4. **Monitor logs** - Check application logs after deployment for configuration warnings
5. **Use secrets management** - Consider using AWS Secrets Manager, HashiCorp Vault, or similar for production
6. **Regular rotation** - Rotate secret keys and API keys regularly
7. **Backup configurations** - Keep encrypted backups of production configurations

## Support

If you encounter issues during migration:

1. Check the error messages - they're now more descriptive
2. Review the [Configuration Security Checklist](../security/CONFIGURATION_SECURITY_CHECKLIST.md)
3. See the full [Configuration Guide](./CONFIGURATION.md) for variable reference
4. Test in development environment first
5. Use `python manage.py shell` to debug configuration issues

### Quick Validation Commands

```bash
# Validate Django deployment settings
python manage.py check --deploy

# Test configuration in Django shell
python manage.py shell -c "from purplex.config.environment import config; config.validate_configuration(); print('OK')"

# View current configuration summary
python manage.py shell -c "from purplex.config.environment import config; print(config.get_config_summary())"
```

## Next Steps

After successful migration:

1. ✅ Delete old .env files that are no longer needed
2. ✅ Update your documentation
3. ✅ Train your team on the new configuration system
4. ✅ Set up monitoring for configuration-related errors
5. ✅ Schedule regular security audits
