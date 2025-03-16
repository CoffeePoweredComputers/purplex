#!/bin/bash
# Start both Django backend and Vue frontend

cd "$(dirname "$0")"

# Activate virtual environment
echo "Activating virtual environment..."
source env/bin/activate

# Load problems and problem sets
echo "Loading problems..."
python manage.py load_problems

echo "Loading problem sets..."
python manage.py load_problemsets

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

# Start both servers
echo "Starting servers..."

if [ "$1" == "prod" ]; then
  echo "Running in production mode..."
  export DJANGO_DEBUG=False
else
  echo "Running in development mode..."
  export DJANGO_DEBUG=True
fi

yarn $1
