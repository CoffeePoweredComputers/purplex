#!/bin/bash
# Verify gevent monkey-patching is active in production containers

set -e

echo "================================================"
echo "Gevent Monkey-Patching Verification"
echo "================================================"
echo ""

echo "Checking Celery worker..."
docker exec purplex_celery_1 python -c "
import gevent.monkey
print('Celery Worker Gevent Status:')
print(f'  Socket:    {gevent.monkey.is_module_patched(\"socket\")}')
print(f'  Threading: {gevent.monkey.is_module_patched(\"threading\")}')
print(f'  Time:      {gevent.monkey.is_module_patched(\"time\")}')
print(f'  SSL:       {gevent.monkey.is_module_patched(\"ssl\")}')
print(f'  Select:    {gevent.monkey.is_module_patched(\"select\")}')
"
echo ""

echo "Checking Web worker..."
docker exec purplex_web_1 python -c "
import gevent.monkey
print('Web Worker Gevent Status:')
print(f'  Socket:    {gevent.monkey.is_module_patched(\"socket\")}')
print(f'  Threading: {gevent.monkey.is_module_patched(\"threading\")}')
print(f'  Time:      {gevent.monkey.is_module_patched(\"time\")}')
print(f'  SSL:       {gevent.monkey.is_module_patched(\"ssl\")}')
print(f'  Select:    {gevent.monkey.is_module_patched(\"select\")}')
"
echo ""

echo "Checking PostgreSQL connection counts..."
docker exec purplex_postgres psql -U purplex -c "
SELECT
    count(*) as total,
    state,
    CASE
        WHEN count(*) > 50 THEN '❌ TOO HIGH'
        WHEN count(*) > 30 THEN '⚠️  WARNING'
        ELSE '✓ OK'
    END as status
FROM pg_stat_activity
WHERE datname = 'purplex'
GROUP BY state
ORDER BY count(*) DESC;
"
echo ""

echo "Checking Redis connection counts..."
docker exec 168b731a1398_purplex_redis redis-cli INFO clients | grep connected_clients
echo ""

echo "================================================"
echo "Expected Results:"
echo "  - All gevent patches should be 'True'"
echo "  - PostgreSQL connections should be <30 total"
echo "  - Redis connections should be <50"
echo "================================================"
