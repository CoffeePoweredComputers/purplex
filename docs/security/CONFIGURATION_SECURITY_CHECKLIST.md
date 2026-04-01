# Configuration Security Checklist

## Pre-Deployment Security Audit

This checklist ensures your Purplex configuration is secure before production deployment. Each item is marked as **[CRITICAL]**, **[HIGH]**, **[MEDIUM]**, or **[LOW]** priority.

**Reference Documentation:**
- [Django Security Documentation](https://docs.djangoproject.com/en/5.0/topics/security/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)

---

## Secret Management

### **[CRITICAL]** Django Secret Key
- [ ] Generated new SECRET_KEY for production (not using development key)
- [ ] SECRET_KEY is at least 50 characters long
- [ ] SECRET_KEY contains random characters (not a simple phrase)
- [ ] SECRET_KEY is unique per environment (different for staging/production)
- [ ] SECRET_KEY is stored securely (environment variable or secrets manager)
- [ ] SECRET_KEY does not contain "test", "dev", or "development"
- [ ] Old SECRET_KEY rotated if compromised
- [ ] SECRET_KEY_FALLBACKS configured for seamless key rotation (Django 4.1+)

**Generate new key:**
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### **[CRITICAL]** API Keys
- [ ] `OPENAI_API_KEY` configured for your OpenAI-compatible provider
- [ ] AI API key has appropriate usage limits/quotas set in provider dashboard
- [ ] AI API keys are not shared across environments
- [ ] Firebase credentials file exists and is valid JSON
- [ ] Firebase credentials file has restricted permissions (chmod 600)
- [ ] No API keys in source code or version control
- [ ] All API keys are rotated regularly (every 90 days recommended)
- [ ] API keys stored in AWS Secrets Manager or equivalent (production)

### **[HIGH]** Database Credentials
- [ ] Database password is strong (16+ characters, mixed case, numbers, symbols)
- [ ] Database user has minimum required privileges (no SUPERUSER)
- [ ] Database connection uses SSL (sslmode=require or sslmode=verify-full)
- [ ] Different database credentials for each environment
- [ ] Database password rotated regularly (quarterly recommended)
- [ ] Database not exposed to public internet (firewall rules configured)
- [ ] Database backups configured and tested

---

## Security Configuration

### **[CRITICAL]** HTTPS/SSL
- [ ] `SECURE_SSL_REDIRECT=true` in production (or handled by reverse proxy)
- [ ] Valid SSL certificates installed (TLS 1.2+ only)
- [ ] SSL certificates not expired (check expiry date)
- [ ] `SESSION_COOKIE_SECURE=true`
- [ ] `CSRF_COOKIE_SECURE=true`
- [ ] HSTS enabled: `SECURE_HSTS_SECONDS=31536000` (1 year)
- [ ] HSTS subdomains: `SECURE_HSTS_INCLUDE_SUBDOMAINS=true`
- [ ] HSTS preload: `SECURE_HSTS_PRELOAD=true` (only if on HSTS preload list)
- [ ] `SECURE_PROXY_SSL_HEADER` configured if behind reverse proxy

**Verify SSL configuration:**
```bash
# Check certificate expiry
openssl x509 -enddate -noout -in /path/to/cert.pem

# Test HTTPS redirect
curl -I http://yoursite.com

# Check SSL grade (online)
# https://www.ssllabs.com/ssltest/
```

### **[CRITICAL]** Debug Mode
- [ ] `DJANGO_DEBUG=False` in production
- [ ] `PURPLEX_ENV=production` set correctly
- [ ] `ENABLE_DEBUG_TOOLBAR=false` in production
- [ ] No debug endpoints exposed
- [ ] Error pages don't leak sensitive information (no stack traces)
- [ ] `USE_MOCK_FIREBASE=false` in production
- [ ] `USE_MOCK_OPENAI=false` in production

### **[HIGH]** CORS Configuration
- [ ] `CORS_ALLOWED_ORIGINS` explicitly set (no wildcards)
- [ ] Only necessary origins whitelisted
- [ ] Different CORS settings for each environment
- [ ] No `Access-Control-Allow-Origin: *` headers
- [ ] `CORS_ALLOW_CREDENTIALS=true` only with explicit origins

### **[HIGH]** CSRF Configuration
- [ ] `CSRF_TRUSTED_ORIGINS` explicitly set for production domain(s)
- [ ] CSRF middleware enabled in MIDDLEWARE
- [ ] `CSRF_COOKIE_HTTPONLY=false` (required for JavaScript access)
- [ ] `CSRF_COOKIE_SAMESITE='Lax'` or `'Strict'`

### **[HIGH]** Allowed Hosts
- [ ] `DJANGO_ALLOWED_HOSTS` explicitly set
- [ ] No wildcards (*) in production
- [ ] Only legitimate domains listed
- [ ] Includes www and non-www variants if needed
- [ ] Web server configured to reject unknown hosts (nginx default_server)

### **[HIGH]** Security Headers
- [ ] `X_FRAME_OPTIONS='DENY'` (clickjacking protection)
- [ ] `SECURE_CONTENT_TYPE_NOSNIFF=true` (MIME type sniffing prevention)
- [ ] `SECURE_BROWSER_XSS_FILTER=true` (XSS filter)
- [ ] `SECURE_REFERRER_POLICY='strict-origin-when-cross-origin'`
- [ ] SecurityMiddleware enabled in MIDDLEWARE
- [ ] XFrameOptionsMiddleware enabled in MIDDLEWARE

### **[MEDIUM]** Content Security Policy (CSP)
- [ ] CSP middleware enabled (`csp.middleware.CSPMiddleware`)
- [ ] `CSP_DEFAULT_SRC` set to `'self'`
- [ ] `CSP_SCRIPT_SRC` restricts script sources appropriately
- [ ] `CSP_STYLE_SRC` restricts style sources appropriately
- [ ] `CSP_IMG_SRC` configured for required image sources
- [ ] `CSP_CONNECT_SRC` configured for API endpoints (Firebase, Google)
- [ ] `CSP_FRAME_SRC` restricted (only necessary iframes)
- [ ] `CSP_OBJECT_SRC` set to `'none'` (blocks plugins)
- [ ] CSP report-uri configured for violation monitoring (optional)

### **[MEDIUM]** Session Security
- [ ] `SESSION_COOKIE_HTTPONLY=true` (prevents JavaScript access)
- [ ] `SESSION_COOKIE_SAMESITE='Lax'` or `'Strict'`
- [ ] `SESSION_COOKIE_AGE` set appropriately (86400 = 24 hours recommended)
- [ ] `SESSION_EXPIRE_AT_BROWSER_CLOSE` configured based on requirements
- [ ] Session backend using Redis cache in production

---

## Rate Limiting

### **[HIGH]** Global Rate Limits
- [ ] `RATE_LIMIT_ENABLED=true` in production
- [ ] Appropriate limits for authentication endpoints
- [ ] Appropriate limits for code execution endpoints
- [ ] Appropriate limits for AI generation endpoints
- [ ] Rate limits tested under load
- [ ] Rate limit bypass headers secured (X-Forwarded-For spoofing prevention)

### **[MEDIUM]** Endpoint-Specific Limits
- [ ] Login attempts limited (5 per minute / 60 per hour recommended)
- [ ] Registration limited (5 per day recommended)
- [ ] Code submission limited (20 per minute / 300 per hour recommended)
- [ ] AI generation limited (10 per minute / 50 per hour recommended)
- [ ] API calls limited based on user tier
- [ ] 429 response page configured (`RATELIMIT_VIEW`)

---

## Access Control

### **[CRITICAL]** File Permissions
- [ ] Configuration files readable only by app user (chmod 600)
- [ ] Log directories writable only by app user (chmod 755)
- [ ] Firebase credentials file has restricted permissions (chmod 600)
- [ ] No world-readable sensitive files
- [ ] Static files have appropriate permissions (chmod 644)
- [ ] Media upload directory permissions set (chmod 755 for dir, 644 for files)

**Check permissions:**
```bash
# Check .env file permissions
ls -la .env*

# Fix permissions
chmod 600 .env.production
chmod 600 firebase-credentials.json

# Check for world-readable secrets
find /app -name "*.env*" -o -name "*credentials*" -o -name "*secret*" | xargs ls -la
```

### **[HIGH]** Service Isolation
- [ ] Redis has authentication enabled (REDIS_PASSWORD set)
- [ ] Redis not exposed to public internet
- [ ] PostgreSQL not exposed to public internet
- [ ] PostgreSQL connection restricted to application servers only
- [ ] Admin interfaces behind VPN or IP whitelist
- [ ] Django admin URL changed from default `/admin/`
- [ ] Monitoring endpoints protected (Flower, health checks)
- [ ] Celery Flower requires authentication

---

## Monitoring and Logging

### **[HIGH]** Log Configuration
- [ ] Log files stored outside web root
- [ ] Log rotation configured (RotatingFileHandler with maxBytes and backupCount)
- [ ] Sensitive data not logged (passwords, tokens, API keys, PII)
- [ ] Error notifications configured (ADMINS and MANAGERS settings)
- [ ] Log aggregation service configured (if applicable)
- [ ] JSON log format for production (structured logging)
- [ ] Log levels appropriate (INFO for production, not DEBUG)

### **[MEDIUM]** Monitoring
- [ ] Sentry or error tracking configured (SENTRY_DSN)
- [ ] Sentry `send_default_pii=False` to protect user privacy
- [ ] Uptime monitoring in place
- [ ] SSL certificate expiry monitoring
- [ ] Database connection monitoring
- [ ] Redis connection monitoring
- [ ] Disk space monitoring for logs
- [ ] Celery task queue monitoring (Flower or equivalent)

---

## Docker Security

### **[HIGH]** Container Configuration
- [ ] Containers run as non-root user (DOCKER_USER=1000:1000)
- [ ] Read-only root filesystem where possible (DOCKER_READ_ONLY=true)
- [ ] Network isolation configured (DOCKER_NETWORK=none for sandbox)
- [ ] Resource limits set (CPU, memory via CODE_EXEC_MAX_MEMORY)
- [ ] No privileged containers in production
- [ ] Seccomp profiles applied for additional syscall filtering
- [ ] AppArmor or SELinux profiles configured

### **[HIGH]** Code Execution Sandbox
- [ ] `CODE_EXEC_MAX_TIME` set (5 seconds recommended for production)
- [ ] `CODE_EXEC_MAX_MEMORY` set (256m recommended for production)
- [ ] `CODE_EXEC_MAX_CPU` percentage limited (50% recommended)
- [ ] Forbidden imports list reviewed and up-to-date
- [ ] Forbidden builtins list reviewed and up-to-date
- [ ] Network disabled in sandbox containers
- [ ] File write disabled in sandbox containers
- [ ] Container pool size appropriate for load (DOCKER_POOL_SIZE)

### **[MEDIUM]** Image Security
- [ ] Using specific image tags (not :latest)
- [ ] Base images regularly updated
- [ ] Security scanning on images (Trivy, Snyk, or equivalent)
- [ ] Minimal base images used (alpine, distroless)
- [ ] No secrets baked into images
- [ ] Multi-stage builds used to reduce attack surface

---

## Validation Commands

Run these commands to validate your configuration:

### 1. Configuration Validation
```python
# In Django shell
from purplex.config.environment import config
config.validate_configuration()
config.validate_security()
print(config.get_config_summary())
```

### 2. Django Security Check
```bash
# Run Django's built-in deployment checklist
python manage.py check --deploy

# Expected: No warnings or errors
# Common issues: DEBUG=True, missing ALLOWED_HOSTS, insecure cookies
```

### 3. Environment Variable Audit
```bash
# Check for required variables
env | grep -E "DJANGO_SECRET_KEY|DATABASE_URL|REDIS_URL|PURPLEX_ENV"

# Check for insecure values (should return empty)
env | grep -iE "test|dev|demo|password|secret" | grep -v "_URL" | grep -v "_PATH"

# Verify production environment
echo $PURPLEX_ENV  # Should output: production
```

### 4. SSL/TLS Test
```bash
# Test SSL configuration
nmap --script ssl-cert,ssl-enum-ciphers -p 443 yoursite.com

# Check certificate chain
openssl s_client -connect yoursite.com:443 -servername yoursite.com

# Online tools (recommended)
# https://www.ssllabs.com/ssltest/
# https://observatory.mozilla.org/
```

### 5. Port Scan
```bash
# Check exposed ports (from external network)
nmap -p 1-65535 yourserver.com

# Expected open ports: 80 (redirect), 443 (HTTPS)
# Should NOT be open: 5432 (PostgreSQL), 6379 (Redis), 5555 (Flower)
```

### 6. Security Headers Check
```bash
# Check security headers
curl -I https://yoursite.com | grep -iE "strict-transport|x-frame|x-content-type|content-security|referrer-policy"

# Online tool: https://securityheaders.com/
```

---

## Red Flags - DO NOT DEPLOY IF:

1. **Using default/development credentials in production**
2. **DEBUG=True in production**
3. **PURPLEX_ENV not set to "production"**
4. **No HTTPS/SSL configured (unless explicitly using HTTP-only deployment)**
5. **Database exposed to internet without firewall**
6. **Default SECRET_KEY from examples/documentation**
7. **SECRET_KEY contains "test", "dev", or "development"**
8. **Wildcard (*) in ALLOWED_HOSTS**
9. **No rate limiting enabled**
10. **Running containers as root**
11. **Sensitive data in logs (passwords, tokens, PII)**
12. **Unencrypted database connections**
13. **USE_MOCK_FIREBASE=true in production**
14. **USE_MOCK_OPENAI=true in production**
15. **Redis accessible without authentication**
16. **CORS_ALLOWED_ORIGINS contains wildcards**

---

## Post-Deployment Checklist

After deployment, verify:

- [ ] Application starts without configuration errors
- [ ] `python manage.py check --deploy` passes with no warnings
- [ ] HTTPS redirect working (HTTP 301/302 to HTTPS)
- [ ] Login rate limiting active (test with repeated failed logins)
- [ ] Error tracking receiving events (trigger test error)
- [ ] Logs being written and rotated
- [ ] Database connections using SSL (check connection string)
- [ ] No sensitive data in browser console (check Network tab)
- [ ] Security headers present in responses
- [ ] CORS properly restricting cross-origin requests
- [ ] CSRF protection working (test form submissions)
- [ ] Session cookies have Secure and HttpOnly flags
- [ ] Content Security Policy not blocking legitimate resources

**Test security headers:**
```bash
curl -I https://yoursite.com | grep -iE "strict-transport-security|x-frame-options|x-content-type|content-security-policy|referrer-policy"

# Expected headers:
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# Content-Security-Policy: default-src 'self'; ...
# Referrer-Policy: strict-origin-when-cross-origin
```

**Test cookie security:**
```bash
curl -c - https://yoursite.com/api/auth/login/ 2>/dev/null | grep -i "secure\|httponly"
```

---

## Regular Maintenance

### Weekly
- [ ] Review error logs for security-related issues
- [ ] Check rate limiting logs for attack patterns
- [ ] Verify backup completion status

### Monthly
- [ ] Review access logs for suspicious activity
- [ ] Check for configuration drift
- [ ] Verify backups are working and can be restored
- [ ] Review rate limit effectiveness
- [ ] Update Docker base images
- [ ] Run `pip list --outdated` and `npm outdated` for security updates

### Quarterly
- [ ] Rotate API keys and passwords (AI providers, database)
- [ ] Update SSL certificates (if not auto-renewed)
- [ ] Review and update security policies
- [ ] Conduct internal security audit
- [ ] Review and update firewall rules
- [ ] Test disaster recovery procedures
- [ ] Run `python manage.py check --deploy`

### Annually
- [ ] Full security penetration test (external)
- [ ] Disaster recovery drill (full restore test)
- [ ] Review and update this checklist
- [ ] Security training for team members
- [ ] Review third-party dependencies for vulnerabilities
- [ ] Rotate Django SECRET_KEY (use SECRET_KEY_FALLBACKS for seamless rotation)

---

## Incident Response

If a security incident occurs:

### 1. Immediate Actions (First Hour)
- [ ] Assess severity and scope of the incident
- [ ] Rotate all potentially compromised secrets and keys
- [ ] Revoke suspicious user sessions
- [ ] Enable additional logging/monitoring
- [ ] Consider taking affected services offline if needed
- [ ] Notify relevant stakeholders

### 2. Containment (First 24 Hours)
- [ ] Isolate affected systems
- [ ] Block malicious IPs/users
- [ ] Preserve evidence (logs, database snapshots)
- [ ] Review access logs for unauthorized activity
- [ ] Check for unauthorized changes (code, config, data)

### 3. Investigation
- [ ] Identify attack vector and entry point
- [ ] Determine scope of data exposure
- [ ] Document detailed timeline
- [ ] Identify affected users/data
- [ ] Preserve forensic evidence

### 4. Remediation
- [ ] Patch vulnerabilities that were exploited
- [ ] Update configuration to prevent recurrence
- [ ] Implement additional security controls
- [ ] Force password resets if credentials exposed
- [ ] Restore from clean backups if needed

### 5. Post-Incident (Within 1 Week)
- [ ] Conduct post-mortem analysis
- [ ] Update security procedures based on lessons learned
- [ ] Notify affected users if required (data breach)
- [ ] Update this checklist with new items
- [ ] Train team on lessons learned
- [ ] File regulatory reports if required (GDPR, etc.)

---

## Security Resources

### Django Security
- [Django Security Documentation](https://docs.djangoproject.com/en/5.0/topics/security/) - Core security features
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/) - Pre-deployment verification
- [Django Security Releases](https://docs.djangoproject.com/en/5.0/releases/security/) - Security update notifications

### General Web Security
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - Common web vulnerabilities
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) - Security implementation guides
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security) - Comprehensive web security

### Infrastructure
- [12 Factor App](https://12factor.net/) - Cloud-native application best practices
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/) - Container security
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks) - System hardening guides

### Testing Tools
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/) - SSL/TLS configuration analysis
- [Security Headers](https://securityheaders.com/) - HTTP security header analysis
- [Mozilla Observatory](https://observatory.mozilla.org/) - Website security scanner

### Compliance
- [GDPR Compliance](https://gdpr.eu/) - EU data protection requirements
- [SOC 2 Overview](https://www.aicpa.org/soc2) - Service organization controls

---

## Quick Reference: Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PURPLEX_ENV` | Yes | development | Environment: development, staging, production |
| `DJANGO_SECRET_KEY` | Yes (prod) | - | Django secret key (50+ random chars) |
| `DJANGO_DEBUG` | No | False (prod) | Debug mode (must be False in prod) |
| `DJANGO_ALLOWED_HOSTS` | Yes (prod) | - | Comma-separated list of allowed hosts |
| `DATABASE_URL` | Yes | - | PostgreSQL connection URL |
| `REDIS_URL` | Yes | - | Redis connection URL |
| `REDIS_PASSWORD` | Recommended | - | Redis authentication password |
| `OPENAI_API_KEY` | Yes (prod) | - | API key for OpenAI-compatible provider |
| `OPENAI_BASE_URL` | No | - | Optional: custom base URL for non-OpenAI providers |
| `FIREBASE_CREDENTIALS_PATH` | Yes (prod) | - | Path to Firebase credentials JSON |
| `SECURE_SSL_REDIRECT` | No | True (prod) | Redirect HTTP to HTTPS |
| `SESSION_COOKIE_SECURE` | No | True (prod) | Only send cookies over HTTPS |
| `CSRF_COOKIE_SECURE` | No | True (prod) | Only send CSRF cookie over HTTPS |
| `CSRF_TRUSTED_ORIGINS` | Yes (prod) | - | Trusted origins for CSRF |
| `RATE_LIMIT_ENABLED` | No | True (prod) | Enable rate limiting |
| `SENTRY_DSN` | Recommended | - | Sentry error tracking DSN |

---

**Remember:** Security is not a one-time task but an ongoing process. Regular audits and updates are essential for maintaining a secure configuration. Run `python manage.py check --deploy` before every production deployment.
