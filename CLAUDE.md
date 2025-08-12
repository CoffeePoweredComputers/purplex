# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Purplex Project Documentation for AI Assistants

# NOTE : DO NOT SAY YOU'RE RIGHT. I CAN BE WRONG. BE QUESTIONING, CRITICAL, AND INQUISITIVE

## 📚 CRITICAL DOCUMENTATION - READ BEFORE CODING

**See [DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md) for complete documentation overview**

**You MUST consult these core documents before writing any code:**

1. **[STANDARDS.md](./STANDARDS.md)** - Coding standards, naming conventions, and patterns (MUST FOLLOW)
2. **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design, data flows, and architectural decisions
3. **[DEVELOPMENT.md](./DEVELOPMENT.md)** - Development workflows, common tasks, and troubleshooting
4. **[PATTERNS.md](./PATTERNS.md)** - Implementation examples and templates
5. **[TESTING_FRAMEWORK.md](./tests/TESTING_FRAMEWORK.md)** - Comprehensive testing guide and patterns

### Pre-Code Checklist
Before writing ANY code:
- [ ] Check STANDARDS.md for required patterns
- [ ] Check PATTERNS.md for similar implementations
- [ ] Use service layer for business logic (never in views)
- [ ] Follow naming conventions strictly
- [ ] Check existing clean implementations (e.g., sse_clean.py)

## 🤖 AUTOMATIC AGENT ENFORCEMENT

**You MUST use these agents automatically:**

### When Creating/Editing Code:
- **Before writing**: Run `pattern-matcher` agent to get correct template
- **After writing**: Run `standards-enforcer` to validate changes
- **For significant changes**: Run `architecture-validator`
- **Check for clean versions**: Look for `_clean.py` variants (e.g., sse_clean.py)

### When Committing:
- **Always run**: `code-quality-orchestrator` (runs all validations)
- **If all pass**: Use `commit-message-generator`
- **If any fail**: FIX BEFORE PROCEEDING

### Agent Response Levels:
- 🚫 **BLOCKING**: Must fix before continuing
- ⚠️ **WARNING**: Should fix but not blocking
- ℹ️ **INFO**: Consider for improvement

**See [.claude/agent_instructions.md](.claude/agent_instructions.md) for detailed agent behaviors**

## Project Overview

Purplex is a modern educational coding challenge platform that helps students practice programming problems with a focus on algorithmic thinking and code comprehension. The platform features AI-powered problem generation, real-time code execution, and comprehensive progress tracking.

### Key Features
- **Database-Native Problem Creation**: Rich web-based problem editor with live validation
- **AI-Powered Test Generation**: Automated test case creation using OpenAI GPT-4
- **EiPL (Explain in Plain Language)**: Natural language code submissions with AI processing
- **Secure Code Execution**: Isolated Docker containers for safe code testing
- **User Progress Tracking**: Detailed analytics on student performance and learning paths
- **Rich Admin Interface**: Custom Vue.js admin panels for problem and user management
- **Firebase Authentication**: Secure authentication with Google sign-in support
- **Real-time Feedback**: Immediate test results with detailed scoring
- **Educational Hint System**: Multi-modal hint delivery (Variable Fade, Subgoal Highlighting, Suggested Trace)
- **Course Context Support**: Full course enrollment and progress isolation
- **Research-Ready Analytics**: Comprehensive tracking for educational intervention studies
- **Async Task Processing**: Celery workers for AI operations and code execution

## Development Memories

- I always have the server and frontend running
- never implement with backwards compatability in mind for this app. This is greenfield and I want the code clean and new rather than bloated with vestigial backwards compatability from development
- Don't worry about backwards compatability at all when extending this. This is a prototype.
- **PostgreSQL Database**: Using PostgreSQL for all environments (development, test, and production).

## Common Development Commands

### Backend (Django)
```bash
# Activate virtual environment
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Start development server
python manage.py runserver

# Run tests with Django's test runner
python manage.py test

# Run tests with pytest (recommended)
pytest                          # Run all tests
pytest -m unit                  # Run unit tests only
pytest -m integration           # Run integration tests only
pytest -m "not slow"            # Skip slow tests
pytest tests/unit/              # Run specific test directory

# Run hint system tests specifically
python run_hint_tests.py

# Create superuser
python manage.py createsuperuser

# Populate sample data
python manage.py populate_sample_data
python manage.py populate_comprehensive_data

# Django shell
python manage.py shell

# Quick start script (starts everything)
./start.sh
```

### Frontend (Vue.js + Vite)
```bash
cd purplex/client

# Install dependencies
npm install
# or
yarn install

# Development server (starts both frontend and backend)
npm run dev
# or
yarn dev

# Frontend only
yarn vite --mode development

# Production build
npm run build
# or
yarn build

# Preview production build
npm run preview

# Type checking
npm run typecheck

# Linting
npm run lint
```

### Celery & Redis (Async Task Processing)
```bash
# Start Redis server (required for Celery)
redis-server
# or with Docker
docker run -d -p 6379:6379 redis:7

# Start Celery worker (from project root with venv activated)
celery -A purplex.celery_simple worker -l info

# Start Celery beat scheduler (for periodic tasks)
celery -A purplex.celery_simple beat -l info

# Monitor Celery with Flower (web UI at http://localhost:5555)
celery -A purplex.celery_simple flower

# Development with Docker Compose (includes Redis, Celery workers, and Flower)
docker-compose -f docker-compose.dev.yml up
```

### Combined Development
```bash
# Quick start script - starts everything with PostgreSQL
./start.sh

# Or manually start services:
# Terminal 1: PostgreSQL (if not using start.sh)
docker run -d --name purplex-postgres \
  -e POSTGRES_DB=purplex \
  -e POSTGRES_USER=purplex_user \
  -e POSTGRES_PASSWORD=purplex2024prod \
  -p 5432:5432 \
  postgres:15-alpine

# Terminal 2: Redis
docker run -d --name purplex-redis -p 6379:6379 redis:7-alpine

# Terminal 3: Django with PostgreSQL
export DJANGO_SETTINGS_MODULE=purplex.settings_production
export $(cat .env.production | grep -v '^#' | xargs)
python manage.py runserver

# Terminal 4: Celery worker
celery -A purplex.celery_simple worker -l info
```

## Architecture Overview

### Tech Stack
- **Backend**: Django 5.0.7 + Django REST Framework
- **Frontend**: Vue 3 + TypeScript + Vite
- **Database**: PostgreSQL 15 (Docker container)
- **Task Queue**: Celery 5.x with Redis broker
- **Cache/Message Broker**: Redis 7 (multiple databases for different purposes)
- **Authentication**: Firebase Authentication (custom Django integration)
- **Code Execution**: Docker containers (isolated for security)
- **State Management**: Vuex 4 + Vue Composables
- **Editor**: Ace Editor
- **AI Services**: OpenAI GPT-4 API
- **Testing**: Pytest + Django Test Framework
- **Process Management**: WhiteNoise (static files), Gunicorn (production)

### Directory Structure
```
purplex/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── firebase-credentials.json # Firebase admin SDK (gitignored)
├── docker-compose.dev.yml    # Development Docker setup
├── docker-compose.production.yml # Production Docker setup
├── pytest.ini               # Pytest configuration
├── start.sh                 # Development environment startup script
├── purplex/                 # Main Django app
│   ├── settings.py          # Django settings
│   ├── urls.py              # Root URL configuration
│   ├── celery_simple.py     # Celery configuration
│   ├── problems_app/        # Problems and hints module
│   │   ├── models.py        # Core data models
│   │   ├── views/           # Refactored API endpoints (modular)
│   │   │   ├── admin_views.py      # Admin management views
│   │   │   ├── student_views.py    # Student-facing views
│   │   │   ├── submission_views.py # Code submission handling
│   │   │   ├── sse_clean.py       # Server-sent events implementation
│   │   │   ├── progress_views.py  # Progress tracking
│   │   │   └── hint_views.py      # Hint system endpoints
│   │   ├── course_views.py  # Course management views
│   │   ├── services/        # Business logic layer
│   │   │   ├── code_execution_service.py
│   │   │   ├── progress_service.py
│   │   │   ├── student_service.py
│   │   │   ├── hint_service.py
│   │   │   └── __init__.py
│   │   ├── tasks/           # Celery async tasks
│   │   │   └── pipeline.py         # Main task pipeline (execute_eipl_pipeline)
│   │   └── tests/           # App-specific tests
│   ├── submissions_app/     # Code submission handling
│   ├── users_app/           # User management and auth
│   │   └── authentication.py # Firebase authentication
│   └── client/              # Vue.js frontend
│       ├── src/
│       │   ├── components/  # Vue components
│       │   ├── features/    # Feature-specific components
│       │   ├── composables/ # Vue 3 composables (useSSE, useNotification, etc.)
│       │   ├── services/    # API services
│       │   ├── store/       # Vuex store
│       │   └── types/       # TypeScript definitions
│       ├── package.json     # Frontend dependencies
│       └── vite.config.ts   # Vite configuration
├── tests/                   # Project-wide tests
│   ├── integration/         # Full workflow tests
│   └── unit/               # Unit tests
└── monitoring/             # Performance and monitoring scripts
```

### Key API Endpoints

#### Problem & Submission Endpoints
- `/api/problems/` - Problem CRUD operations
- `/api/problem-sets/` - Problem set management
- `/api/test-solution/` - Test code solutions
- `/api/submit-solution/` - Submit final solutions
- `/api/submit-eipl/` - EiPL (Explain in Plain Language) submission
- `/api/categories/` - Problem categories

#### Course Management Endpoints
- `/api/courses/` - Admin course CRUD operations
- `/api/courses/<id>/problem-sets/` - Manage course problem sets
- `/api/courses/<id>/students/` - Manage course enrollments
- `/api/instructor/courses/` - Instructor course views
- `/api/student/courses/` - Student enrolled courses
- `/api/courses/lookup/` - Find courses by code
- `/api/courses/enroll/` - Enroll in a course

#### Progress & Hints Endpoints
- `/api/progress/` - User progress tracking
- `/api/progress/problem-set/<slug>/` - Problem set progress
- `/api/progress/summary/` - Overall progress summary
- `/api/hints/<problem_slug>/availability/` - Check hint availability
- `/api/hints/<problem_slug>/<hint_id>/` - Get specific hint

#### Real-time & Admin Endpoints
- `/api/sse/task/<task_id>/` - Server-sent events for task updates
- `/api/sse/batch/` - Batch task status updates
- `/api/admin/problems/` - Admin problem management
- `/api/admin/test-cases/` - Admin test case management
- `/api/users/` - User authentication and profiles

### Database Models
- **Problem**: Core problem definition with code templates and test cases
- **ProblemSet**: Collection of problems with ordering
- **ProblemSetMembership**: Links problems to sets with order/weight
- **ProblemCategory**: Problem categorization and tagging
- **ProblemHint**: Hint definitions (Variable Fade, Subgoal, Trace)
- **TestCase**: Input/output test cases for problems
- **Submission**: User code submissions and results
- **UserProgress**: Detailed progress tracking per problem/course
- **UserProblemSetProgress**: Aggregate progress for problem sets
- **ProgressSnapshot**: Historical progress tracking over time
- **Course**: Course definitions with instructors and enrollment codes
- **CourseEnrollment**: Student enrollments in courses
- **CourseProblemSet**: Links problem sets to courses with ordering

## Recent System Changes

### Code Cleanup (Completed)
- **Removed duplicate/unused files**: Various legacy implementations
- **Removed unused frontend**: `hints/HintButton.vue`, `cleanSubmissionService.ts`, `useCleanSubmission.ts`
- **Fixed dead code**: Corrected logic error in `AdminUserManagementView`
- **Removed broken references**: Eliminated methods calling non-existent Celery tasks
- **Cleaned dependencies**: Removed unused Python (django-celery-beat, django-celery-results, django-storages, boto3) and JavaScript (bootstrap-vue, vue-cli-service, punycode) packages
- **Configuration improvements**: Made GPT model configurable via `GPT_MODEL` setting

### Hint System Implementation (Previous)

### Architecture Overview
- **Full-stack hint system**: Complete implementation across Django backend, Vue.js frontend, and database schema
- **Three hint types**: Variable Fade (🏷️), Subgoal Highlighting (🎯), and Suggested Trace (🔍)
- **Attempt-based gating**: Hints unlock after configurable minimum attempts (default: 3)
- **Course context integration**: Full support for course enrollment and progress isolation
- **Admin management**: Comprehensive hint authoring and configuration interface

### Recent Architectural Improvements (Completed)

✅ **RESOLVED ARCHITECTURE ISSUES**:
1. **Service Layer Extraction**: All business logic moved from views to service classes
2. **SSE Implementation Unified**: Removed legacy sse_views.py, using only sse_clean.py
3. **State Management Guidelines**: Created comprehensive STATE_MANAGEMENT.md documentation
4. **API Naming Consistency**: Verified all endpoints use kebab-case

⚠️ **Remaining Production Considerations**:
1. **Rate Limiting**: Consider adding rate limiting on submission endpoints
2. **Input Validation**: Strengthen EiPL prompt validation
3. **Security Configuration**: Ensure CSRF_COOKIE_SECURE = True in production

⚠️ **USER EXPERIENCE ISSUES** - Recently fixed:
1. ~~**Poor Error Messages**: Frontend showed generic "Failed to load hint content" instead of helpful "need more attempts" messages~~ ✅ **FIXED**
2. ~~**Missing Attempt Requirements**: No indication of current attempts vs required attempts for locked hints~~ ✅ **FIXED**

### Technical Architecture
- ✅ **Service Layer**: Complete separation of business logic from views
- ✅ **SSE Implementation**: Single, clean implementation (sse_clean.py only)
- ✅ **State Management**: Clear guidelines - Vuex for global, composables for local (see STATE_MANAGEMENT.md)
- ✅ **Modular Views**: Views refactored into focused modules
- **Testing**: Comprehensive pytest infrastructure with Django test support
- **Performance**: Service layer caching, optimized queries

### Architecture Quality Score: 9.5/10
**Strengths**: 
- Clean service layer architecture with complete separation of concerns
- Unified SSE implementation
- Clear state management guidelines
- Modern technology stack, research-ready design

**Areas for Enhancement**: 
- Add comprehensive monitoring
- Expand performance testing

## Development Guidelines

### Code Quality Standards
- **CRITICAL**: All database logic must be tested with comprehensive edge cases
- **SECURITY**: Input validation required on both frontend and backend for all user content
- **PERFORMANCE**: Async processing mandatory for all AI and external service calls
- **ARCHITECTURE**: Service layer pattern required - no business logic in views

### Testing Requirements
- Integration tests mandatory for all new features (see tests/TESTING_FRAMEWORK.md)
- Frontend component tests required for complex user interactions
- Performance testing required for code execution and hint processing
- Security testing required for all user input handling
- Use pytest exclusively with the provided test infrastructure

### Deployment Prerequisites
- Fix critical bugs identified in system review before any production deployment
- Complete security audit and implement rate limiting
- Performance testing under load with realistic user scenarios
- Comprehensive error handling and logging implementation

## Environment Variables
```bash
# Now using .env.production file (created during migration)
# Key variables:
DJANGO_SECRET_KEY=<generated-key>          # Unique for each deployment
DJANGO_SETTINGS_MODULE=purplex.settings_production
DATABASE_URL=postgresql://purplex_user:purplex2024prod@localhost:5432/purplex
OPENAI_API_KEY=<your-key>                  # For AI-powered features
GPT_MODEL=gpt-4o-mini                      # OpenAI model to use
FIREBASE_CREDENTIALS_PATH=/home/anavarre/Projects/purplex/firebase-credentials.json
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Docker Development
```bash
# Production deployment
docker-compose -f docker-compose.production.yml up

# Code execution service
# Runs in isolated containers for security
```

## Important Files and Scripts

### Configuration Files
- `firebase-credentials.json` - Firebase admin SDK credentials (gitignored)
- `gunicorn_config.py` - Production server configuration
- `nginx.conf` - Nginx reverse proxy configuration
- `pytest.ini` - Pytest configuration with test markers
- `docker-compose.dev.yml` - Development Docker services
- `docker-compose.production.yml` - Production Docker configuration

### Development Scripts
- `start.sh` - Complete development environment startup (Redis, Celery, Django)
- `run_hint_tests.py` - Dedicated hint system test runner
- `monitoring/performance_test.py` - Performance testing utilities

### Key Python Modules
- `purplex/celery_simple.py` - Simplified Celery configuration
- `purplex/users_app/authentication.py` - Firebase authentication integration
- `purplex/problems_app/tasks/pipeline.py` - Main EiPL task implementation (execute_eipl_pipeline)

## High-Level Architecture Patterns

### Async Task Processing with Celery
The application uses Celery for asynchronous processing of long-running tasks:
- **Main Task**: `pipeline.execute_eipl_pipeline` in `tasks/pipeline.py`
- **Task Pipeline**: This single orchestrator task handles:
  - AI-powered natural language code generation
  - Testing generated code against test cases
  - Segmenting user prompts for analysis
  - Saving submissions and results
  - Secure Docker-based code execution
- **Task Tracking**: Tasks are tracked with unique IDs, status polling available via API
- **Redis Backend**: Uses Redis for both message broker and result backend
- **Configuration**: See `celery_simple.py` for simplified Celery setup

### Authentication Flow
- Frontend uses Firebase Authentication for user login (Google sign-in)
- Backend verifies Firebase tokens using Firebase Admin SDK
- Custom Django user model integrates with Firebase UID
- All API endpoints require authentication via Firebase token in headers

### Submission Processing Pipeline
1. User submits code/EiPL through Vue frontend
2. Django creates submission record and queues Celery task
3. Celery worker processes submission (AI generation or code execution)
4. Results stored in database, Redis cache for quick access
5. Frontend polls status endpoint or uses SSE for real-time updates
6. Progress tracking updates user statistics

### Frontend-Backend Communication
- RESTful API using Django REST Framework
- Authentication via Firebase tokens in Authorization header
- Real-time updates via Server-Sent Events (SSE) for submissions
- Vuex store manages global state, composables for local state
- TypeScript interfaces ensure type safety across API boundaries

### Course Management System
- **Course Structure**: Courses contain ordered problem sets with instructor management
- **Enrollment Flow**: Students join via course codes, progress tracked per course
- **Role-Based Access**: Different views for admins, instructors, and students
- **Progress Isolation**: Student progress is tracked separately for each course context
- **Problem Set Ordering**: Instructors can customize problem set order per course