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
cp .env.production .env.production.backup
cp .env.development .env.development.backup
```

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
2. Create `.env.local` for any personal overrides (gitignored)
3. The system will use sensible defaults for most settings

```bash
# Copy the development template
cp .env.development .env

# Edit with your specific values (especially API keys)
nano .env
```

#### For Production

1. Copy the production template:
```bash
cp .env.production.template .env.production
```

2. Fill in ALL required values:
   - Generate a new `DJANGO_SECRET_KEY`
   - Set proper `DJANGO_ALLOWED_HOSTS`
   - Configure database credentials
   - Add API keys (OpenAI, Firebase)
   - Set SSL certificate paths

3. Validate your configuration:
```bash
# Test configuration loading
python manage.py shell -c "from purplex.config.environment import config; print(config.get_config_summary())"
```

### Step 4: Update Docker Compose Files

If using Docker, update your compose files to use the new environment variables:

```yaml
# docker-compose.yml
services:
  web:
    env_file:
      - .env.production  # or .env.development
    environment:
      - PURPLEX_ENV=${PURPLEX_ENV}
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

### New Required Variables (Production)

These variables MUST be set in production:

- `PURPLEX_ENV=production`
- `DJANGO_SECRET_KEY` (newly generated)
- `DATABASE_URL` (PostgreSQL connection string)
- `REDIS_URL` (Redis connection string)
- `OPENAI_API_KEY` (unless using mock)
- `FIREBASE_CREDENTIALS_PATH` (unless using mock)

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
- `DJANGO_LOG_FILE` (default: /var/log/purplex/django.log)
- `ERROR_LOG_FILE` (default: /var/log/purplex/errors.log)
- `LOG_LEVEL` (default: INFO prod, DEBUG dev)

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
- Require HTTPS/SSL settings
- Disable debug mode
- Enforce rate limiting
- Validate Firebase and OpenAI credentials

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

#### 4. Log directory not writable

The application cannot write to the configured log paths.

**Solution**: Create the directories and set permissions:
```bash
sudo mkdir -p /var/log/purplex
sudo chown -R www-data:www-data /var/log/purplex
```

### Rollback Procedure

If you need to rollback to the old configuration:

1. Restore your backup files:
```bash
cp .env.backup .env
cp .env.production.backup .env.production
```

2. Revert the code changes:
```bash
git checkout -- purplex/config/environment.py
git checkout -- purplex/settings/
```

3. Restart your application

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
2. Review the `CONFIGURATION_SECURITY_CHECKLIST.md`
3. Test in development environment first
4. Use `python manage.py shell` to debug configuration issues

## Next Steps

After successful migration:

1. ✅ Delete old .env files that are no longer needed
2. ✅ Update your documentation
3. ✅ Train your team on the new configuration system
4. ✅ Set up monitoring for configuration-related errors
5. ✅ Schedule regular security audits
