#!/bin/bash
# tests/load/k6/run-all-tests.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
REPORT_DIR="tests/load/reports/$(date +%Y%m%d_%H%M%S)"

mkdir -p "$REPORT_DIR"

echo "========================================="
echo "Purplex Load Testing Suite"
echo "Target: $BASE_URL"
echo "Report Directory: $REPORT_DIR"
echo "========================================="

# Test 1: Core Submission Flow
echo ""
echo "[1/4] Running Core Submission Flow Test..."
k6 run \
  --out=html="$REPORT_DIR/01-submission-flow.html" \
  --out=json="$REPORT_DIR/01-submission-flow.json" \
  tests/load/k6/scenarios/01-submission-flow.js

echo "✓ Submission flow test complete"
sleep 30  # Cool down period

# Test 2: Authentication Load
echo ""
echo "[2/4] Running Authentication Load Test..."
k6 run \
  --out=html="$REPORT_DIR/02-authentication-load.html" \
  --out=json="$REPORT_DIR/02-authentication-load.json" \
  tests/load/k6/scenarios/02-authentication-load.js

echo "✓ Authentication test complete"
sleep 30

# Test 3: Mixed Load
echo ""
echo "[3/4] Running Mixed Read/Write Load Test..."
k6 run \
  --out=html="$REPORT_DIR/03-mixed-load.html" \
  --out=json="$REPORT_DIR/03-mixed-load.json" \
  tests/load/k6/scenarios/03-mixed-load.js

echo "✓ Mixed load test complete"
sleep 30

# Test 4: Spike/Stress Test
echo ""
echo "[4/4] Running Spike/Stress Test..."
k6 run \
  --out=html="$REPORT_DIR/04-spike-test.html" \
  --out=json="$REPORT_DIR/04-spike-test.json" \
  tests/load/k6/scenarios/04-spike-test.js

echo "✓ Spike test complete"

echo ""
echo "========================================="
echo "All tests complete!"
echo "Reports available in: $REPORT_DIR"
echo "========================================="