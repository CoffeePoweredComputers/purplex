# Purplex Deployment Checklist

## Pre-Deployment

- [ ] Review changes since last deployment (`git log --oneline -20`)
- [ ] Check for database migrations (`python manage.py showmigrations --plan | grep "\[ \]"`)
- [ ] Review migration safety (backward compatible? reversible?)
- [ ] Ensure backup retention policy is met
- [ ] Verify disk space (>20% free) (`df -h`)
- [ ] Verify memory availability (>10% free) (`free -h`)
- [ ] Check Docker disk usage (`docker system df`)
- [ ] Check for system updates that require restart
- [ ] Verify environment variables are set in `.env.production`
- [ ] Notify team in communication channel
- [ ] Set deployment time (prefer low-traffic periods)

## Backup Verification

- [ ] List available backups: `bash scripts/backup-recovery/list-backups.sh`
- [ ] Verify local backups exist (`ls -lh backups/` or `/home/ubuntu/backups/postgres/`)
- [ ] Verify S3 backups if configured (`aws s3 ls s3://purplex-db-backups/daily/ --recursive | tail -5`)
- [ ] Test database backup restoration on staging environment
- [ ] Confirm backup storage availability (local and S3)
- [ ] Document current version/commit hash (`git rev-parse HEAD`)

## Deployment Execution

- [ ] Run pre-deployment checks: `bash scripts/pre-deployment-check.sh`
- [ ] Review pre-check output for warnings (disk >80%, memory >90%)
- [ ] Start deployment: `bash scripts/deploy-rolling.sh`
- [ ] Monitor deployment logs in real-time (`tail -f logs/deployment-*.log`)
- [ ] Watch for error messages or warnings
- [ ] Verify backup tag is created and logged (format: `backup-YYYYMMDD-HHMMSS`)

**Note:** Production services use Docker Compose profiles. Use `COMPOSE_PROFILES=production` prefix for production commands.

## Post-Deployment Validation

- [ ] Check service status: `COMPOSE_PROFILES=production docker compose ps`
- [ ] Verify all services show "healthy" (web, celery, postgres-prod, redis-prod, nginx, dind)
- [ ] Test health endpoints:
  - [ ] Main health: `curl http://localhost/api/health/`
  - [ ] Readiness: `curl http://localhost/api/health/ready/`
  - [ ] Liveness: `curl http://localhost/api/health/live/`
  - [ ] Nginx health: `curl http://localhost/nginx-health`
- [ ] Test critical user flows:
  - [ ] User login
  - [ ] Problem listing
  - [ ] Code submission
  - [ ] EiPL submission
  - [ ] Hint retrieval
- [ ] Check error logs: `docker compose logs web --since 10m | grep -i error`
- [ ] Monitor Celery workers: `docker compose exec celery celery -A purplex.celery_simple inspect ping`
- [ ] Check Celery queue stats: `docker compose exec celery celery -A purplex.celery_simple inspect stats`
- [ ] Verify static files serve correctly (`curl -I http://localhost/static/...`)
- [ ] Check database connection pool
- [ ] Monitor Flower dashboard (if running): `http://localhost:5555`

## Performance Verification

- [ ] Check response times (should be <500ms for API): `curl -o /dev/null -s -w '%{time_total}\n' http://localhost/api/health/`
- [ ] Verify no memory leaks (stable memory usage): `docker stats --no-stream`
- [ ] Check CPU usage (should normalize after 5 minutes): `docker stats --no-stream`
- [ ] Monitor disk I/O: `iostat -x 1 5` (if available)
- [ ] Verify log files are being written: `ls -la logs/`
- [ ] Run container monitoring check: `bash scripts/monitor_containers.sh`

## Rollback Decision

**If ANY of these occur, initiate rollback immediately:**
- Health endpoint returns 503 or non-200
- More than 5% of requests return errors
- Database connection failures
- Celery workers not responding (`celery inspect ping` fails)
- Memory usage >95%
- Response times >5 seconds
- Docker-in-Docker (dind) service unhealthy

**Rollback command:**
```bash
# Use the backup tag from the deployment log
bash scripts/rollback.sh backup-YYYYMMDD-HHMMSS
```

**List available backups:**
```bash
bash scripts/backup-recovery/list-backups.sh
# Or manually:
ls -lt backups/db-backup-*.sql | head -5
```

## Post-Deployment Tasks

- [ ] Update deployment log with commit hash and backup tag
- [ ] Document any issues encountered
- [ ] Update runbook if new issues found
- [ ] Notify team of successful deployment
- [ ] Monitor error rates for 1 hour
- [ ] Run Docker cleanup if needed: `bash scripts/docker-cleanup.sh`
- [ ] Schedule cleanup of old backups (>30 days local, >90 days S3)
- [ ] Verify backup cron job is running: `crontab -l | grep backup`
- [ ] Update deployment documentation if process changed

## Emergency Contacts

Configure emergency contacts for your deployment:
- Primary On-Call: (configure in deployment secrets)
- Secondary On-Call: (configure in deployment secrets)
- Database Admin: (configure in deployment secrets)
- Cloud Provider Support: AWS Support Center or your provider's support page

---

## Common Issues and Solutions

### Issue: Pre-deployment checks fail

**Symptoms:**
- `pre-deployment-check.sh` exits with error
- Services show as unhealthy

**Actions:**
1. Check `docker compose ps` for service status
2. Review logs: `docker compose logs [service]`
3. Fix underlying issue before deployment
4. Re-run pre-deployment checks

### Issue: Migration failures

**Symptoms:**
- Deployment script exits during migration step
- Database errors in logs

**Actions:**
1. Rollback will automatically restore database
2. Review migration in development
3. Test on production backup locally
4. Fix migration and redeploy

### Issue: New container fails health checks

**Symptoms:**
- Deployment times out waiting for health
- Container shows "unhealthy"

**Diagnosis:**
```bash
docker compose logs web | tail -50
docker compose exec web curl http://localhost:8000/api/health/
```

**Common causes:**
- Missing environment variables
- Database migration not applied
- Port binding conflict

**Actions:**
1. Rollback automatically initiated
2. Fix issue identified
3. Test in staging
4. Redeploy

### Issue: Rollback fails

**Symptoms:**
- Rollback script exits with error
- Services won't start after rollback

**Manual rollback (production):**
```bash
# Stop everything
COMPOSE_PROFILES=production docker compose down

# Start postgres and redis only
COMPOSE_PROFILES=production docker compose up -d postgres-prod redis-prod
sleep 10

# Restore database manually (use actual environment variables)
docker compose exec -T postgres-prod psql -U ${POSTGRES_USER} -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
docker compose exec -T postgres-prod psql -U ${POSTGRES_USER} -c "CREATE DATABASE ${POSTGRES_DB};"
cat backups/db-backup-YYYYMMDD-HHMMSS.sql | docker compose exec -T postgres-prod psql -U ${POSTGRES_USER} ${POSTGRES_DB}

# Start all services
COMPOSE_PROFILES=production docker compose up -d

# Verify
curl http://localhost/api/health/
```

**Alternative: Restore from S3 backup:**
```bash
bash scripts/backup-recovery/restore-from-s3.sh <s3-backup-path>
```

---

## Deployment Best Practices

### Timing
- **Best:** Tuesday-Thursday, 10 AM - 2 PM
- **Avoid:** Friday afternoons, late evenings, exam periods

### Frequency
- Regular deployments: Once per week
- Hotfixes: As needed
- Major releases: Monthly

### Change Management
- Keep deployments small (easier to debug)
- One feature at a time when possible
- Always test in staging first
- Document breaking changes

### Communication
- Announce deployments in advance
- Provide rollback window estimates
- Update team on completion
- Document lessons learned

---

## Monitoring Checklist

### During Deployment (Real-time)
- [ ] Deployment script output (`tail -f logs/deployment-*.log`)
- [ ] Service health checks (`docker compose ps`)
- [ ] HTTP response codes
- [ ] Error logs (`docker compose logs -f web celery`)

### After Deployment (First hour)
- [ ] Response times: `curl -o /dev/null -s -w '%{time_total}\n' http://localhost/api/health/`
- [ ] Error rates: `docker compose logs web --since 1h | grep -c -i error`
- [ ] Memory usage trends: `docker stats --no-stream`
- [ ] Celery queue depth: `docker compose exec celery celery -A purplex.celery_simple inspect reserved`
- [ ] Database connection count: check via Django admin or pg_stat_activity
- [ ] Container pool health: `bash scripts/monitor_containers.sh`

### Ongoing (First 24 hours)
- [ ] User-reported issues
- [ ] Sentry error rates (if configured)
- [ ] Background job completion rates (check Flower at :5555)
- [ ] System resource trends
- [ ] Container pool alerts: `cat /var/log/purplex/container_alerts.log`
- [ ] Orphaned container cleanup if needed: `bash scripts/docker-cleanup.sh --force`

### Monitoring Scripts Reference

| Script | Purpose | Recommended Frequency |
|--------|---------|----------------------|
| `scripts/monitor_containers.sh` | Track Docker container pool health | Every 5 minutes (cron) |
| `scripts/docker-cleanup.sh` | Remove orphaned sandbox containers | Hourly (cron) |
| `scripts/backup-recovery/backup-postgres.sh` | Create database backup | Daily at 2 AM (cron) |
| `scripts/backup-recovery/list-backups.sh` | List all available backups | As needed |

### Cron Job Setup (Recommended)

```bash
# Add to crontab (crontab -e)
*/5 * * * * /path/to/scripts/monitor_containers.sh
0 * * * * /path/to/scripts/docker-cleanup.sh --force >> /var/log/purplex-cleanup.log 2>&1
0 2 * * * /path/to/scripts/backup-recovery/backup-postgres.sh
```

---

**Document Version:** 1.2
**Last Updated:** 2025-12-26
**Next Review:** After each deployment
