#!/bin/bash
set -e

echo "🧪 Running Purplex Tests..."
echo "================================"

# Backend tests
echo ""
echo "📦 Backend Tests..."
echo "--------------------------------"
pytest tests/ -v --cov=purplex --cov-report=term-missing

# Frontend tests (if vitest is installed)
if [ -f "purplex/client/vitest.config.ts" ]; then
    echo ""
    echo "🎨 Frontend Tests..."
    echo "--------------------------------"
    cd purplex/client
    npm test -- --run
    cd ../..
else
    echo ""
    echo "⚠️  Frontend tests not yet configured"
fi

echo ""
echo "✅ All tests completed!"
echo "================================"