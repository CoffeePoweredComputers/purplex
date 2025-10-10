# Purplex Load Testing with k6

This directory contains comprehensive load testing scenarios for the Purplex educational coding platform.

## Overview

Load testing validates that Purplex can handle expected user loads and identifies performance bottlenecks before production deployment.

### Test Scenarios

1. **01-submission-flow.js** - Core code submission workflow (most critical)
2. **02-read-heavy-load.js** - Read-heavy API load test (GET endpoints)
3. **03-mixed-load.js** - Realistic read/write traffic patterns (70/20/10 split)
4. **04-spike-test.js** - Stress testing to find breaking points

## Quick Start

### Installation

#### Option 1: Docker (Recommended)
```bash
docker pull grafana/k6:latest
```

#### Option 2: Direct Installation (Linux)
```bash
wget https://github.com/grafana/k6/releases/download/v0.48.0/k6-v0.48.0-linux-amd64.tar.gz
tar -xzf k6-v0.48.0-linux-amd64.tar.gz
sudo mv k6-v0.48.0-linux-amd64/k6 /usr/local/bin/
k6 version
```

#### Option 3: Package Manager (Debian/Ubuntu)
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 \
  --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | \
  sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

### Prerequisites

**IMPORTANT:** Tests must run against the nginx endpoint (port 80), NOT Django directly (port 8000).

1. Ensure development environment is running:
```bash
# Start all services with start.sh
./start.sh
```

2. Verify services are accessible:
```bash
# Health check (no auth required)
curl http://localhost/api/health/

# Test endpoints should return 200 or 401 (auth required)
curl http://localhost/api/problems/
curl http://localhost/api/user/me/
```

3. Ensure database has test data:
```bash
python manage.py populate_sample_data
```

### Running Tests

#### Run Individual Test (Recommended for First Time)
```bash
# From project root - use nginx endpoint!
export BASE_URL="http://localhost"
k6 run tests/load/k6/scenarios/01-submission-flow.js
```

#### Run All Tests
```bash
# From project root
export BASE_URL="http://localhost"
./tests/load/k6/run-all-tests.sh
```

#### Run with HTML Reports
```bash
k6 run --out=html=tests/load/reports/submission-flow.html \
  tests/load/k6/scenarios/01-submission-flow.js
```

#### Run with Docker
```bash
# Single test - IMPORTANT: Use --network=host and BASE_URL=http://localhost
docker run --rm \
  --network=host \
  -e BASE_URL="http://localhost" \
  -v $(pwd)/tests/load:/scripts \
  grafana/k6 run /scripts/k6/scenarios/01-submission-flow.js

# With HTML output
docker run --rm \
  --network=host \
  -e BASE_URL="http://localhost" \
  -v $(pwd)/tests/load:/scripts \
  -v $(pwd)/tests/load/reports:/reports \
  grafana/k6 run --out=html=/reports/test.html /scripts/k6/scenarios/01-submission-flow.js
```

## Authentication System

**Purplex uses Mock Firebase authentication in development.**

### Token Format

Tests use Mock Firebase tokens with the format:
```
MOCK.<base64_payload>.development
```

The payload contains:
```json
{
  "email": "student@test.local",
  "uid": "mock-uid-student-test-local",
  "name": "student",
  "iat": 1234567890,
  "exp": 1234571490,
  "email_verified": true
}
```

### Test Users

Available test users (defined in `purplex/users_app/mock_firebase.py`):
- `student@test.local` - Regular student
- `student2@test.local` - Second student
- `admin@test.local` - Admin user
- `instructor@test.local` - Instructor user
- `dhsmith2@illinois.edu` - Super admin

### Auth Helper

All tests use `helpers/auth.js`:
```javascript
import { getAuthHeaders } from '../helpers/auth.js';

// Get headers with mock token
const headers = getAuthHeaders('student@test.local');

// Use in requests
http.get(`${BASE_URL}/api/problems/`, { headers: headers });
```

### Common Auth Issues

**401 Unauthorized**
- Check `PURPLEX_ENV=development` is set
- Verify Mock Firebase is enabled (not production Firebase)
- Ensure `.env.development` is loaded

**404 Not Found on Auth Endpoint**
- This is expected! Purplex doesn't have `/api/users/auth/verify-token/`
- Authentication uses Bearer tokens in Authorization header
- No separate auth endpoint needed

## Test Scenarios Explained

### 1. Submission Flow Test (01-submission-flow.js)

**Purpose**: Tests the most critical user journey - submitting and testing code.

**Load Pattern** (reduced for initial testing):
- Ramp to 5 users (10s), hold (30s)
- Total duration: ~50s

**Success Criteria**:
- Error rate < 1%
- P95 response time < 2s for API calls
- P99 code execution < 5s
- Submission errors < 10

**What It Tests**:
- Mock Firebase authentication
- Problem fetching: `GET /api/problems/{slug}/`
- Code submission: `POST /api/test-solution/`
- Progress tracking: `GET /api/progress/{slug}/`
- Docker container execution
- Task completion

**Endpoints Used**:
- `/api/health/` - Health check (setup)
- `/api/user/me/` - User profile (setup)
- `/api/problems/` - Problem list (setup)
- `/api/problems/{slug}/` - Problem detail
- `/api/test-solution/` - Submit code (POST)
- `/api/progress/{slug}/` - User progress

### 2. Read-Heavy Load Test (02-read-heavy-load.js)

**Purpose**: Tests authenticated GET endpoints under high request rate.

**Load Pattern**:
- Constant 20 req/s for 60s
- Total: 1200 requests

**Success Criteria**:
- Error rate < 1%
- P99 response time < 800ms
- Read success rate > 99%

**What It Tests**:
- Authenticated read operations
- Database query performance
- Redis caching effectiveness
- API response times

**Endpoints Used** (weighted distribution):
- `/api/problems/` - 30%
- `/api/user/me/` - 20%
- `/api/progress/` - 25%
- `/api/categories/` - 15%
- `/api/problem-sets/` - 10%

### 3. Mixed Load Test (03-mixed-load.js)

**Purpose**: Simulates realistic usage with read/write mix.

**Load Pattern**:
- 15 concurrent users for 2 minutes
- 70% read operations (browsing problems)
- 20% moderate operations (checking progress, hints)
- 10% write operations (code submissions)

**Success Criteria**:
- Error rate < 1%
- P95 read latency < 1s
- P95 write latency < 3s

**What It Tests**:
- Mixed workload handling
- Realistic user behavior
- Database caching effectiveness
- Code submission under load

### 4. Spike Test (04-spike-test.js)

**Purpose**: Find breaking point and validate graceful degradation.

**Load Pattern**:
- Warm up to 10 users (10s)
- Hold at 10 (30s)
- Spike to 30 users (10s)
- Hold at 30 (30s)
- Spike to 50 users (10s)
- Hold at 50 (30s)

**Success Criteria**:
- System doesn't crash
- Error rate < 10% (degraded performance acceptable)
- P95 response time < 10s

**What It Tests**:
- System breaking point
- Graceful degradation
- Error handling under stress
- Recovery mechanisms

## Performance Targets

### Response Times

| Endpoint Category | P50 | P95 | P99 |
|------------------|-----|-----|-----|
| Read Operations | < 200ms | < 500ms | < 1000ms |
| Write Operations | < 500ms | < 1500ms | < 2000ms |
| Code Execution | < 2000ms | < 3000ms | < 5000ms |

### Throughput

| Operation Type | Target RPS | Concurrent Users |
|----------------|------------|------------------|
| Read Operations | 20-50 req/s | 50-100 |
| Code Execution | 5-10 req/s | 20-50 |

### Error Rates

| Scenario | Max Error Rate |
|----------|----------------|
| Normal Load | < 1% |
| Peak Load | < 2% |
| Stress Test | < 10% |

## Interpreting Results

### Good Results ✓
- Error rate < 1%
- Response times consistent under load
- Resource usage < 70%
- No crashes or timeouts
- Graceful degradation under stress

### Warning Signs ⚠️
- Error rate 1-5%
- Response times increasing with load
- Resource usage 70-85%
- Intermittent timeouts
- Database connection pool pressure

### Critical Issues ❌
- Error rate > 5%
- Response times > 10s
- Resource usage > 90%
- Service crashes
- Data corruption

## Monitoring During Tests

### System Resources
```bash
# CPU and memory usage
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Database connections
docker exec purplex-postgres psql -U purplex_user -d purplex_dev -c \
  "SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';"

# Redis memory
docker exec purplex-redis redis-cli INFO memory | grep used_memory_human

# Container count
docker ps -q | wc -l
```

### Application Logs
```bash
# Django logs (if running with ./start.sh, logs are in terminal)
tail -f logs/django.log

# Celery logs
tail -f logs/celery.log

# Nginx logs
docker logs nginx 2>&1 | tail -f
```

## Bottleneck Identification

### High http_req_waiting
- **Issue**: Slow backend processing
- **Action**: Check database queries, optimize code

### High http_req_connecting
- **Issue**: Connection pooling problem
- **Action**: Increase Gunicorn workers

### Increasing http_req_duration
- **Issue**: Capacity limit reached
- **Action**: Scale infrastructure

### Error 429 (Rate Limit)
- **Issue**: Rate limiting triggered
- **Action**: Verify limits are appropriate for load test

### Error 503 (Unavailable)
- **Issue**: Service overload
- **Action**: Scale workers/containers

### Error 401 (Unauthorized)
- **Issue**: Authentication failure
- **Action**: Verify Mock Firebase is enabled, check token format

### Error 404 (Not Found)
- **Issue**: Endpoint doesn't exist or problem slug not in database
- **Action**: Verify test data exists, check endpoint URL

## Troubleshooting

### "Server not reachable"
```bash
# Verify nginx is running and accessible
curl http://localhost/api/health/

# Should return: {"status": "healthy"}

# If not, check nginx:
docker ps | grep nginx

# Check if Django is running:
curl http://localhost:8000/api/health/
```

### "Authentication failed"
```bash
# Test mock authentication manually:
curl -H "Authorization: Bearer MOCK.eyJlbWFpbCI6ICJzdHVkZW50QHRlc3QubG9jYWwiLCAidWlkIjogIm1vY2stdWlkLXN0dWRlbnQiLCAibmFtZSI6ICJzdHVkZW50IiwgImlhdCI6IDE3MDk1NDM2MDAsICJleHAiOiAxNzA5NTQ3MjAwLCAiZW1haWxfdmVyaWZpZWQiOiB0cnVlfQ==.development" \
  http://localhost/api/user/me/

# Should return user info, not 401
```

### "No problems found"
```bash
# Populate test data:
python manage.py populate_sample_data

# Verify problems exist:
python manage.py shell
>>> from purplex.problems_app.models import Problem
>>> Problem.objects.count()
# Should be > 0
```

### "Task never completed"
```bash
# Check Celery is running:
ps aux | grep celery

# Check Redis is running:
docker ps | grep redis

# Check Celery logs:
tail -f logs/celery.log
```

## Next Steps After Testing

1. **Analyze Results**
   - Review k6 console output for metrics
   - Check HTML reports in `tests/load/reports/` (if generated)
   - Identify bottlenecks using monitoring data
   - Compare actual vs. target capacity

2. **Optimize**
   - Address identified bottlenecks
   - Tune configuration (workers, pools, timeouts)
   - Optimize slow queries
   - Adjust Docker resource limits

3. **Document Capacity**
   - Record actual supported user counts
   - Set realistic SLOs
   - Update capacity planning docs

4. **Continuous Testing**
   - Run before major deployments
   - Weekly/monthly regression tests
   - Monitor production metrics

## API Endpoints Reference

All endpoints require authentication except `/api/health/`.

### Read Endpoints (GET)
- `/api/health/` - Health check (no auth)
- `/api/problems/` - List all problems
- `/api/problems/{slug}/` - Problem detail
- `/api/problem-sets/` - List problem sets
- `/api/problem-sets/{slug}/` - Problem set detail
- `/api/categories/` - List categories
- `/api/user/me/` - Current user profile
- `/api/progress/` - All user progress
- `/api/progress/{slug}/` - Progress for specific problem
- `/api/problems/{slug}/hints/` - Check hint availability
- `/api/submissions/history/{slug}/` - Submission history

### Write Endpoints (POST)
- `/api/test-solution/` - Submit code for testing (body: `{problem_slug, code}`)
- `/api/submit-eipl/` - Submit EiPL explanation (body: `{problem_slug, prompt}`)
- `/api/submit-solution/` - Submit final solution (body: `{problem_slug, code}`)

### Real-time Endpoints
- `/api/tasks/{task_id}/stream/` - SSE for task updates (GET, no polling needed)

## Resources

- [k6 Documentation](https://k6.io/docs/)
- [k6 Examples](https://k6.io/docs/examples/)
- [Purplex API Documentation](../../docs/API.md)

## Support

For issues or questions:
1. Check this README
2. Review k6 console output and error messages
3. Check application logs (Django, Celery, Nginx)
4. Verify authentication and test data
5. Check that BASE_URL points to nginx (port 80), not Django (port 8000)