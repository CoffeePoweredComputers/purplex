#!/bin/bash
# Container Pool Monitoring Script
# Runs every 5 minutes via cron to track Docker container pool health
# Logs to /var/log/purplex/container_monitor.log

LOG_DIR="/var/log/purplex"
LOG_FILE="$LOG_DIR/container_monitor.log"
ALERT_FILE="$LOG_DIR/container_alerts.log"

# Create log directory if needed
mkdir -p "$LOG_DIR"

# Get timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Count containers
TOTAL=$(docker ps --filter "ancestor=purplex/python-sandbox:latest" --format "{{.ID}}" | wc -l)
POOL=$(docker ps --filter "ancestor=purplex/python-sandbox:latest" --filter "label=purplex-pool=true" --format "{{.ID}}" | wc -l)
ORPHANS=$((TOTAL - POOL))

# Memory stats (in GB)
MEM_TOTAL=$(free -g | awk 'NR==2{print $2}')
MEM_FREE=$(free -g | awk 'NR==2{print $4}')
MEM_USED=$(free -g | awk 'NR==2{print $3}')

# Disk stats
DISK_FREE=$(df -h / | awk 'NR==2{print $4}')

# Oldest container age
OLDEST=$(docker ps --filter "ancestor=purplex/python-sandbox:latest" --format "{{.RunningFor}}" | head -1)
if [ -z "$OLDEST" ]; then
    OLDEST="none"
fi

# Log metrics
echo "$TIMESTAMP | containers=$TOTAL pool=$POOL orphans=$ORPHANS | mem_free=${MEM_FREE}GB mem_used=${MEM_USED}GB | disk_free=$DISK_FREE | oldest=$OLDEST" >> "$LOG_FILE"

# Check for alerts
if [ $TOTAL -gt 30 ]; then
    echo "$TIMESTAMP | CRITICAL: $TOTAL containers running (>30 limit)" >> "$ALERT_FILE"
elif [ $TOTAL -gt 20 ]; then
    echo "$TIMESTAMP | WARNING: $TOTAL containers running (>20 expected)" >> "$ALERT_FILE"
fi

if [ $ORPHANS -gt 0 ]; then
    echo "$TIMESTAMP | WARNING: $ORPHANS orphaned containers detected" >> "$ALERT_FILE"
    # List orphaned container IDs for debugging
    docker ps --filter "ancestor=purplex/python-sandbox:latest" --format "{{.ID}} {{.CreatedAt}}" | while read id created; do
        # Check if it has the pool label
        if ! docker inspect $id --format '{{.Config.Labels}}' | grep -q "purplex-pool:true"; then
            echo "$TIMESTAMP |   Orphan: $id created $created" >> "$ALERT_FILE"
        fi
    done
fi

if [ $MEM_FREE -lt 2 ]; then
    echo "$TIMESTAMP | CRITICAL: Low memory ($MEM_FREE GB free)" >> "$ALERT_FILE"
fi

# Rotate logs if >100MB
if [ -f "$LOG_FILE" ]; then
    SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || stat -f%z "$LOG_FILE" 2>/dev/null)
    if [ ! -z "$SIZE" ] && [ $SIZE -gt 104857600 ]; then
        mv "$LOG_FILE" "$LOG_FILE.$(date +%Y%m%d)"
        gzip "$LOG_FILE.$(date +%Y%m%d)" &
    fi
fi
