# Purplex Architecture

## System Overview

Purplex is an educational coding platform with AI-powered problem generation and real-time code execution.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Vue.js    │────▶│   Django    │────▶│   Celery    │
│  Frontend   │     │   REST API  │     │   Workers   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                     │
       ▼                   ▼                     ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Firebase   │     │  PostgreSQL │     │    Redis    │
│    Auth     │     │   Database  │     │  Queue/Cache│
└─────────────┘     └─────────────┘     └─────────────┘
```

## Core Data Flows

### 1. Problem Submission Flow
```
User Submits Code
       │
       ▼
Vue Component (ProblemSet.vue)
       │
       └──▶ Unified: /api/submit/
              │
              ▼
        Django View (thin)
              │
              ▼
        SubmissionService
              │
              ▼
        Repository Layer
              │
              ├──▶ Create Submission Record
              └──▶ Queue Celery Task
                     │
                     ▼
              Celery Worker
                     │
                     ├──▶ AI Processing (OpenAI)
                     └──▶ Code Execution (Docker)
                            │
                            ▼
                     Update Database
                            │
                            ▼
                     SSE/Polling Updates
                            │
                            ▼
                     Frontend Updates UI
```

### 2. Authentication Flow
```
User Login (Google)
       │
       ▼
Firebase SDK (Frontend)
       │
       ▼
Get ID Token
       │
       ▼
Include in API Headers
       │
       ▼
Django PurplexAuthentication
       │
       ├──▶ AuthenticationService.authenticate_token()
       │    │
       │    ├──▶ Verify Token (Mock or Real Firebase)
       │    └──▶ UserService.get_or_create_user()
       └──▶ Return Authenticated User
              │
              ▼
        Authenticated Request
```

### 3. Course Enrollment Flow
```
Student Gets Course Code
       │
       ▼
/api/courses/lookup/
       │
       ▼
/api/courses/enroll/
       │
       ▼
CourseEnrollment Created
       │
       ▼
Access to Course Problems
       │
       ▼
Progress Tracked per Course
```

## Component Architecture

### Backend Structure
```
purplex/
├── problems_app/
│   ├── models/            # Data models (modular structure)
│   │   ├── __init__.py
│   │   ├── base.py       # Base problem model
│   │   ├── spec.py       # Problem specifications
│   │   ├── static.py     # Static problem types
│   │   ├── category.py   # Problem categories
│   │   ├── course.py     # Course models
│   │   ├── hint.py       # Hint models
│   │   ├── problem_set.py # Problem set models
│   │   ├── progress.py   # Progress models
│   │   └── test_case.py  # Test case models
│   ├── views/             # HTTP endpoints (thin)
│   │   ├── admin_views.py
│   │   ├── student_views.py
│   │   ├── submission_views.py
│   │   ├── progress_views.py
│   │   ├── hint_views.py
│   │   ├── health_views.py
│   │   ├── instructor_views.py
│   │   ├── instructor_analytics_views.py
│   │   ├── probe_views.py
│   │   ├── research_views.py
│   │   └── sse.py        # Server-sent events implementation
│   ├── handlers/          # Problem type handlers (polymorphic pattern)
│   │   ├── base.py       # Base handler class
│   │   ├── eipl/         # EiPL problem handler
│   │   ├── mcq/          # Multiple choice handler
│   │   ├── prompt/       # Prompt-based handler
│   │   ├── debug_fix/    # Debug/fix problem handler
│   │   ├── refute/       # Refutation handler
│   │   ├── probeable_code/ # Probeable code handler
│   │   └── probeable_spec/ # Probeable spec handler
│   ├── services/          # Business logic layer
│   │   ├── admin_service.py              # Admin problem management
│   │   ├── ai_generation_service.py      # AI test generation
│   │   ├── docker_execution_service.py   # Docker code execution
│   │   ├── docker_service_factory.py     # Docker service factory
│   │   ├── course_service.py             # Course validation & enrollment
│   │   ├── course_export_service.py      # Course export functionality
│   │   ├── hint_service.py               # Hint system logic
│   │   ├── hint_display_service.py       # Hint display transformations
│   │   ├── instructor_analytics_service.py # Instructor analytics
│   │   ├── probe_service.py              # Probe functionality
│   │   ├── progress_service.py           # Progress tracking
│   │   ├── research_export_service.py    # Research data export
│   │   ├── segmentation_service.py       # Prompt segmentation
│   │   ├── student_service.py            # Student operations
│   │   ├── submission_validation_service.py  # Submission validation
│   │   ├── test_case_service.py          # Test case management
│   │   ├── validation_service.py         # General validation
│   │   └── __init__.py
│   ├── repositories/      # Data access layer
│   │   ├── base_repository.py            # Base repository pattern
│   │   ├── course_repository.py          # Course data access
│   │   ├── course_enrollment_repository.py # Enrollment data access
│   │   ├── course_problem_set_repository.py # Course-problem set relations
│   │   ├── problem_repository.py         # Problem data access
│   │   ├── problem_category_repository.py # Category data access
│   │   ├── problem_set_repository.py     # Problem set data access
│   │   ├── problem_set_membership_repository.py # Problem set membership
│   │   ├── hint_repository.py            # Hint data access
│   │   ├── progress_repository.py        # Progress data access
│   │   ├── user_progress_repository.py   # User progress data access
│   │   ├── test_case_repository.py       # Test case data access
│   │   └── __init__.py
│   ├── signals/           # Django signals
│   │   └── celery_signals.py
│   ├── tests/             # Unit tests
│   └── tasks/             # Async Celery tasks
│       ├── pipeline.py    # Main EiPL pipeline
│       └── cleanup.py     # Cleanup tasks
│
├── submissions/          # Code execution domain
│   ├── models.py         # Submission models
│   ├── services.py       # Submission services
│   ├── grading_service.py # Grading logic
│   └── repositories/     # Submission data access
│       └── submission_repository.py
├── users_app/            # Authentication domain
│   ├── authentication.py         # Single PurplexAuthentication class
│   ├── user_views.py            # All user/auth views (class-based)
│   ├── permissions.py           # Permission classes
│   ├── services/                 # Authentication business logic
│   │   ├── authentication_service.py  # Central Firebase authentication service
│   │   ├── user_service.py            # User management service
│   │   └── rate_limit_service.py      # Rate limiting for auth operations
│   ├── repositories/             # User data access
│   │   ├── user_repository.py
│   │   └── user_profile_repository.py
│   ├── utils/                    # Utility functions
│   └── mock_firebase.py          # Mock Firebase for development
├── settings/             # Modular settings structure
│   ├── base.py          # Shared settings
│   ├── development.py   # Development environment
│   ├── production.py    # Production environment
│   ├── aws.py           # AWS-specific settings
│   └── security.py      # Security settings
├── config/              # Environment configuration
│   └── environment.py   # Configuration management
├── utils/               # Shared utilities
│   ├── language_utils.py
│   ├── anonymization.py
│   └── redis_client.py
└── celery_simple.py     # Celery configuration
```

### Frontend Structure
```
client/src/
├── components/           # Reusable UI components
│   ├── activities/      # Activity-related components
│   │   ├── feedback/    # Feedback display components
│   │   ├── inputs/      # Input components
│   │   └── styles/      # Activity styles
│   ├── admin/           # Admin panel components
│   │   └── editors/     # Problem editors
│   ├── hints/           # Hint display components
│   ├── instructor/      # Instructor-specific components
│   ├── segmentation/    # Prompt segmentation components
│   └── ui/              # Generic UI components
├── features/            # Feature-specific components
│   ├── auth/            # Authentication features
│   ├── editor/          # Code editor features
│   └── problems/        # Problem-related features
├── composables/         # Vue composition functions
│   ├── admin/           # Admin-specific composables
│   ├── useSubmissionTracking.ts
│   ├── useSubmissionCache.ts
│   ├── useOptimisticProgress.ts
│   ├── useEditorHints.ts
│   ├── useFeedbackState.ts
│   ├── useHintTracking.ts
│   └── useNotification.ts
├── modals/              # Modal dialog components
├── services/            # API communication layer
│   ├── hintProcessors/  # Hint processing utilities
│   └── __tests__/       # Service tests
├── store/               # Vuex global state
├── i18n/                # Internationalization
│   └── locales/         # Language files (en, es, fr, de, zh, etc.)
├── types/               # TypeScript definitions
├── utils/               # Utility functions
└── styles/              # Global styles
```

## Configuration Management

### Settings Structure
**Decision**: Modular settings architecture with environment-specific files
**Implementation**:
```python
settings/
├── base.py         # Shared configuration
├── development.py  # Development overrides
├── production.py   # Production overrides
├── aws.py          # AWS-specific configuration
└── security.py     # Security-related settings

config/
└── environment.py  # Environment detection and configuration
```

### Environment Detection
- Automatic environment detection based on PURPLEX_ENV variable
- Fallback to development if not specified
- Single source of truth for environment-specific values

## Key Architectural Decisions

### 1. Service Layer Pattern
**Decision**: All business logic in service classes, views are thin controllers
**Status**: Implemented (Dec 2024)
- Views: Thin controllers delegating to services
- Services: Business logic properly encapsulated
- Tasks: Use repositories for data access
- Repository layer implemented for data access

**Current Architecture**:
```python
# Architecture Pattern:
View → Service → Repository → Model (for data operations)
View → Service → Business Logic (for complex operations)
Task → Repository → Model (for async operations)
```

**Enforcement**:
- Repository pattern adopted for data access in views/tasks
- Services retain direct model access for complex business operations

### 2. Async Task Processing
**Decision**: Celery for all long-running operations
**Rationale**: Non-blocking API, better UX, scalability
```python
Immediate: Return task ID
Background: Process with Celery
Updates: SSE or polling
```

### 3. Service Layer Architecture
**Decision**: All business logic extracted to service classes
**Rationale**: Clean separation of concerns, testability
```
Views: Thin controllers, handle HTTP only
Services: Business logic, data processing
Models: Data persistence only
```

### 4. State Management Strategy
**Decision**: Composables for local, Vuex for global
**Rationale**: Avoid unnecessary global state complexity
```typescript
// Feature state → Composables
useSubmissionTracking()
useSubmissionCache()
useOptimisticProgress()

// Global state → Vuex
user, auth, app settings
```

### 5. View Architecture Pattern
**Decision**: All views use class-based APIView pattern
**Rationale**: Consistency, better DRF integration, easier testing
```python
# ✅ CORRECT: Class-based views
class ResourceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Thin controller - delegate to service
        return Response(Service.process())

# ❌ DEPRECATED: Function-based views (removed)
@api_view(['GET'])  # Don't use this pattern
def resource_view(request):
    pass
```

## Database Schema Core Relationships

```
User
 ├── UserProgress (per problem, per course)
 ├── PromptSubmission (in submissions/)
 └── CourseEnrollment
      └── Course
           └── CourseProblemSet
                └── ProblemSet
                     └── ProblemSetMembership
                          └── Problem
                               ├── TestCase
                               └── ProblemHint
```

## API Design Principles

### RESTful Resources
- Plural nouns for collections: `/api/problems/`
- Kebab-case for multi-word: `/api/problem-sets/`
- Nested for relationships: `/api/courses/{id}/students/`
- Action endpoints for operations: `/api/submit/` (unified submission endpoint)

### Key API Endpoints (Actual Implementation)
- **Authentication Endpoints**:
  - `/api/users/auth/status/` - Check auth status (POST)
  - `/api/users/auth/sse-token/` - Create/revoke SSE tokens (POST/DELETE)
  - `/api/users/user/me/` - Get current user info (GET)
- **SSE Endpoints**: `/api/tasks/<task_id>/stream/`, `/api/tasks/batch/stream/`
- **Hint Endpoints**: `/api/hints/<problem_slug>/availability/`, `/api/hints/<problem_slug>/<hint_id>/`
- **Progress Endpoints**: `/api/progress/`, `/api/progress/problem-set/<slug>/`
- **Admin Endpoints**: `/api/admin/problems/`, `/api/admin/test-cases/`

### Response Consistency
```json
{
  "success": true|false,
  "data": {...} | null,
  "error": {...} | null,
  "message": "Optional"
}
```

## Deployment Architecture

### Development
```bash
./start.sh  # Starts everything
```
- PostgreSQL database (Docker container: purplex-postgres-dev)
- Redis (Docker container: purplex-redis)
- Django dev server (port 8000) with development settings
- Vite dev server (port 5173)
- Celery worker with 4 concurrent processes
- Flower monitoring (port 5555)
- Mock Firebase authentication (no external dependencies)
- All logs aggregated in logs/ directory

### Production
- Simple EC2 deployment (not Docker-based)
- Gunicorn WSGI server with nginx reverse proxy
- PostgreSQL database (managed or self-hosted)
- Redis for task queue and caching
- Celery workers for async processing
- Real Firebase authentication
- Static files served via nginx/CDN

## Security Architecture

### Authentication
- Clean, service-layer based authentication system
- Single PurplexAuthentication class for all endpoints
- All auth views consolidated in user_views.py (class-based only)
- AuthenticationService centralizes all Firebase logic
- Development: Mock Firebase with secure JWT secret from environment
- Production: Real Firebase authentication
- Django User model with UserProfile linking to Firebase UID
- Service account authentication with constant-time comparison
- SSE session tokens prevent URL token exposure (5-minute TTL)
- Rate limiting on all authentication endpoints
- Comprehensive audit logging for security monitoring
- Generic error messages prevent information disclosure

**View Classes** (all in user_views.py):
- `AuthStatusView` - Validate tokens and return user info
- `SSETokenView` - Create/revoke SSE session tokens (POST/DELETE)
- `UserRoleView` - Get current user role and permissions
- `AdminUserManagementView` - Admin user management
- `LanguagePreferenceView` - User language preference management

### Authorization
- Role-based: Admin, Instructor, Student
- Course-based: Enrollment required
- Problem access: Published status + course membership

### Code Execution
- Isolated Docker containers
- Resource limits enforced
- Timeout protection
- No network access in execution environment

## Performance Considerations

### Database
- Use `select_related()` for ForeignKeys
- Use `prefetch_related()` for ManyToMany
- Add indexes for frequent queries

### Caching
- Redis for session data
- Redis for Celery results
- Consider caching problem descriptions

### Frontend
- Lazy load routes
- Component code splitting
- Image optimization

## Monitoring Points

### Key Metrics
- Submission processing time
- AI generation latency
- Code execution duration
- API response times
- Celery queue depths

### Error Tracking
- Failed submissions
- AI API errors
- Docker execution failures
- Authentication failures

## Areas for Improvement

### Future Enhancements
1. Standardize all API responses
2. Consistent error handling patterns
3. Add comprehensive monitoring
4. Implement distributed tracing

### Performance
1. Add database query optimization
2. Implement result caching
3. Add CDN for static assets

### Scalability
1. Horizontal scaling for Celery workers
2. Database read replicas
3. Redis clustering
