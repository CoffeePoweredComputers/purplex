#!/bin/bash
# Start both Django backend and Vue frontend

cd "$(dirname "$0")"

# Set OpenAI API key (replace with your actual key)
export OPENAI_API_KEY="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"

# Activate virtual environment
echo "Activating virtual environment..."
source env/bin/activate

# migrate
echo "Migrating database..."
python manage.py migrate

# Install frontend dependencies if needed
echo "Installing frontend dependencies..."
cd purplex/client
yarn install

# Verify Vue is installed properly
if [ ! -d "node_modules/vue" ]; then
  echo "Installing Vue as dependency..."
  yarn add vue@3.3.11
fi

if [ ! -d "node_modules/@vue/compiler-sfc" ]; then
  echo "Installing Vue compiler..."
  yarn add @vue/compiler-sfc -D
fi

# Go back to project root
cd ../..

# Start both servers
echo "Starting servers..."

if [ "$1" == "prod" ]; then
  echo "Running in production mode..."
  export DJANGO_DEBUG=False
else
  echo "Running in development mode..."
  export DJANGO_DEBUG=True
fi

# Start Django backend in background
echo "Starting Django backend on port 8000..."
python manage.py runserver 0.0.0.0:8000 &
DJANGO_PID=$!

# Give Django a moment to start
sleep 2

# Start Vite frontend
echo "Starting Vite frontend..."
cd purplex/client
yarn vite

# When frontend exits, kill Django server
kill $DJANGO_PID
