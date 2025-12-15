# Security Documentation

## Recent Security Enhancements (2025)

### 1. SSE Token Security (CRITICAL - Fixed)
**Previous Issue**: Authentication tokens were exposed in URL query parameters for SSE connections
**Solution Implemented**:
- Created separate SSE session token system with 5-minute TTL
- Added `/api/auth/sse-token/` endpoint for secure token exchange
- Frontend now exchanges Firebase tokens for short-lived SSE tokens
- Tokens stored in Redis with automatic expiration
- No more sensitive tokens in URLs, logs, or browser history

### 2. Mock Secret Security (CRITICAL - Fixed)
**Previous Issue**: Hardcoded JWT secret in mock_firebase.py
**Solution Implemented**:
- Secret now loaded from `MOCK_JWT_SECRET` environment variable
- Automatic random generation if not provided
- Runtime check prevents mock system activation in production
- Added to `.env.development` for local configuration

### 3. Service Account Timing Attack Prevention (HIGH - Fixed)
**Previous Issue**: Direct string comparison vulnerable to timing attacks
**Solution Implemented**:
- Using `hmac.compare_digest()` for constant-time comparison
- Added 100ms delay on failed attempts
- Comprehensive audit logging for all service account attempts

### 4. Error Message Sanitization (HIGH - Fixed)
**Previous Issue**: Detailed Firebase errors exposed to clients
**Solution Implemented**:
- All authentication errors now return generic messages
- Detailed errors logged server-side for debugging
- Client receives only safe error codes without internal details

### 5. Rate Limiting & Audit Trail (MEDIUM - Fixed)
**Solution Implemented**:
- Redis-based rate limiting on all authentication endpoints
- Limits: 10 auth attempts/minute, 100/hour per IP
- Service accounts: 5 attempts/minute
- SSE tokens: 20 requests/minute per user
- Exponential backoff for repeated failures
- Comprehensive audit logging for security monitoring

## Authentication Architecture

### Service Layer Pattern
- Single `PurplexAuthentication` class for all endpoints
- `AuthenticationService` centralizes Firebase logic
- Clean separation between authentication and business logic
- No authentication code in views or models

### Token Management
```
Firebase Token (Long-lived)
    ↓
[Exchange via /api/auth/sse-token/]
    ↓
SSE Session Token (5-minute TTL)
    ↓
[Used for EventSource connections]
```

### Rate Limiting Thresholds
- **Regular Authentication**: 10/minute, 100/hour
- **Service Accounts**: 5/minute
- **SSE Token Creation**: 20/minute
- **Failed Attempts**: Exponential backoff (1min → 5min → 15min → 1hr)

## Security Headers
All SSE responses include:
- `Cache-Control: no-cache`
- `X-Accel-Buffering: no`
- CORS headers properly configured

## Environment Variables
Required security-related environment variables:
- `DJANGO_SECRET_KEY`: Must be unique per deployment
- `MOCK_JWT_SECRET`: For development mock authentication
- `SERVICE_ACCOUNT_KEY`: For service-to-service auth
- `PURPLEX_ENV`: Must be 'production' in production

## Best Practices
1. Never expose Firebase tokens in URLs
2. Use SSE session tokens for EventSource connections
3. Monitor authentication logs for suspicious patterns
4. Rotate service account keys regularly
5. Keep rate limiting rules updated based on usage patterns

## Code Execution Security

### Docker-Based Sandboxed Execution (CRITICAL - Implemented)
**Previous Issue**: Direct subprocess execution on host with no isolation
**Solution Implemented**:
- Complete Docker containerization with full isolation
- Network disabled (`network_mode: none`)
- Resource limits: 256MB RAM, 50% CPU, 5-second timeout
- Read-only filesystem with minimal tmpfs
- Non-root user execution (UID 1000)
- Code validation blocks dangerous imports and functions

### Container Security Configuration
```python
{
    'network_mode': 'none',              # No network access
    'mem_limit': '256m',                  # Memory limit
    'cpu_quota': 50000,                   # 50% CPU max
    'pids_limit': 50,                     # Process limit
    'read_only': True,                    # Read-only root
    'security_opt': ['no-new-privileges'], # No privilege escalation
    'user': '1000:1000'                   # Non-root user
}
```

### Code Validation Rules
**Blocked Imports**:
- System: `os`, `sys`, `subprocess`
- Network: `socket`, `requests`, `urllib`
- Serialization: `pickle`, `marshal`
- Dynamic: `importlib`, `__import__`

**Blocked Functions**:
- Execution: `eval()`, `exec()`, `compile()`
- File Access: `open()`, `file()`
- Introspection: `globals()`, `locals()`

### Execution Rate Limiting
- Per user: 10 executions/minute
- Per hour: 100 executions
- Cached in Redis with automatic expiration

### Security Monitoring
- All executions logged with SHA256 hash
- Suspicious pattern detection and alerting
- Full audit trail with user ID and timestamps

## Reporting Security Issues
If you discover a security vulnerability, please email security@purplex.com with:
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

Do not create public GitHub issues for security vulnerabilities.
