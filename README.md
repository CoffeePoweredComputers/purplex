# Purplex - Educational Coding Challenge Platform

A modern educational platform for coding challenges with AI-powered problem generation, real-time code execution, and comprehensive progress tracking.

## Documentation

Essential documentation for developers working on Purplex:

### Core Documentation
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design, data flows, and architectural decisions
- **[STANDARDS.md](./STANDARDS.md)** - Coding standards, naming conventions, and required patterns
- **[PATTERNS.md](./PATTERNS.md)** - Implementation examples and code templates
- **[DEVELOPMENT.md](./DEVELOPMENT.md)** - Development workflows, setup guides, and troubleshooting

### Specialized Guides
- **[tests/TESTING_FRAMEWORK.md](./tests/TESTING_FRAMEWORK.md)** - Comprehensive testing guide and patterns
- **[SIMPLE_AWS_DEPLOYMENT.md](./SIMPLE_AWS_DEPLOYMENT.md)** - Production deployment guide
- **[CLAUDE.md](./CLAUDE.md)** - AI assistant configuration and project instructions

**Before writing any code**, consult STANDARDS.md and PATTERNS.md for required implementation patterns.

## Authentication Setup

### Development Environment
Development uses **mock Firebase authentication** - no external setup required! The mock system automatically handles authentication for testing.

### Production Environment
Production uses real Firebase authentication:

1. **Firebase Admin SDK Credentials**
   
   a. Go to the Firebase Console: https://console.firebase.google.com/
   b. Select your project
   c. Go to Project Settings > Service accounts
   d. Click "Generate new private key" to download the credentials file
   e. Save this file as `firebase-credentials.json` in the project root directory
   
   f. Set the environment variable:
   ```bash
   export FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json
   ```

2. **Enabling Google Sign-In**
   - In Firebase Console, go to Authentication > Sign-in method
   - Enable Google as a sign-in provider
   - Add authorized domains if necessary

## Prerequisites

- **Python 3.11+** with pip and venv
- **Docker** (required for PostgreSQL and Redis containers)
- **Node.js 20+** with npm/yarn
- **Git** (for version control)

## Database Setup

### Using Docker (Recommended)
```bash
# Start PostgreSQL container for development
docker run -d --name purplex-postgres-dev \
  -e POSTGRES_DB=purplex_dev \
  -e POSTGRES_USER=purplex_user \
  -e POSTGRES_PASSWORD=devpass \
  -p 5432:5432 \
  -v purplex_postgres_dev_data:/var/lib/postgresql/data \
  postgres:15-alpine
```

### Manual Installation (Optional)
```bash
# Create PostgreSQL database for development
sudo -u postgres createdb purplex_dev
sudo -u postgres createuser purplex_user -P  # Enter password: devpass
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE purplex_dev TO purplex_user;"
```

### Environment Configuration

A complete `.env.development` file is already provided in the repository with all necessary development settings. You only need to update the OpenAI API key:

```bash
# Edit .env.development and set your OpenAI API key
# Change this line:
OPENAI_API_KEY="your-openai-api-key-here"

# All other settings are pre-configured for development including:
# - DATABASE_URL=postgresql://purplex_user:devpass@localhost:5432/purplex_dev  
# - REDIS_URL=redis://localhost:6379/0
# - Mock Firebase authentication enabled
# - Debug mode and development settings

# Load environment variables
export $(cat .env.development | grep -v '^#' | xargs)
```

## Running the Project

### Quick Start (Recommended)

**Option 1: Use the automated startup script**
```bash
# Make script executable (first time only)
chmod +x start.sh

# Start everything with one command
./start.sh
```

This script automatically starts and manages:
- PostgreSQL database (Docker container)
- Redis server (Docker container)  
- Django development server (port 8000)
- Celery worker with proper configuration
- Vue.js frontend (port 5173)
- Flower monitoring (port 5555)

**Access points after startup:**
- Frontend: http://localhost:5173
- Django API: http://localhost:8000
- Django Admin: http://localhost:8000/admin
- Flower Monitor: http://localhost:5555

Press `Ctrl+C` once for graceful shutdown, twice for force quit.

### Manual Setup (Alternative)

If you prefer to run services individually:

**1. Setup Python Environment**
```bash
# Create and activate virtual environment
python -m venv env
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Load environment variables
export $(cat .env.development | grep -v '^#' | xargs)
```

**2. Start Database Services**
```bash
# Start PostgreSQL (use Docker command from Database Setup section above)
# Start Redis
docker run -d --name purplex-redis -p 6379:6379 redis:7-alpine
```

**3. Initialize Database**
```bash
# Run migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser

# Load sample data (optional)
python manage.py populate_sample_data
```

**4. Start Backend Services**
```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker  
celery -A purplex.celery_simple worker -l info

# Terminal 3: Flower monitoring (optional)
celery -A purplex.celery_simple flower
```

**5. Start Frontend**
```bash
cd purplex/client

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

## Testing

Run the comprehensive test suite:

```bash
# Activate virtual environment
source env/bin/activate

# Run all tests
pytest

# Run specific test categories
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m "not slow"        # Skip slow tests

# Run with coverage
pytest --cov=purplex

# Run frontend tests
cd purplex/client
npm run test
```

## Technology Stack

### Backend
- **Django 5.0.7** - Web framework
- **Django REST Framework 3.15.2** - API framework
- **PostgreSQL 15** - Primary database
- **Redis 7** - Cache and message broker
- **Celery 5.3.4** - Asynchronous task queue
- **Firebase Admin SDK** - Authentication (production)
- **OpenAI API** - AI-powered features
- **Docker** - Container runtime

### Frontend  
- **Vue 3** - Frontend framework
- **TypeScript** - Type safety
- **Vite 5** - Build tool and dev server
- **Vuex 4** - State management
- **Ace Editor** - Code editing
- **Axios** - HTTP client

### Development & Testing
- **Pytest 8.3.0** - Python testing
- **Vitest** - Frontend testing
- **ESLint** - Code linting
- **Gunicorn** - Production WSGI server

## Common Issues & Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL container is running
docker ps | grep purplex-postgres

# View PostgreSQL logs
docker logs purplex-postgres-dev

# Reset PostgreSQL container
docker stop purplex-postgres-dev
docker rm purplex-postgres-dev
# Then run the Docker command from Database Setup section
```

### Redis Connection Issues
```bash
# Check if Redis is running
docker ps | grep purplex-redis

# Test Redis connection
docker exec purplex-redis redis-cli ping

# Reset Redis container  
docker stop purplex-redis && docker rm purplex-redis
docker run -d --name purplex-redis -p 6379:6379 redis:7-alpine
```

### Celery Not Working
```bash
# Check Celery worker logs
tail -f logs/celery_worker.log

# Restart Celery worker
pkill -f "celery.*purplex"
celery -A purplex.celery_simple worker -l info

# Clear Celery tasks (if stuck)
celery -A purplex.celery_simple purge
```

### Frontend Build Issues
```bash
# Clear npm cache and reinstall
cd purplex/client
rm -rf node_modules package-lock.json
npm install

# Check for TypeScript errors
npm run typecheck
```

### Port Already in Use
```bash
# Kill processes on common ports
sudo lsof -t -i:8000 | xargs kill -9  # Django
sudo lsof -t -i:5173 | xargs kill -9  # Vue
sudo lsof -t -i:5555 | xargs kill -9  # Flower
```

### Environment Variables Not Loading
```bash
# Verify .env.development exists and has correct format
cat .env.development | grep -v '^#'

# Manually export variables
export $(cat .env.development | grep -v '^#' | xargs)

# Check if variables are set
echo $DATABASE_URL
echo $OPENAI_API_KEY
```

## Important Notes

⚠️ **Development Only**: The current configuration is for development. Do not use these credentials or settings in production.

⚠️ **OpenAI API Key Required**: Many features require a valid OpenAI API key. Set this in `.env.development`.

⚠️ **Docker Required**: PostgreSQL and Redis run in Docker containers. Ensure Docker is installed and running.

⚠️ **Virtual Environment**: Always activate the Python virtual environment (`source env/bin/activate`) before running Django commands.

✅ **Mock Authentication**: Development uses mock Firebase authentication - no real Firebase setup required for development.

✅ **Auto-Reload**: Both Django and Vue development servers automatically reload on code changes.