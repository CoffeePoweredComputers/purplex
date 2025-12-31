# Purplex Configuration Guide

Complete guide to all environment variables used by Purplex. All configuration is managed through environment variables and validated by `purplex/config/environment.py`.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Environment Files](#environment-files)
3. [Variable Reference](#variable-reference)
4. [Security Best Practices](#security-best-practices)
5. [Deployment Validation](#deployment-validation)
6. [Common Configurations](#common-configurations)

---

## Quick Start

### Development Setup

```bash
# Copy development environment file
cp .env.development .env

# OR source it directly
export $(cat .env.development | grep -v '^#' | xargs)

# Start development server
./start.sh
```

### Production Setup

```bash
# Copy template and fill in values
cp .env.production.template .env.production

# Edit with your actual values
nano .env.production

# Validate configuration
export PURPLEX_ENV=production
export $(cat .env.production | grep -v '^#' | xargs)
python manage.py check --deploy

# Deploy with Docker Compose
docker-compose -f docker-compose.yml up -d
```

---

## Environment Files

| File | Purpose | Committed to Git? | Usage |
|------|---------|-------------------|-------|
| `.env.development` | Safe development defaults | Yes | Local development |
| `.env.production.template` | Production template | Yes | Template only |
| `.env.production` | Actual production config | **NO** | Production deployment |
| `.env.example` | Minimal example (legacy) | Yes | Basic reference |

**Security Rule**: Never commit files containing actual secrets (API keys, passwords, etc.)

---

## Variable Reference

### Core Environment

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PURPLEX_ENV` | Yes | `development` | Environment: `development`, `staging`, or `production` |

**Validation**: Must be one of the three allowed values. Determines which settings module is loaded and activates environment-specific defaults.

---

### Django Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | Yes (prod) | Dev: `dev-secret-key-...` | Django cryptographic signing key |
| `DJANGO_DEBUG` | No | Dev: `true`, Prod: `false` | Enable debug mode (MUST be false in production) |
| `DJANGO_ALLOWED_HOSTS` | Yes (prod) | Dev: `*`, Prod: required | Comma-separated list of allowed hostnames |
| `SERVER_URL` | No | Dev: `http://localhost:8000` | Internal server URL for link generation |

**Security Notes**:
- `DJANGO_SECRET_KEY`: Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `DJANGO_ALLOWED_HOSTS`: In production, NEVER use `*`. Must list actual domains/IPs.
- `DJANGO_DEBUG`: Validation fails if `true` in production

---

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes (prod) | Dev: Local PostgreSQL | Full PostgreSQL connection string |
| `DB_CONN_MAX_AGE` | No | Dev: `0`, Prod: `600` | Database connection max age in seconds |
| `DB_POOL_SIZE` | No | Dev: `5`, Prod: `75` | Connection pool size (increased for beta with gevent workers) |

**Format**: `postgresql://username:password@host:port/database` <!-- pragma: allowlist secret -->

**Examples**:
- Development: `postgresql://purplex_user:devpass@localhost:5432/purplex_dev` <!-- pragma: allowlist secret -->
- AWS RDS: `postgresql://purplex_user:STRONG_PASSWORD@purplex-db.abc123.us-east-1.rds.amazonaws.com:5432/purplex_prod` <!-- pragma: allowlist secret -->
- Docker: `postgresql://purplex_user:password@postgres:5432/purplex_prod` <!-- pragma: allowlist secret -->

---

### Redis Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes (prod) | Dev: `redis://localhost:6379/0` | Full Redis connection string |
| `REDIS_HOST` | No | Derived from `REDIS_URL` | Redis hostname |
| `REDIS_PORT` | No | `6379` | Redis port |
| `REDIS_MAX_MEMORY` | No | Dev: `512mb`, Prod: `2gb` | Redis memory limit |

**Format**: `redis://host:port/database`

**Examples**:
- Development: `redis://localhost:6379/0`
- AWS ElastiCache: `redis://purplex-redis.abc123.cache.amazonaws.com:6379/0`
- Docker: `redis://redis:6379/0`

**Note**: By default, Celery uses database 0 for broker and database 1 for results. The `.env.example` template uses databases 1/2 to keep database 0 separate for caching.

---

### Celery Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CELERY_BROKER_URL` | No | Same as `REDIS_URL` | Message broker URL (Redis database 0) |
| `CELERY_RESULT_BACKEND` | No | `REDIS_URL` with `/1` | Result backend URL (Redis database 1) |
| `CELERY_TASK_TIME_LIMIT` | No | Dev: `300`, Prod: `1800` | Hard task timeout in seconds |
| `CELERY_TASK_SOFT_TIME_LIMIT` | No | Dev: `240`, Prod: `1500` | Soft task timeout in seconds |
| `CELERY_MAX_TASKS_PER_CHILD` | No | `1000` | Max tasks per worker before restart |
| `CELERY_EAGER` | No | `false` | Run tasks synchronously (dev only) |

**Worker Count**: Set via Docker Compose `CELERY_WORKERS` environment variable

---

### External Services

#### Firebase Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_MOCK_FIREBASE` | No | Dev: `true`, Prod: `false` | Use mock Firebase (dev only) |
| `FIREBASE_CREDENTIALS_PATH` | Yes (prod) | None | Path to Firebase service account JSON |

**Production Setup**:
1. Download service account JSON from Firebase Console
2. Upload to server (e.g., `/app/firebase-credentials.json`)
3. Set `FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json`
4. Ensure file is NOT in version control

**Validation**: Production fails if `USE_MOCK_FIREBASE=true`

#### AI Provider Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_PROVIDER` | No | `openai` | Primary AI provider: `openai` or `llama` |

**Note**: The configured provider's API key is required in production. If `AI_PROVIDER=llama`, then `LLAMA_API_KEY` is required; if `AI_PROVIDER=openai`, then `OPENAI_API_KEY` is required.

#### OpenAI Integration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_MOCK_OPENAI` | No | `false` | Use mock OpenAI (dev only) |
| `OPENAI_API_KEY` | Yes (if AI_PROVIDER=openai) | None | OpenAI API key |
| `GPT_MODEL` | No | `gpt-4o-mini` | OpenAI model to use |

**Getting API Key**: https://platform.openai.com/api-keys

**Validation**: Production fails if `USE_MOCK_OPENAI=true`

#### Llama Integration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLAMA_API_KEY` | Yes (if AI_PROVIDER=llama) | None | Meta Llama API key |
| `LLAMA_MODEL` | No | `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8` | Llama model to use |

**Getting API Key**: https://www.llama.com/ (currently FREE beta access)

**Note**: When `AI_PROVIDER=llama`, Llama is used as the primary AI provider for all AI-powered features.

---

### Security Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECURE_SSL_REDIRECT` | No | Dev: `false`, Prod: `true` (code default) | Redirect HTTP to HTTPS |
| `SESSION_COOKIE_SECURE` | No | Dev: `false`, Prod: `true` (code default) | Require HTTPS for session cookies |
| `CSRF_COOKIE_SECURE` | No | Dev: `false`, Prod: `true` (code default) | Require HTTPS for CSRF cookies |
| `ENFORCE_SSL_IN_PRODUCTION` | No | `false` | Fail validation if SSL not configured |
| `X_FRAME_OPTIONS` | No | Dev: `SAMEORIGIN`, Prod: `DENY` | X-Frame-Options header |

**Note**: While the code defaults SSL settings to `true` in production, the `.env.production.template` sets them to `false` to support HTTP deployments. Override to `true` when using HTTPS.

**IMPORTANT**: If deploying with HTTP (not recommended), set SSL settings to `false`:
```bash
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
ENFORCE_SSL_IN_PRODUCTION=false
```

**RECOMMENDED**: Use HTTPS in production with Let's Encrypt or AWS Certificate Manager

---

### Network Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ALLOWED_ORIGINS` | Yes (prod) | Dev: localhost URLs | Comma-separated allowed CORS origins |
| `CSRF_TRUSTED_ORIGINS` | Yes (prod) | None | Comma-separated trusted origins for CSRF |

**Examples**:
```bash
# Development
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://localhost:8000

# Production with HTTPS
CORS_ALLOWED_ORIGINS=https://purplex.example.com,https://www.purplex.example.com
CSRF_TRUSTED_ORIGINS=https://purplex.example.com,https://api.purplex.example.com

# Production with HTTP (not recommended)
CORS_ALLOWED_ORIGINS=http://purplex.example.com
CSRF_TRUSTED_ORIGINS=http://purplex.example.com
```

---

### Resource Limits

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | No | Dev: `10485760`, Prod: `5242880` | Max file upload size in bytes |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | No | Same as file upload | Max request body size in bytes |
| `MAX_PROMPT_LENGTH` | No | Dev: `5000`, Prod: `2000` | Max EiPL prompt length |
| `MAX_CODE_LENGTH` | No | Dev: `100000`, Prod: `50000` | Max code submission length |

**Default Sizes**:
- Development: 10MB uploads, 5000 char prompts
- Production: 5MB uploads, 2000 char prompts

---

### Code Execution Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CODE_EXEC_MAX_TIME` | No | Dev: `10`, Prod: `5` | Max execution time in seconds |
| `CODE_EXEC_MAX_MEMORY` | No | Dev: `512m`, Prod: `256m` | Max memory for code execution |
| `CODE_EXEC_MAX_CPU` | No | Dev: `100`, Prod: `50` | Max CPU percentage |
| `DOCKER_POOL_SIZE` | No | Dev: `3`, Prod: `30` | Number of pre-warmed Docker containers in the pool |

**Security**: All code runs in isolated Docker containers with these hard limits

**Docker Pool Sizing**: Each EiPL submission tests 5 code variations, so a pool of 30 containers supports approximately 6 concurrent EiPL submissions. Adjust based on expected concurrent load.

#### Docker Pool Health Monitoring

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DOCKER_POOL_HEALTH_CHECK_INTERVAL` | No | Dev: `120`, Prod: `60` | Seconds between container health checks |
| `DOCKER_POOL_CONTAINER_MAX_AGE` | No | Dev: `7200`, Prod: `3600` | Maximum container age in seconds before rotation |
| `DOCKER_POOL_MAX_RESTART_ATTEMPTS` | No | `3` | Max restart attempts before removing unhealthy container |

**Health Monitoring Features**:
- **Background Thread**: Checks container pool health every 60-120 seconds
- **Age-Based Rotation**: Containers older than max age are automatically replaced
- **Unhealthy Container Detection**: Non-running containers are removed and replaced
- **Graceful Degradation**: Falls back to one-off containers if Docker daemon fails
- **Metrics Tracking**: Pool size, health checks, rotations, and errors are logged
- **Zero Performance Impact**: Health checks run in daemon thread, don't block execution

**Tuning Recommendations**:
- **Development**: Longer intervals (120s), higher max age (2 hours) for less churn
- **Production**: Shorter intervals (60s), lower max age (1 hour) to prevent memory leaks
- **High Load**: Consider interval=30s with larger pool size

**Monitoring**: All health events reported to logs and Sentry (if configured)

---

### Logging Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | Dev: `DEBUG`, Prod: `INFO` | Application log level |
| `DJANGO_LOG_LEVEL` | No | Dev: `DEBUG`, Prod: `WARNING` | Django framework log level |
| `DJANGO_LOG_FILE` | No | Dev: `logs/django.log`, Prod: `/app/logs/django.log` | Django log file path |
| `ERROR_LOG_FILE` | No | Dev: `logs/errors.log`, Prod: `/app/logs/errors.log` | Error log file path |
| `ACCESS_LOG_FILE` | No | Dev: `logs/access.log`, Prod: `/app/logs/access.log` | Access log file path |
| `LOG_SQL_QUERIES` | No | `false` | Log all SQL queries (very verbose) |

**Log Levels**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

---

### Feature Flags

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENABLE_EIPL` | No | `true` | Enable Explain in Plain Language feature |
| `ENABLE_HINTS` | No | `true` | Enable hints system |
| `ENABLE_COURSES` | No | `true` | Enable course management |
| `ENABLE_DEBUG_TOOLBAR` | No | Dev: `true`, Prod: `false` | Enable Django Debug Toolbar |
| `SHOW_DEBUG_TOOLBAR` | No | `false` | Actually display the debug toolbar (requires ENABLE_DEBUG_TOOLBAR) |
| `ENABLE_QUERY_LOGGING` | No | `false` | Log SQL queries (development debugging) |
| `ENABLE_REQUEST_LOGGING` | No | Dev: `true`, Prod: `false` | Log HTTP requests |

**Production**: Debug toolbar is always disabled in production regardless of settings

---

### Development-Specific Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEST_USER_PASSWORD` | No | `testpass123` | Password for test users in development |
| `LOG_SQL_QUERIES` | No | `false` | Alias for ENABLE_QUERY_LOGGING |

**Note**: These settings only apply in development mode.

---

### Rate Limiting

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | No | Prod: `true` | Enable rate limiting |
| `RATE_LIMIT_PER_MINUTE` | No | Dev: `1000`, Prod: `60` | Global rate limit per minute |
| `RATE_LIMIT_AUTH_PER_MINUTE` | No | Dev: `100`, Prod: `5` | Auth endpoint rate limit per minute |

**Recommendation**: Always enable in production to prevent abuse

---

### Gunicorn Settings (Production)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GUNICORN_WORKERS` | No | `2 * CPU + 1` | Number of worker processes |
| `GUNICORN_TIMEOUT` | No | `30` | Worker timeout in seconds |
| `GUNICORN_GRACEFUL_TIMEOUT` | No | `30` | Graceful worker timeout for restart |
| `GUNICORN_WORKER_CLASS` | No | `sync` | Worker class (`sync`, `gevent`, etc.) |
| `GUNICORN_THREADS` | No | `4` | Threads per worker (sync only) |
| `GUNICORN_WORKER_CONNECTIONS` | No | `1000` | Connections per worker (gevent only) |
| `GUNICORN_MAX_REQUESTS` | No | `1000` | Max requests before worker restart |
| `GUNICORN_MAX_REQUESTS_JITTER` | No | `50` | Random jitter added to max requests |
| `GUNICORN_LOG_LEVEL` | No | `info` | Gunicorn log level |
| `GUNICORN_ACCESS_LOG` | No | `/app/logs/access.log` | Access log path |
| `GUNICORN_ERROR_LOG` | No | `/app/logs/error.log` | Error log path |
| `WEB_PORT` | No | `8000` | Port to bind to |
| `CELERY_WORKERS` | No | `4` | Number of Celery worker processes |

**Worker Count Formula**: `2 * CPU_CORES + 1`
- AWS t3.medium (2 vCPUs): 5 workers
- AWS t3.large (2 vCPUs): 5 workers
- AWS c5.xlarge (4 vCPUs): 9 workers

---

### Email Configuration (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMAIL_BACKEND` | No | Dev: `console`, Prod: `smtp` | Email backend |
| `EMAIL_HOST` | No | `smtp.gmail.com` | SMTP server hostname |
| `EMAIL_PORT` | No | `587` | SMTP server port |
| `EMAIL_USE_TLS` | No | `true` | Use TLS for SMTP |
| `EMAIL_HOST_USER` | No | None | SMTP username |
| `EMAIL_HOST_PASSWORD` | No | None | SMTP password |
| `DEFAULT_FROM_EMAIL` | No | `noreply@purplex.com` | Default sender email |
| `SERVER_EMAIL` | No | `server@purplex.com` | Server error email |
| `ADMIN_EMAIL` | No | None | Admin notification email |

---

### Monitoring (Optional but Recommended)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | No | None | Sentry error tracking DSN |
| `SENTRY_ENVIRONMENT` | No | Dev: `development`, Prod: `production` | Sentry environment name |
| `SENTRY_RELEASE` | No | None | Sentry release version (git commit SHA recommended) |
| `SENTRY_TRACES_SAMPLE_RATE` | No | `0.1` | Percentage of transactions to sample (0.0-1.0) |
| `SENTRY_PROFILES_SAMPLE_RATE` | No | `0.0` | Percentage of profiles to sample (0.0-1.0) |

**Setup**: Create account at https://sentry.io/ and get DSN

**Free Tier Limits**:
- 5,000 error events/month
- 10,000 performance transactions/month
- Unlimited team members

**Configuration**:
```bash
# 1. Sign up at https://sentry.io
# 2. Create new project → Select "Django"
# 3. Copy DSN and add to .env:
SENTRY_DSN=https://your-key@your-org.ingest.sentry.io/your-project-id

# 4. Adjust sampling rates based on traffic:
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of transactions
SENTRY_PROFILES_SAMPLE_RATE=0.0  # Disabled (conserve quota)

# 5. Set release via CI/CD (recommended):
SENTRY_RELEASE=$(git rev-parse HEAD)
```

**Custom Sampling Logic**:
Purplex uses intelligent sampling to prioritize critical paths within free tier limits:
- **EiPL submissions**: 100% sampled (always monitored)
- **API endpoints**: 50% sampled
- **Health checks**: 5% sampled
- **Admin pages**: 10% sampled
- **Other requests**: 10% sampled (default)

This ensures critical user-facing operations are always monitored while conserving quota for less important endpoints.

**Health Check Endpoints**:
- `/health/` - Simple text health check (for Nginx/load balancers)
- `/api/health/` - Comprehensive JSON health check (database, cache, Celery)
- `/api/health/ready/` - Kubernetes-style readiness probe
- `/api/health/live/` - Kubernetes-style liveness probe

All health endpoints require **no authentication** and are safe to expose to monitoring services.

---

### AWS-Specific Settings (Optional)

These settings are only used when deploying to AWS and using the `aws` settings module.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_REGION` | No | `us-east-1` | AWS region for services |
| `INITIAL_DEPLOYMENT` | No | `false` | Allow wildcard ALLOWED_HOSTS during initial setup |
| `CORS_ALLOW_ALL` | No | `false` | Allow all CORS origins (development only) |
| `USE_S3` | No | `false` | Use S3 for static file storage |
| `AWS_STORAGE_BUCKET_NAME` | If USE_S3 | None | S3 bucket name for static files |
| `AWS_ACCESS_KEY_ID` | If USE_S3 | None | AWS access key for S3 |
| `AWS_SECRET_ACCESS_KEY` | If USE_S3 | None | AWS secret key for S3 |
| `AWS_S3_REGION_NAME` | No | `us-east-1` | S3 bucket region |
| `AWS_S3_CUSTOM_DOMAIN` | No | None | Custom domain for S3 (CloudFront) |
| `USE_CLOUDWATCH` | No | `false` | Enable CloudWatch logging |
| `USE_ELASTICACHE` | No | `false` | Use ElastiCache for Redis |
| `ELASTICACHE_ENDPOINT` | If USE_ELASTICACHE | `redis` | ElastiCache endpoint |
| `USE_RDS` | No | `false` | Use RDS for PostgreSQL |
| `RDS_DB_NAME` | If USE_RDS | None | RDS database name |
| `RDS_USERNAME` | If USE_RDS | None | RDS username |
| `RDS_PASSWORD` | If USE_RDS | None | RDS password |
| `RDS_HOSTNAME` | If USE_RDS | None | RDS hostname |
| `RDS_PORT` | No | `5432` | RDS port |
| `USE_SECRETS_MANAGER` | No | `false` | Load secrets from AWS Secrets Manager |
| `USE_SES` | No | `false` | Use AWS SES for email |
| `AWS_SES_REGION_NAME` | No | `us-east-1` | SES region |
| `USE_XRAY` | No | `false` | Enable AWS X-Ray tracing |

**Note**: When `USE_SECRETS_MANAGER=true`, database credentials and other secrets are automatically loaded from AWS Secrets Manager.

---

## Security Best Practices

### 1. Secret Management

**DO**:
- Use environment variables for all secrets
- Generate unique random values for `DJANGO_SECRET_KEY`
- Store production `.env` files securely (AWS Secrets Manager, encrypted storage)
- Use different secrets for each environment

**DON'T**:
- Commit `.env.production` to version control
- Reuse development secrets in production
- Share secrets via email or chat
- Use weak or obvious passwords

### 2. Production Checklist

Before deploying to production:

```bash
# 1. Validate environment
python manage.py check --deploy

# 2. Check for security issues
python manage.py check --deploy --fail-level WARNING

# 3. Verify configuration
python -c "from purplex.config.environment import config; print(config.get_config_summary())"

# 4. Test database connection
python manage.py migrate --check

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Run tests
pytest
```

### 3. Configuration Validation

The `environment.py` module validates:
- ✅ Required variables are set
- ✅ No development/test values in production
- ✅ Mock services disabled in production
- ✅ Debug mode is off in production
- ✅ SSL settings match environment
- ✅ Allowed hosts are specific (not wildcard)
- ✅ Weak passwords are rejected

**Validation Failures**: Application will not start if validation fails

---

## Deployment Validation

### Step 1: Basic Validation

```bash
# Set environment
export PURPLEX_ENV=production

# Load environment file
export $(cat .env.production | grep -v '^#' | xargs)

# Run Django checks
python manage.py check --deploy
```

### Step 2: Configuration Review

```bash
# View configuration summary (secrets are hidden)
python -c "from purplex.config.environment import config; print(config.get_config_summary())"
```

Expected output:
```
Purplex Configuration Summary:
  Environment: production
  Debug: False
  Mock Firebase: False
  Mock OpenAI: False
  SSL Redirect: True
  Rate Limiting: True
  Features: EiPL=True, Hints=True, Courses=True
  Database: Configured
  Redis: Configured
```

### Step 3: Database Validation

```bash
# Test database connection
python manage.py migrate --check

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Step 4: Static Files

```bash
# Collect static files
python manage.py collectstatic --noinput

# Verify static files
ls -la staticfiles/
```

### Step 5: Service Tests

```bash
# Test Redis connection
redis-cli -h $REDIS_HOST ping

# Test Celery worker
celery -A purplex.celery_simple inspect ping

# Test OpenAI API (if configured)
python -c "import openai; openai.api_key='$OPENAI_API_KEY'; print(openai.Model.list())"
```

---

## Common Configurations

### Local Development (HTTP)

```bash
PURPLEX_ENV=development
DJANGO_DEBUG=true
USE_MOCK_FIREBASE=true
USE_MOCK_OPENAI=false
DATABASE_URL=postgresql://purplex_user:devpass@localhost:5432/purplex_dev  # pragma: allowlist secret
REDIS_URL=redis://localhost:6379/0

# AI Provider (choose one)
AI_PROVIDER=llama  # or 'openai'
LLAMA_API_KEY=your-llama-key-here  # Free beta access at llama.com
OPENAI_API_KEY=your-openai-key-here
```

### Production AWS EC2 (HTTP - Simple)

```bash
PURPLEX_ENV=production
DJANGO_SECRET_KEY=<generated-secret>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=54.123.45.67,purplex.example.com
DATABASE_URL=postgresql://purplex_user:STRONG_PASSWORD@postgres:5432/purplex_prod  # pragma: allowlist secret
REDIS_URL=redis://redis:6379/0
FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json

# AI Provider (configure the one you're using)
AI_PROVIDER=openai  # or 'llama'
OPENAI_API_KEY=<your-openai-key>
# LLAMA_API_KEY=<your-llama-key>  # Alternative: use Llama instead

SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
CORS_ALLOWED_ORIGINS=http://54.123.45.67,http://purplex.example.com
```

### Production AWS with RDS & ElastiCache (HTTPS)

```bash
PURPLEX_ENV=production
DJANGO_SECRET_KEY=<generated-secret>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=purplex.example.com,www.purplex.example.com
SERVER_URL=https://purplex.example.com
DATABASE_URL=postgresql://purplex_user:STRONG_PASSWORD@purplex-db.abc123.us-east-1.rds.amazonaws.com:5432/purplex_prod  # pragma: allowlist secret
REDIS_URL=redis://purplex-redis.abc123.cache.amazonaws.com:6379/0
FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json

# AI Provider
AI_PROVIDER=openai
OPENAI_API_KEY=<your-openai-key>

SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
ENFORCE_SSL_IN_PRODUCTION=true
CORS_ALLOWED_ORIGINS=https://purplex.example.com,https://www.purplex.example.com
CSRF_TRUSTED_ORIGINS=https://purplex.example.com,https://api.purplex.example.com
RATE_LIMIT_ENABLED=true
```

---

## Common Mistakes to Avoid

### 1. Wildcard Allowed Hosts in Production
```bash
# ❌ WRONG
DJANGO_ALLOWED_HOSTS=*

# ✅ CORRECT
DJANGO_ALLOWED_HOSTS=purplex.example.com,54.123.45.67
```

### 2. Using Development Secret Key
```bash
# ❌ WRONG (contains 'dev')
DJANGO_SECRET_KEY=dev-secret-key-12345

# ✅ CORRECT
DJANGO_SECRET_KEY=uj*8h#kl2jh$lk3j4h5lk2j3h4lkj5h2lk3j4h
```

### 3. Mock Services in Production
```bash
# ❌ WRONG
USE_MOCK_FIREBASE=true

# ✅ CORRECT
USE_MOCK_FIREBASE=false
FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json
```

### 4. Missing Protocol in URLs
```bash
# ❌ WRONG
CORS_ALLOWED_ORIGINS=purplex.example.com

# ✅ CORRECT
CORS_ALLOWED_ORIGINS=https://purplex.example.com
```

### 5. Wrong Redis Database for Celery
```bash
# ❌ WRONG (both use same database)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ✅ CORRECT (different databases)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 6. SSL Settings Mismatch
```bash
# ❌ WRONG (SSL redirect enabled but cookies not secure)
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=false

# ✅ CORRECT (all SSL settings match)
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

### 7. Insufficient Worker Resources
```bash
# ❌ WRONG (too few workers for production)
GUNICORN_WORKERS=2

# ✅ CORRECT (formula: 2 * CPU + 1)
# For 2 vCPU instance:
GUNICORN_WORKERS=5
```

---

## Troubleshooting

### Configuration Validation Fails

```bash
# Error: "Required configuration missing: DJANGO_SECRET_KEY"
# Solution: Set the variable in .env.production

# Error: "Production cannot use development/test secret key"
# Solution: Generate a new secret key

# Error: "ALLOWED_HOSTS must be properly configured"
# Solution: Set specific domains/IPs, not '*'
```

### Database Connection Fails

```bash
# Check connection string format
echo $DATABASE_URL

# Test direct connection
psql $DATABASE_URL

# Verify host is reachable
ping <database-host>
```

### Redis Connection Fails

```bash
# Check connection string
echo $REDIS_URL

# Test direct connection
redis-cli -h <redis-host> ping

# Check Redis is running
docker ps | grep redis
```

### SSL Issues

```bash
# If not using HTTPS, disable SSL settings:
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false

# If using HTTPS, ensure certificate is valid:
curl -v https://your-domain.com
```

---

## Additional Resources

- Django Settings Documentation: https://docs.djangoproject.com/en/5.0/ref/settings/
- Django Deployment Checklist: https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/
- Gunicorn Configuration: https://docs.gunicorn.org/en/stable/settings.html
- Celery Configuration: https://docs.celeryq.dev/en/stable/userguide/configuration.html
- AWS RDS Guide: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/
- AWS ElastiCache Guide: https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/
