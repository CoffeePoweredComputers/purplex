#!/bin/bash
# PostgreSQL Zombie Transaction Monitoring Script
# Detects idle transactions, blocking queries, and held locks

CONTAINER="purplex_postgres"
USER="purplex"
DB="purplex"

echo "=================================================="
echo "PostgreSQL Zombie Transaction Monitor"
echo "=================================================="
echo ""

echo "1. IDLE IN TRANSACTION (Zombies)"
echo "--------------------------------------------------"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT
    pid,
    usename,
    application_name,
    state,
    NOW() - state_change AS idle_duration,
    NOW() - query_start AS query_age,
    LEFT(query, 100) AS query_preview
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND (NOW() - state_change) > interval '10 seconds'
ORDER BY state_change;
"
echo ""

echo "2. BLOCKING QUERIES (Causing Waits)"
echo "--------------------------------------------------"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.state AS blocked_state,
    blocking_activity.state AS blocking_state,
    NOW() - blocking_activity.state_change AS blocking_duration,
    LEFT(blocked_activity.query, 80) AS blocked_query,
    LEFT(blocking_activity.query, 80) AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
"
echo ""

echo "3. LOCKS ON SPECIFIC TABLE (UserProblemSetProgress)"
echo "--------------------------------------------------"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT
    l.pid,
    l.locktype,
    l.mode,
    l.granted,
    a.state,
    NOW() - a.state_change AS lock_duration,
    LEFT(a.query, 100) AS query_preview
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
JOIN pg_class c ON l.relation = c.oid
WHERE c.relname = 'problems_app_userproblemsetprogress'
ORDER BY l.granted, a.state_change;
"
echo ""

echo "4. LONG RUNNING TRANSACTIONS (>30s)"
echo "--------------------------------------------------"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT
    pid,
    usename,
    application_name,
    state,
    NOW() - xact_start AS transaction_age,
    NOW() - query_start AS query_age,
    LEFT(query, 100) AS query_preview
FROM pg_stat_activity
WHERE (NOW() - xact_start) > interval '30 seconds'
  AND state != 'idle'
ORDER BY xact_start;
"
echo ""

echo "5. SUMMARY STATS"
echo "--------------------------------------------------"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT
    state,
    COUNT(*) as count,
    MAX(NOW() - state_change) as max_duration
FROM pg_stat_activity
WHERE pid != pg_backend_pid()
GROUP BY state
ORDER BY count DESC;
"
echo ""

echo "6. KILL ZOMBIE COMMAND (if needed)"
echo "--------------------------------------------------"
echo "To kill a specific zombie transaction:"
echo "  docker exec $CONTAINER psql -U $USER -d $DB -c \"SELECT pg_terminate_backend(<pid>);\""
echo ""
echo "To kill ALL idle in transaction (use with caution!):"
echo "  docker exec $CONTAINER psql -U $USER -d $DB -c \\"
echo "    \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction';\""
echo ""
