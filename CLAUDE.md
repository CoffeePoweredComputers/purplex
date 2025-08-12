# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Purplex Project Documentation for AI Assistants

# NOTE : DO NOT SAY YOU'RE RIGHT. I CAN BE WRONG. BE QUESTIONING, CRITICAL, AND INQUISITIVE

## 📚 CRITICAL DOCUMENTATION - READ BEFORE CODING

**You MUST consult these documents before writing any code:**

1. **[STANDARDS.md](./STANDARDS.md)** - Coding standards, naming conventions, and patterns (MUST FOLLOW)
2. **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design, data flows, and architectural decisions
3. **[DEVELOPMENT.md](./DEVELOPMENT.md)** - Development workflows, common tasks, and troubleshooting
4. **[REFACTORING_PLAN.md](./REFACTORING_PLAN.md)** - Legacy code migration status (check before using any code)
5. **[PATTERNS.md](./PATTERNS.md)** - Implementation examples and templates

### Pre-Code Checklist
Before writing ANY code:
- [ ] Check STANDARDS.md for required patterns
- [ ] Check REFACTORING_PLAN.md to avoid using legacy code
- [ ] Check PATTERNS.md for similar implementations
- [ ] Use service layer for business logic (never in views)
- [ ] Follow naming conventions strictly

## 🤖 AUTOMATIC AGENT ENFORCEMENT

**You MUST use these agents automatically:**

### When Creating/Editing Code:
- **Before writing**: Run `pattern-matcher` agent to get correct template
- **Before using existing code**: Run `refactoring-guardian` to check for clean versions
- **After writing**: Run `standards-enforcer` to validate changes
- **For significant changes**: Run `architecture-validator`

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
# From client directory - starts both frontend and backend
cd purplex/client && npm run dev

# In separate terminals, also start:
# Terminal 1: Redis
redis-server

# Terminal 2: Celery worker
celery -A purplex.celery_simple worker -l info

# Terminal 3: Celery beat (if using scheduled tasks)
celery -A purplex.celery_simple beat -l info
```

## Architecture Overview

### Tech Stack
- **Backend**: Django 5.0.7 + Django REST Framework
- **Frontend**: Vue 3 + TypeScript + Vite
- **Database**: SQLite (dev) / PostgreSQL (production ready)
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
├── db.sqlite3               # Development database
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
│   │   │   ├── eipl_clean.py      # Clean EiPL implementation
│   │   │   ├── sse_views.py       # Server-sent events
│   │   │   ├── sse_clean.py       # Clean SSE implementation
│   │   │   ├── progress_views.py  # Progress tracking
│   │   │   └── hint_views.py      # Hint system endpoints
│   │   ├── course_views.py  # Course management views
│   │   ├── services.py      # Business logic layer
│   │   ├── tasks/           # Celery async tasks
│   │   │   ├── pipeline.py         # Legacy task pipeline
│   │   │   └── pipeline_clean.py   # Clean task implementation
│   │   └── tests/           # App-specific tests
│   ├── submissions_app/     # Code submission handling
│   ├── users_app/           # User management and auth
│   │   └── authentication.py # Firebase authentication
│   └── client/              # Vue.js frontend
│       ├── src/
│       │   ├── components/  # Vue components
│       │   ├── features/    # Feature-specific components
│       │   ├── composables/ # Vue 3 composables (useSSE, useCleanSubmission)
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

## Recent System Changes (Hint System Implementation)

### Architecture Overview
- **Full-stack hint system**: Complete implementation across Django backend, Vue.js frontend, and database schema
- **Three hint types**: Variable Fade (🏷️), Subgoal Highlighting (🎯), and Suggested Trace (🔍)
- **Attempt-based gating**: Hints unlock after configurable minimum attempts (default: 3)
- **Course context integration**: Full support for course enrollment and progress isolation
- **Admin management**: Comprehensive hint authoring and configuration interface

### Critical Issues Requiring Immediate Attention

⚠️ **PRODUCTION BLOCKERS** - These must be fixed before deployment:
1. **Missing Async Processing**: AI operations in EiPLSubmissionView are synchronous and block requests
2. **Rate Limiting Missing**: No rate limiting on submission endpoints, allowing potential abuse
3. **Input Validation Gaps**: EiPL prompts lack length validation and sanitization
4. **Security Configuration**: CSRF_COOKIE_SECURE = False (should be True in production), logging exposes sensitive data

⚠️ **USER EXPERIENCE ISSUES** - Recently fixed:
1. ~~**Poor Error Messages**: Frontend showed generic "Failed to load hint content" instead of helpful "need more attempts" messages~~ ✅ **FIXED**
2. ~~**Missing Attempt Requirements**: No indication of current attempts vs required attempts for locked hints~~ ✅ **FIXED**

### Technical Debt and Improvements
- ✅ **RESOLVED**: Views refactored from monolithic `views.py` into modular structure
- **Clean implementations**: New clean versions alongside legacy code (`eipl_clean.py`, `sse_clean.py`, `pipeline_clean.py`)
- **Mixed state management**: Inconsistent patterns between Vuex and composables
- **Testing coverage**: Both Django tests and pytest infrastructure available
- **Performance optimizations**: Consider prefetch_related for N+1 query issues

### Architecture Quality Score: 8.5/10
**Strengths**: Clean separation of concerns, modern technology stack, research-ready design
**Weaknesses**: Performance optimization needed, testing infrastructure gaps, scalability planning required

## Development Guidelines

### Code Quality Standards
- **CRITICAL**: All database logic must be tested with comprehensive edge cases
- **SECURITY**: Input validation required on both frontend and backend for all user content
- **PERFORMANCE**: Async processing mandatory for all AI and external service calls
- **ARCHITECTURE**: Service layer pattern required - no business logic in views

### Testing Requirements
- Integration tests mandatory for all new features
- Frontend component tests required for complex user interactions
- Performance testing required for code execution and hint processing
- Security testing required for all user input handling

### Deployment Prerequisites
- Fix critical bugs identified in system review before any production deployment
- Complete security audit and implement rate limiting
- Performance testing under load with realistic user scenarios
- Comprehensive error handling and logging implementation

## Environment Variables
```bash
# Django settings
DJANGO_DEBUG=True                    # Set to False in production
DJANGO_SECRET_KEY=your-secret-key    # Required for production
OPENAI_API_KEY=your-openai-key       # For AI-powered features

# Firebase (backend)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-credentials.json

# Database (production)
DATABASE_URL=postgres://user:pass@host:port/dbname

# Redis (production caching)
REDIS_URL=redis://localhost:6379/0
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
- `purplex/problems_app/tasks/pipeline_clean.py` - Clean EiPL task implementation

## High-Level Architecture Patterns

### Async Task Processing with Celery
The application uses Celery for asynchronous processing of long-running tasks:
- **EiPL Processing**: AI-powered natural language code generation via `pipeline.execute_eipl` task
- **Code Execution**: Secure Docker-based code execution happens in Celery workers
- **Task Pipeline**: Main tasks include:
  - `pipeline.generate_variations` - Generate code variations from EiPL
  - `pipeline.segment_prompt` - Parse and segment user prompts
  - `pipeline.save_submission` - Save and process submissions
  - `pipeline.execute_eipl` - Complete EiPL pipeline execution
- **Task Tracking**: Tasks are tracked with unique IDs, status polling available via API
- **Queue Configuration**: Multiple queues in production (high_priority, ai_operations, analytics, maintenance)
- **Clean vs Legacy**: Both `pipeline.py` (legacy) and `pipeline_clean.py` (refactored) implementations exist

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