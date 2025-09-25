# Configuration Security Checklist

## Pre-Deployment Security Audit

This checklist ensures your Purplex configuration is secure before production deployment. Each item is marked as **[CRITICAL]**, **[HIGH]**, **[MEDIUM]**, or **[LOW]** priority.

---

## 🔐 Secret Management

### **[CRITICAL]** Django Secret Key
- [ ] Generated new SECRET_KEY for production (not using development key)
- [ ] SECRET_KEY is at least 50 characters long
- [ ] SECRET_KEY contains random characters (not a simple phrase)
- [ ] SECRET_KEY is unique per environment (different for staging/production)
- [ ] SECRET_KEY is stored securely (environment variable or secrets manager)
- [ ] Old SECRET_KEY rotated if compromised

**Generate new key:**
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### **[CRITICAL]** API Keys
- [ ] OpenAI API key is valid and has appropriate limits set
- [ ] OpenAI API key is not shared across environments
- [ ] Firebase credentials file exists and is valid JSON
- [ ] Firebase credentials file has restricted permissions (600)
- [ ] No API keys in source code or version control
- [ ] All API keys are rotated regularly (every 90 days)

### **[HIGH]** Database Credentials
- [ ] Database password is strong (16+ characters, mixed case, numbers, symbols)
- [ ] Database user has minimum required privileges
- [ ] Database connection uses SSL (sslmode=require)
- [ ] Different database credentials for each environment
- [ ] Database password rotated regularly

---

## 🛡️ Security Configuration

### **[CRITICAL]** HTTPS/SSL
- [ ] `SECURE_SSL_REDIRECT=true` in production
- [ ] Valid SSL certificates installed
- [ ] SSL certificates not expired (check expiry date)
- [ ] `SESSION_COOKIE_SECURE=true`
- [ ] `CSRF_COOKIE_SECURE=true`
- [ ] HSTS enabled with appropriate max-age

**Verify SSL configuration:**
```bash
# Check certificate expiry
openssl x509 -enddate -noout -in /path/to/cert.pem

# Test HTTPS redirect
curl -I http://yoursite.com
```

### **[CRITICAL]** Debug Mode
- [ ] `DJANGO_DEBUG=False` in production
- [ ] `DEBUG_TOOLBAR_ENABLED=false` in production
- [ ] No debug endpoints exposed
- [ ] Error pages don't leak sensitive information

### **[HIGH]** CORS Configuration
- [ ] `CORS_ALLOWED_ORIGINS` explicitly set (no wildcards)
- [ ] Only necessary origins whitelisted
- [ ] Different CORS settings for each environment
- [ ] No `Access-Control-Allow-Origin: *` headers

### **[HIGH]** Allowed Hosts
- [ ] `DJANGO_ALLOWED_HOSTS` explicitly set
- [ ] No wildcards (*) in production
- [ ] Only legitimate domains listed
- [ ] Includes www and non-www variants if needed

---

## 🚦 Rate Limiting

### **[HIGH]** Global Rate Limits
- [ ] `RATE_LIMIT_ENABLED=true` in production
- [ ] Appropriate limits for authentication endpoints
- [ ] Appropriate limits for code execution endpoints
- [ ] Appropriate limits for AI generation endpoints
- [ ] Rate limits tested under load

### **[MEDIUM]** Endpoint-Specific Limits
- [ ] Login attempts limited (5 per minute recommended)
- [ ] Registration limited (5 per day recommended)
- [ ] Code submission limited (10 per minute recommended)
- [ ] API calls limited based on user tier

---

## 🔒 Access Control

### **[CRITICAL]** File Permissions
- [ ] Configuration files readable only by app user (chmod 600)
- [ ] Log directories writable only by app user
- [ ] Firebase credentials file has restricted permissions
- [ ] No world-readable sensitive files

**Check permissions:**
```bash
# Check .env file permissions
ls -la .env*

# Fix permissions
chmod 600 .env.production
chmod 600 firebase-credentials.json
```

### **[HIGH]** Service Isolation
- [ ] Redis has authentication enabled (requirepass)
- [ ] PostgreSQL not exposed to public internet
- [ ] Admin interfaces behind VPN or IP whitelist
- [ ] Monitoring endpoints protected

---

## 📊 Monitoring & Logging

### **[HIGH]** Log Configuration
- [ ] Log files stored outside web root
- [ ] Log rotation configured
- [ ] Sensitive data not logged (passwords, tokens)
- [ ] Error notifications configured
- [ ] Log aggregation service configured (if applicable)

### **[MEDIUM]** Monitoring
- [ ] Sentry or error tracking configured
- [ ] Uptime monitoring in place
- [ ] SSL certificate expiry monitoring
- [ ] Database connection monitoring
- [ ] Disk space monitoring for logs

---

## 🐳 Docker Security

### **[HIGH]** Container Configuration
- [ ] Containers run as non-root user
- [ ] Read-only root filesystem where possible
- [ ] Network isolation configured
- [ ] Resource limits set (CPU, memory)
- [ ] No privileged containers in production

### **[MEDIUM]** Image Security
- [ ] Using specific image tags (not :latest)
- [ ] Base images regularly updated
- [ ] Security scanning on images
- [ ] Minimal base images used (alpine, distroless)

---

## ✅ Validation Commands

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
python manage.py check --deploy
```

### 3. Environment Variable Audit
```bash
# Check for required variables
env | grep -E "DJANGO_SECRET_KEY|DATABASE_URL|REDIS_URL"

# Check for insecure values
env | grep -iE "test|dev|demo|password|secret" | grep -v "_URL"
```

### 4. SSL/TLS Test
```bash
# Test SSL configuration
nmap --script ssl-cert,ssl-enum-ciphers -p 443 yoursite.com

# Or use online tool
# https://www.ssllabs.com/ssltest/
```

### 5. Port Scan
```bash
# Check exposed ports
nmap -p 1-65535 yourserver.com
```

---

## 🚨 Red Flags - DO NOT DEPLOY IF:

1. **Using default/development credentials in production**
2. **DEBUG=True in production**
3. **No HTTPS/SSL configured**
4. **Database exposed to internet without firewall**
5. **Default SECRET_KEY from examples/documentation**
6. **Wildcard (*) in ALLOWED_HOSTS**
7. **No rate limiting enabled**
8. **Running containers as root**
9. **Sensitive data in logs**
10. **Unencrypted database connections**

---

## 📋 Post-Deployment Checklist

After deployment, verify:

- [ ] Application starts without configuration errors
- [ ] HTTPS redirect working
- [ ] Login rate limiting active
- [ ] Error tracking receiving events
- [ ] Logs being written and rotated
- [ ] Database connections using SSL
- [ ] No sensitive data in browser console
- [ ] Security headers present in responses

**Test security headers:**
```bash
curl -I https://yoursite.com | grep -i "strict-transport-security\|x-frame-options\|x-content-type"
```

---

## 🔄 Regular Maintenance

### Monthly
- [ ] Review access logs for suspicious activity
- [ ] Check for configuration drift
- [ ] Verify backups are working
- [ ] Review rate limit effectiveness

### Quarterly
- [ ] Rotate API keys and passwords
- [ ] Update SSL certificates (if needed)
- [ ] Review and update security policies
- [ ] Conduct security audit

### Annually
- [ ] Full security penetration test
- [ ] Disaster recovery drill
- [ ] Review and update this checklist

---

## 📞 Incident Response

If a security incident occurs:

1. **Immediate Actions:**
   - [ ] Rotate all secrets and keys
   - [ ] Review access logs
   - [ ] Check for unauthorized changes
   - [ ] Enable additional logging

2. **Investigation:**
   - [ ] Identify attack vector
   - [ ] Determine data exposure
   - [ ] Document timeline

3. **Remediation:**
   - [ ] Patch vulnerabilities
   - [ ] Update configuration
   - [ ] Implement additional controls

4. **Post-Incident:**
   - [ ] Update security procedures
   - [ ] Train team on lessons learned
   - [ ] Update this checklist

---

## 🎓 Security Resources

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [12 Factor App](https://12factor.net/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)

---

**Remember:** Security is not a one-time task but an ongoing process. Regular audits and updates are essential for maintaining a secure configuration.