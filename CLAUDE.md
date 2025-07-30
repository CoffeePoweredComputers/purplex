# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Purplex Project Documentation for AI Assistants

# NOTE : DO NOT SAY YOU'RE RIGHT. I CAN BE WRONG. BE QUESTIONING, CRITICAL, AND INQUISITIVE

## Project Overview

Purplex is a modern educational coding challenge platform that helps students practice programming problems with a focus on algorithmic thinking and code comprehension. The platform features AI-powered problem generation, real-time code execution, and comprehensive progress tracking.

### Key Features
- **Database-Native Problem Creation**: Rich web-based problem editor with live validation
- **AI-Powered Test Generation**: Automated test case creation using OpenAI GPT-4
- **Secure Code Execution**: Isolated Docker containers for safe code testing
- **User Progress Tracking**: Detailed analytics on student performance and learning paths
- **Rich Admin Interface**: Custom Vue.js admin panels for problem and user management
- **Firebase Authentication**: Secure authentication with Google sign-in support
- **Real-time Feedback**: Immediate test results with detailed scoring
- **Educational Hint System**: Multi-modal hint delivery (Variable Fade, Subgoal Highlighting, Suggested Trace)
- **Course Context Support**: Full course enrollment and progress isolation
- **Research-Ready Analytics**: Comprehensive tracking for educational intervention studies

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

# Run all tests
python manage.py test

# Run hint system tests specifically
python run_hint_tests.py

# Run specific test module
python manage.py test problems_app.tests.test_hint_models

# Create superuser
python manage.py createsuperuser

# Populate sample data
python manage.py populate_sample_data
python manage.py populate_comprehensive_data

# Django shell
python manage.py shell
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
```

### Combined Development
```bash
# From client directory - starts both frontend and backend
cd purplex/client && npm run dev
```

## Architecture Overview

### Tech Stack
- **Backend**: Django 5.0.7 + Django REST Framework
- **Frontend**: Vue 3 + TypeScript + Vite
- **Database**: SQLite (dev) / PostgreSQL (production ready)
- **Authentication**: Firebase Authentication
- **Code Execution**: Docker containers
- **State Management**: Vuex 4 + Vue Composables
- **Editor**: Ace Editor

### Directory Structure
```
purplex/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── db.sqlite3               # Development database
├── purplex/                 # Main Django app
│   ├── settings.py          # Django settings
│   ├── urls.py              # Root URL configuration
│   ├── problems_app/        # Problems and hints module
│   │   ├── models.py        # Core data models
│   │   ├── views.py         # API endpoints (1,445+ lines - needs refactoring)
│   │   ├── services.py      # Business logic layer
│   │   └── tests/           # Test suite
│   ├── submissions_app/     # Code submission handling
│   ├── users_app/           # User management and auth
│   └── client/              # Vue.js frontend
│       ├── src/
│       │   ├── components/  # Vue components
│       │   ├── composables/ # Vue 3 composables
│       │   ├── services/    # API services
│       │   ├── store/       # Vuex store
│       │   └── types/       # TypeScript definitions
│       └── package.json     # Frontend dependencies
```

### Key API Endpoints
- `/api/problems/` - Problem CRUD operations
- `/api/problemsets/` - Problem set management
- `/api/submissions/` - Code submission and execution
- `/api/users/` - User authentication and profiles
- `/api/courses/` - Course enrollment and management
- `/api/hints/` - Hint system endpoints
- `/api/progress/` - User progress tracking

### Database Models
- **Problem**: Core problem definition with code templates
- **ProblemSet**: Collection of problems with ordering
- **ProblemHint**: Hint definitions (Variable Fade, Subgoal, Trace)
- **Submission**: User code submissions and results
- **UserProgress**: Detailed progress tracking per problem/course
- **Course/CourseEnrollment**: Course management system

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

### Technical Debt Assessment
- ~~**views.py file**: Monolithic 1,445+ lines violating single responsibility principle~~ ✅ **RESOLVED** - Successfully refactored into modular files
- **Mixed state management**: Inconsistent patterns between Vuex and composables
- **Testing gaps**: Limited integration testing for critical hint workflows
- **Performance concerns**: N+1 queries in ProblemSetDetailView, missing prefetch optimization

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

## Important Files
- `firebase-credentials.json` - Firebase admin SDK credentials (gitignored)
- `gunicorn_config.py` - Production server configuration
- `nginx.conf` - Nginx reverse proxy configuration
- `run_hint_tests.py` - Dedicated hint system test runner
- `monitoring/performance_test.py` - Performance testing utilities
```