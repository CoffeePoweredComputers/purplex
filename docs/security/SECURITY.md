# Security Documentation

## Recent Security Enhancements (2024)

### 1. SSE Token Security (CRITICAL - Fixed)
**Previous Issue**: Authentication tokens were exposed in URL query parameters for SSE connections
**Solution Implemented**:
- Created separate SSE session token system with 5-minute TTL
- Added `/api/auth/sse-token/` endpoint for secure token exchange
- Frontend now exchanges Firebase tokens for short-lived SSE tokens
- Tokens stored in Django cache (Redis backend) with automatic expiration
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
Firebase Token (Long-lived, ~1 hour)
    ↓
[Exchange via POST /api/auth/sse-token/]
    ↓
SSE Session Token (5-minute TTL, sliding expiration)
    ↓
[Used for EventSource connections]
```

### SSE Token Extraction
SSE tokens are extracted in this priority order:
1. `X-SSE-Token` header (preferred)
2. `sse_token` query parameter (fallback for EventSource API compatibility)

This is more secure than exposing Firebase tokens because:
- SSE tokens are short-lived (5 minutes vs 1 hour)
- SSE tokens have sliding expiration (refreshed on use)
- SSE tokens can be revoked via DELETE to `/api/auth/sse-token/`

### Rate Limiting Thresholds
- **Regular Authentication**: 10/minute, 100/hour (blocked after 10+ failures)
- **Service Accounts**: 5/minute
- **SSE Token Creation**: 20/minute
- **Failed Attempts**: Exponential backoff based on failure count:
  - 1-3 failures: 60 second lockout
  - 4-6 failures: 5 minute lockout
  - 7-10 failures: 15 minute lockout
  - 11+ failures: 1 hour lockout

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
- Resource limits: Configurable RAM (default 256MB), CPU (default 50%), timeout (default 5s)
- Read-only filesystem with minimal tmpfs (10MB /tmp, 1MB /sandbox)
- Non-root user execution (UID 1000)
- All Linux capabilities dropped (`cap_drop: ["ALL"]`)
- Code validation blocks dangerous imports and functions

### Container Security Configuration
```python
{
    'network_mode': 'none',              # No network access
    'mem_limit': '256m',                  # Memory limit (configurable)
    'memswap_limit': '256m',              # Prevent swap usage
    'cpu_quota': 50000,                   # 50% CPU max (configurable)
    'cpu_period': 100000,                 # 100ms period
    'pids_limit': 50,                     # Process limit
    'read_only': True,                    # Read-only root filesystem
    'privileged': False,                  # Explicit non-privileged mode
    'cap_drop': ['ALL'],                  # Drop all Linux capabilities
    'security_opt': ['no-new-privileges'], # No privilege escalation
    'user': '1000:1000',                  # Non-root user
    'tmpfs': {
        '/tmp': 'size=10M,mode=1777',     # Limited temp space
        '/sandbox': 'size=1M,mode=755'    # Tiny working directory
    },
    'ulimits': [{'name': 'nofile', 'soft': 64, 'hard': 64}]  # File descriptor limit
}
```

### Code Validation Rules
**Blocked Imports** (defined in `purplex/settings/security.py`):
- System: `os`, `sys`, `subprocess`
- Network: `socket`, `requests`, `urllib`, `http`, `ftplib`, `telnetlib`, `ssl`
- Serialization: `pickle`, `shelve`, `marshal`
- Dynamic: `importlib`, `__import__`, `eval`, `exec`, `compile`
- I/O: `open`, `file`, `input`, `raw_input`

**Blocked Builtins**:
- Execution: `eval()`, `exec()`, `compile()`, `__import__()`
- File Access: `open()`, `file()`, `input()`, `raw_input()`
- Introspection: `globals()`, `locals()`, `vars()`, `dir()`
- Attribute Access: `getattr()`, `setattr()`, `delattr()`, `hasattr()`

**Additional Suspicious Pattern Detection**:
- `__dict__`, `__class__`, `__bases__`, `__subclasses__`
- `__code__`, `__builtins__`, `__globals__`
- `base64` (encoding bypass attempts)

### Execution Rate Limiting
Configurable via environment variables (defaults shown):
- Per minute: 20 executions (`RATE_LIMIT_SUBMIT_PER_MINUTE`)
- Per hour: 300 executions (`CODE_EXEC_RATE_LIMIT_PER_HOUR`)
- Per day: 500 executions (`CODE_EXEC_RATE_LIMIT_PER_DAY`)
- Cached in Django cache (Redis backend) with automatic expiration

### Container Pooling
For performance, containers are pooled and reused:
- Pool size: 3 (development) / 15 (production)
- Containers are cleaned between executions (tmpfs cleared)
- Health monitoring runs every 60 seconds
- Containers rotated after 1 hour max age
- Containers removed after 3 restart failures

### Security Monitoring
- All executions logged with SHA256 hash of code
- Suspicious pattern detection (system, popen, socket, eval, exec keywords)
- Full audit trail with user ID and timestamps

## Reporting Security Issues
If you discover a security vulnerability, please email security@purplex.com with:
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

Do not create public GitHub issues for security vulnerabilities.
