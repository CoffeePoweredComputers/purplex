# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Purplex is an educational coding challenge platform with AI-powered problem generation, real-time Docker-based code execution, and comprehensive progress tracking. It features an EiPL (Explain in Plain Language) submission system and a multi-modal hint system (Variable Fade, Subgoal Highlighting, Suggested Trace).

## Tech Stack

- **Backend**: Django 5.0 + Django REST Framework
- **Frontend**: Vue 3 + TypeScript + Vite (in `purplex/client/`)
- **Database**: PostgreSQL 15 (SQLite in legacy dev)
- **Task Queue**: Celery 5.x with Redis broker + gevent workers
- **Auth**: Firebase Authentication (mock in dev)
- **Code Execution**: Docker containers via Docker-in-Docker
- **AI**: OpenAI GPT-4 API

## Development Commands

```bash
# Quick start - starts all services (PostgreSQL, Redis, Django, Celery, Vue, Flower)
./start.sh

# Or use Make targets
make dev                    # Start development environment
make stop                   # Stop all services
make migrate                # Run database migrations
make test                   # Run all tests
make test-unit              # Run unit tests only
make test-coverage          # Run with coverage report
make lint                   # Run linters (flake8 + eslint)
make format                 # Format code (black + isort)
```

### Testing

```bash
pytest                       # All tests
pytest -m unit               # Unit tests only
pytest -m integration        # Integration tests only
pytest -m "not slow"         # Skip slow tests
pytest tests/test_setup.py   # Infrastructure tests (known working)
pytest -k test_name          # Run specific test by name

# Frontend tests
cd purplex/client && npm run test
```

### Manual Service Commands

```bash
# Backend
source env/bin/activate
python manage.py runserver
celery -A purplex.celery_simple worker -l info
celery -A purplex.celery_simple flower  # Monitoring at :5555

# Frontend
cd purplex/client && npm run dev
```

### Docker Development

```bash
COMPOSE_PROFILES=development docker-compose up -d
COMPOSE_PROFILES=development docker-compose build web-dev celery-dev
```

## Architecture

### Django Apps

- `purplex/problems_app/` - Problems, problem sets, courses, hints, test cases
- `purplex/submissions/` - Code submissions, execution results, scoring
- `purplex/progress/` - User progress tracking, analytics
- `purplex/users_app/` - User management, Firebase integration

### Key Patterns

- **Views**: Located in `views/` subdirectories (e.g., `problems_app/views/`)
- **Services**: Business logic in `services/` subdirectories
- **Tasks**: Celery async tasks in `tasks/` subdirectories
- **Repositories**: Data access layer in `repositories/` subdirectories

### API Flow for Submissions

1. User submits code via REST API
2. Validation + authorization checks (course enrollment, problem access)
3. Celery task queued for async execution
4. Code executed in isolated Docker container
5. Results stored, progress updated
6. Frontend polls for completion status

### Frontend Structure (`purplex/client/`)

- Composition API with TypeScript
- Vuex 4 for state management
- Services layer for API calls
- Composables with `use` prefix (e.g., `useTaskPolling`)

## Code Conventions

- **Python**: PEP 8, Google-style docstrings, type hints
- **TypeScript**: ESLint configured, Composition API
- **Models**: Singular names, snake_case fields
- **API**: RESTful, JSON, consistent error format

## Environment

Development uses `.env.development` with mock Firebase auth. Key vars:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `OPENAI_API_KEY` - Required for AI features

## Access Points (Development)

- Frontend: http://localhost:5173
- Django API: http://localhost:8000
- Django Admin: http://localhost:8000/admin
- Flower Monitor: http://localhost:5555
