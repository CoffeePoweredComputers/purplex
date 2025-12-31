# Docker Deployment Guide

## Overview

Purplex uses Docker Compose with **profile-based configuration** to support both development and production environments. This guide covers deployment procedures, container management, and troubleshooting.

## Architecture

### Networks

- **frontend** (172.20.0.0/24): Public-facing services (nginx)
- **backend** (172.21.0.0/24): Application services (web, celery)
- **database** (172.22.0.0/24): Database isolation (postgres, redis)

### Resource Limits

Production services have configured limits:
- **PostgreSQL**: 1.5 CPU cores, 4GB RAM (2GB reserved)
- **Web**: 2.5 CPU cores, 3.5GB RAM (2GB reserved)
- **Celery**: 3.4 CPU cores, 4.5GB RAM (3GB reserved)
- **Redis**: 0.3 CPU cores, 2.5GB RAM with 2GB maxmemory (LRU eviction)
- **Nginx**: 0.2 CPU cores, 512MB RAM
- **Celery Beat**: 0.1 CPU cores, 256MB RAM

## Quick Start

### Development Environment

```bash
# Start development stack
COMPOSE_PROFILES=development docker-compose up -d

# Services included:
# - postgres (port 5432)
# - redis (port 6379)
# - web-dev (port 8000)
# - celery-dev
# - celery-beat-dev (periodic tasks)
# - frontend-dev (port 5173)

# View logs
docker-compose logs -f web-dev

# Stop all services
docker-compose down
```

### Production Environment

```bash
# Start production stack
COMPOSE_PROFILES=production docker-compose up -d

# Services included:
# - postgres-prod (PostgreSQL database)
# - redis-prod (Redis cache/broker)
# - web (Django behind nginx)
# - celery (async task workers)
# - celery-beat (periodic tasks scheduler)
# - nginx (reverse proxy, ports 80/443)
# - certbot (SSL certificate management)
# - dind (Docker-in-Docker for secure code execution)

# Check service health
docker-compose ps

# View logs
docker-compose logs -f web celery
```

## Deployment Procedures

### Initial Production Deployment

1. **Prepare environment file**:
   ```bash
   cp .env.production.template .env.production
   # Edit .env.production with production values
   # Key variables: POSTGRES_*, REDIS_PASSWORD, DJANGO_SECRET_KEY, OPENAI_API_KEY
   ```

   For development, Docker uses `.env.docker.development` (already configured with defaults).

2. **Build images**:
   ```bash
   COMPOSE_PROFILES=production docker-compose build
   ```

3. **Start services**:
   ```bash
   COMPOSE_PROFILES=production docker-compose up -d
   ```

4. **Run migrations**:
   ```bash
   docker-compose exec web python manage.py migrate
   ```

5. **Collect static files**:
   ```bash
   docker-compose exec web python manage.py collectstatic --noinput
   ```

6. **Create superuser**:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

### Updating Production

```bash
# Pull latest code
git pull origin main

# Rebuild images
COMPOSE_PROFILES=production docker-compose build

# Restart services with zero-downtime
docker-compose up -d --no-deps web celery

# Run migrations if needed
docker-compose exec web python manage.py migrate
```

## Container Cleanup

### Automatic Cleanup (Recommended)

The system includes **automatic cleanup** via Celery Beat:
- **Hourly**: Removes orphaned sandbox containers
- **Every 15 minutes**: Logs pool metrics

Ensure `celery-beat` or `celery-beat-dev` is running.

### Manual Cleanup

```bash
# Use provided cleanup script
./scripts/docker-cleanup.sh

# Force mode (no prompts)
./scripts/docker-cleanup.sh --force

# Manual docker commands
docker ps -a --filter "status=exited" --filter "label=purplex-pool=true" -q | xargs docker rm
```

### Cron Job Setup

Add to crontab for automated cleanup:
```bash
# Run cleanup every hour
0 * * * * /path/to/purplex/scripts/docker-cleanup.sh --force >> /var/log/purplex-cleanup.log 2>&1
```

## Monitoring

### Health Checks

All production services have health checks:

```bash
# Check service health status
docker-compose ps

# View health check logs
docker inspect purplex_postgres | grep -A 10 Health
```

### Resource Usage

```bash
# Current resource usage
docker stats

# Disk usage
docker system df
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web

# Last 100 lines
docker-compose logs --tail=100 celery

# Since timestamp
docker-compose logs --since 2025-01-01T00:00:00
```

## Troubleshooting

### Container Accumulation

**Problem**: Hundreds of exited sandbox containers

**Solution**:
1. Run cleanup script: `./scripts/docker-cleanup.sh --force`
2. Verify celery-beat is running for automatic cleanup
3. Check logs: `docker-compose logs celery-beat-dev`

### Service Won't Start

```bash
# Check logs for specific service
docker-compose logs <service-name>

# Check container status
docker-compose ps

# Restart specific service
docker-compose restart <service-name>

# Full restart
docker-compose down && docker-compose up -d
```

### Database Connection Issues

```bash
# Check postgres health
docker-compose exec postgres-prod pg_isready

# Test connection from web container
docker-compose exec web python manage.py dbshell

# View postgres logs
docker-compose logs postgres-prod
```

### Redis Connection Issues

```bash
# Test Redis connection (production requires password)
docker-compose exec redis-prod redis-cli -a $REDIS_PASSWORD ping

# Check Redis info
docker-compose exec redis-prod redis-cli -a $REDIS_PASSWORD info

# View Redis logs
docker-compose logs redis-prod

# Development (no password required)
docker-compose exec redis redis-cli ping
```

### Out of Memory

If services are OOMKilled:

1. Check current limits:
   ```bash
   docker-compose config | grep -A 5 "resources:"
   ```

2. Adjust in docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 8G  # Increase as needed
   ```

3. Restart affected service:
   ```bash
   docker-compose up -d --no-deps <service>
   ```

### SSL Certificate Issues

```bash
# Manual certificate renewal
docker-compose exec certbot certbot renew

# Check certificate status
docker-compose exec certbot certbot certificates

# View certbot logs
docker-compose logs certbot
```

## Security Best Practices

### Docker-in-Docker (DinD) for Code Execution

Production uses Docker-in-Docker (dind service) instead of mounting the host Docker socket. Web and Celery connect via `DOCKER_HOST=tcp://dind:2375`.

**Security measures in place**:
- DinD runs on internal backend network only (no external access)
- Web/Celery containers run with `security_opt: no-new-privileges`
- Web/Celery containers have `cap_drop: ALL` with minimal capabilities
- AppArmor profiles applied (`apparmor:docker-default`)
- Sandbox containers are network-isolated (network_mode: none)
- Resource limits prevent resource exhaustion
- Read-only root filesystem in sandbox containers
- Non-root user execution (uid 1000)

### Network Isolation

Production services use separate networks:
- Database network is **internal only** (no external access)
- Backend network allows controlled outbound for APIs
- Frontend network only exposes nginx

### Secrets Management

**Never commit**:
- `.env.production`
- `firebase-credentials.json`

**Use**:
- AWS Secrets Manager for production (see AWS_DEPLOYMENT_GUIDE.md)
- Strong passwords generated with: `openssl rand -base64 32`

## Backup & Recovery

### Database Backup

```bash
# Backup postgres
docker-compose exec postgres-prod pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql

# Restore postgres
cat backup.sql | docker-compose exec -T postgres-prod psql -U $POSTGRES_USER $POSTGRES_DB
```

### Volume Backup

```bash
# Backup postgres volume
docker run --rm -v purplex_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restore postgres volume
docker run --rm -v purplex_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
```

## Performance Optimization

### Redis Memory Management

Redis is configured with:
- Max memory: 2GB (production)
- Eviction policy: allkeys-lru (Least Recently Used)
- Password authentication required in production

Configuration in docker-compose.yml:
```yaml
command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru --requirepass ${REDIS_PASSWORD}
```

### Worker Scaling

Adjust concurrency based on load:
```bash
# Development (default: 2 workers)
CELERY_WORKERS=4 COMPOSE_PROFILES=development docker-compose up -d celery-dev

# Production (default: 100 gevent workers)
CELERY_WORKERS=100 COMPOSE_PROFILES=production docker-compose up -d celery
```

Note: Production uses gevent pool for high concurrency, development uses prefork pool.

### Gunicorn Workers

```bash
# Formula: (2 × CPU cores) + 1
# Default is 5 workers (from .env.production.template)
GUNICORN_WORKERS=9 COMPOSE_PROFILES=production docker-compose up -d web
```

Note: Production uses gunicorn with configuration from `/app/config/gunicorn/gunicorn.py`.

## Profiles Reference

### Development Profile

Services: postgres, redis, web-dev, celery-dev, celery-beat-dev, frontend-dev

```bash
COMPOSE_PROFILES=development docker-compose up -d
```

### Production Profile

Services: postgres-prod, redis-prod, web, celery, celery-beat, nginx, certbot, dind

```bash
COMPOSE_PROFILES=production docker-compose up -d
```

### Mixed Profiles

Run both (not recommended):
```bash
COMPOSE_PROFILES=development,production docker-compose up -d
```

## Useful Commands

```bash
# Rebuild specific service
docker-compose build <service>

# Scale workers
docker-compose up -d --scale celery=3

# Execute command in running container
docker-compose exec web python manage.py shell

# Attach to running container
docker-compose exec web /bin/bash

# Copy files from container
docker cp purplex_postgres:/var/lib/postgresql/data ./backup

# View container resource constraints
docker inspect <container> | grep -A 20 "HostConfig"
```

## Related Documentation

- [Development Guide](../development/DEVELOPMENT.md)
- [Architecture Overview](../architecture/ARCHITECTURE.md)
- [Deployment Checklist](./DEPLOYMENT_CHECKLIST.md)
