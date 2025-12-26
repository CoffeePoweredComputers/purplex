# Development Workflow

## Code Quality Checks

Code quality is enforced through:
- **Linting**: `make lint` runs flake8 (Python) and eslint (TypeScript)
- **Formatting**: `make format` runs black and isort
- **Pre-commit hooks**: See `.pre-commit-config.yaml`
- **Code review**: Follow patterns in [STANDARDS.md](./STANDARDS.md) and [PATTERNS.md](./PATTERNS.md)

## Quick Start

```bash
# Start everything with one command
./start.sh

# Or manually:
source env/bin/activate

# Start PostgreSQL for development (if not using start.sh)
docker run -d --name purplex-postgres \
  -e POSTGRES_DB=purplex_dev \
  -e POSTGRES_USER=purplex_user \
  -e POSTGRES_PASSWORD=devpass \
  -p 5432:5432 \
  -v purplex_postgres_dev_data:/var/lib/postgresql/data \
  postgres:15-alpine

python manage.py runserver          # Terminal 1
cd purplex/client && npm run dev    # Terminal 2
redis-server                        # Terminal 3
celery -A purplex.celery_simple worker -l info  # Terminal 4
```

## Adding New Features

### 1. Adding a New Problem Type

**Files to modify:**
```
1. models.py         - Add model fields
2. services/         - Add business logic in appropriate service file
3. serializers.py    - Add API serialization
4. views/            - Add thin view in appropriate view file
5. urls.py          - Add route
6. Frontend component - Add UI
```

**Example: Adding "MultipleChoice" problem type**

```python
# 1. models.py
class Problem(models.Model):
    PROBLEM_TYPES = [
        ('code', 'Code'),
        ('multiple_choice', 'Multiple Choice'),  # NEW
    ]
    problem_type = models.CharField(choices=PROBLEM_TYPES)
    choices = models.JSONField(null=True, blank=True)  # NEW

# 2. services/problem_service.py (create new file if needed)
class ProblemService:
    @staticmethod
    def validate_multiple_choice_answer(problem, answer):
        """Business logic for checking MC answers."""
        correct = problem.choices.get('correct')
        return answer == correct

# 3. views/problem_views.py
class MultipleChoiceSubmitView(APIView):
    def post(self, request, problem_id):
        problem = get_object_or_404(Problem, id=problem_id)
        is_correct = ProblemService.validate_multiple_choice_answer(
            problem,
            request.data.get('answer')
        )
        return Response({'correct': is_correct})
```

### 2. Adding a New API Endpoint

**Standard pattern (MUST use class-based views):**
```python
# views/feature_views.py (or add to existing views file)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .permissions import IsAuthenticated

class FeatureView(APIView):
    """
    REQUIRED: All views must be class-based using APIView.
    Thin controller - delegates to service.
    """
    permission_classes = [IsAuthenticated]  # Always specify

    def get(self, request):
        # 1. Parse input
        params = request.query_params

        # 2. Call service (NO business logic here)
        result = FeatureService.process_feature(params)

        # 3. Return response
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request):
        # Multiple HTTP methods in same class
        data = request.data
        result = FeatureService.create_feature(data)
        return Response(result, status=status.HTTP_201_CREATED)

# services/feature_service.py (or add to existing service file)
class FeatureService:
    """Contains ALL business logic."""

    @staticmethod
    def process_feature(params):
        # Complex logic here
        pass

    @staticmethod
    def create_feature(data):
        # Creation logic here
        pass

# urls.py
urlpatterns = [
    path('api/feature/', FeatureView.as_view()),  # Single URL, multiple methods
]

# ❌ NEVER USE function-based views:
# @api_view(['GET'])  # Don't use this pattern
# def feature_view(request):
#     pass
```

### 3. Adding a Celery Task

**Standard pattern:**
```python
# tasks/feature_tasks.py
from celery import shared_task

@shared_task(name='feature.process')
def process_feature_async(feature_id):
    """Async processing task."""
    feature = Feature.objects.get(id=feature_id)
    # Long-running process
    return {'status': 'completed'}

# Usage in view/service
task = process_feature_async.delay(feature_id)
return {'task_id': task.id}
```

### 4. Adding a Vue Component

**Standard pattern:**
```vue
<!-- components/FeatureCard.vue -->
<template>
  <div class="feature-card">
    <!-- Template -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useFeature } from '@/composables/useFeature'

const props = defineProps<{
  featureId: number
}>()

// Use composable for logic
const { data, loading, error, fetchFeature } = useFeature()

// Component-specific logic
onMounted(() => {
  fetchFeature(props.featureId)
})
</script>
```

## Common Workflows

### Refactoring Legacy Code

1. **Identify legacy file** (e.g., `old_view.py`)
2. **Create clean version**: `old_view_clean.py`
3. **Refactor following standards**:
   - Move business logic to services
   - Standardize naming
   - Add proper error handling
4. **Update imports** to use clean version
5. **Test thoroughly**
6. **Replace original** with clean version

### Database Migrations

```bash
# After modifying models.py
python manage.py makemigrations
python manage.py migrate

# Check migration SQL (PostgreSQL)
python manage.py sqlmigrate problems_app 0001

# Reset all migrations (DEVELOPMENT ONLY - BE CAREFUL)
python manage.py migrate problems_app zero
python manage.py migrate submissions_app zero
python manage.py migrate users_app zero
rm purplex/problems_app/migrations/0*.py
rm purplex/submissions_app/migrations/0*.py
rm purplex/users_app/migrations/0*.py
python manage.py makemigrations
python manage.py migrate
```

### Testing Workflow

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_services.py

# Run with coverage
pytest --cov=purplex

# Run only fast tests
pytest -m "not slow"
```

### Debugging

#### Django Shell
```bash
python manage.py shell

# Example debugging - ALWAYS use service layer
from purplex.problems_app.services.admin_service import AdminProblemService
from purplex.problems_app.services.student_service import StudentService

# Never query models directly in shell for business logic
problems = AdminProblemService.get_all_problems_optimized()
student_problems = StudentService.get_active_problems()
```

#### Celery Task Debugging
```python
# Run task synchronously for debugging
from purplex.problems_app.tasks import process_submission

# Instead of: process_submission.delay(id)
result = process_submission(id)  # Runs immediately
```

#### Vue DevTools
- Install Vue DevTools browser extension
- Check component state and props
- Monitor Vuex mutations

## Git Workflow

### Branch Naming
```bash
feature/add-multiple-choice
fix/submission-timeout
refactor/clean-views
```

### Commit Messages
```bash
# Format: type: description

feat: add multiple choice problem type
fix: resolve submission timeout issue
refactor: migrate views to service pattern
docs: update API documentation
test: add service layer tests
```

### Pre-Commit Checklist
- [ ] Tests pass: `pytest`
- [ ] Linting passes: `npm run lint`
- [ ] Migrations created if needed
- [ ] Documentation updated
- [ ] Following STANDARDS.md
- [ ] NO direct model queries in views (Service Layer ENFORCED)
- [ ] All business logic in service layer

## Environment Setup

### Settings Module Structure
The project uses a modular settings architecture:
```
purplex/settings/
├── __init__.py     # Auto-selects based on PURPLEX_ENV
├── base.py         # Shared settings
├── development.py  # Development overrides (mock Firebase)
└── production.py   # Production settings (real Firebase)

purplex/config/
└── environment.py  # Environment detection and configuration
```

The correct settings module is automatically loaded based on the `PURPLEX_ENV` environment variable.

### Required Environment Variables
```bash
# .env.development file (for development)
PURPLEX_ENV=development
DJANGO_SECRET_KEY=development-secret-key-do-not-use-in-production
DATABASE_URL=postgresql://purplex_user:devpass@localhost:5432/purplex_dev
OPENAI_API_KEY=your-openai-key-here
GPT_MODEL=gpt-4o-mini
REDIS_HOST=localhost
REDIS_PORT=6379

# .env.production file (for production)
PURPLEX_ENV=production
DJANGO_SECRET_KEY=<generated-production-key>
DATABASE_URL=<production-database-url>
OPENAI_API_KEY=<production-openai-key>
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json
REDIS_HOST=<production-redis-host>
REDIS_PORT=6379
```

### VS Code Recommended Extensions
```json
{
  "recommendations": [
    "ms-python.python",
    "Vue.volar",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode"
  ]
}
```

## Troubleshooting

### Common Issues

#### Redis Connection Error
```bash
# Check Redis is running
redis-cli ping

# Start Redis
redis-server
```

#### Celery Tasks Not Processing
```bash
# Check worker is running
celery -A purplex.celery_simple inspect active

# Check for errors in worker log
tail -f logs/celery_worker.log
```

#### Frontend Proxy Issues
```bash
# Ensure Django is running on :8000
# Check vite.config.ts proxy settings
```

#### Migration Conflicts
```bash
# Reset migrations (DEVELOPMENT ONLY)
python manage.py migrate problems_app zero
rm purplex/problems_app/migrations/0*.py
python manage.py makemigrations
python manage.py migrate
```

#### PostgreSQL Connection Issues
```bash
# Check PostgreSQL container is running
docker ps | grep postgres

# Restart PostgreSQL development container
docker restart purplex-postgres

# Check PostgreSQL logs
docker logs purplex-postgres
```

#### Authentication Issues
```bash
# Development uses mock Firebase (no external dependencies)
# Production uses real Firebase
# Check PURPLEX_ENV environment variable
echo $PURPLEX_ENV

# For production, ensure Firebase credentials exist
ls -la firebase-credentials.json

# Test authentication service directly
python manage.py shell
from purplex.users_app.services.authentication_service import AuthenticationService
from purplex.users_app.user_views import AuthStatusView, SSETokenView
# Test token verification (example)
# All auth views are now in user_views.py (class-based only)
```

## Performance Optimization

### Database Queries
```python
# Bad - N+1 query
problems = Problem.objects.all()
for problem in problems:
    print(problem.category.name)  # Extra query each time

# Good - Single query
problems = Problem.objects.select_related('category')
for problem in problems:
    print(problem.category.name)  # No extra query
```

### Celery Tasks
```python
# Bad - Passing full objects
process_submission.delay(submission)  # Serializes entire object

# Good - Pass IDs
process_submission.delay(submission.id)  # Just the ID
```

## Database Optimization

### Current Capacity & Target
- **Current**: 100-200 concurrent users
- **Target**: 2,000 university students
- **Usage Pattern**: Bursty during homework deadlines, not sustained high traffic

### Immediate Performance Fixes

#### 1. Fix Django Connection Settings
```python
# settings/production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # 10 minutes (was 0 or 60)
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

#### 2. Add Missing Database Indexes
```sql
-- Create migration for these critical indexes
CREATE INDEX CONCURRENTLY idx_userprogress_user
    ON problems_app_userprogress(user_id);

CREATE INDEX CONCURRENTLY idx_submission_lookup
    ON submissions_app_promptsubmission(user_id, problem_id, submitted_at DESC);

CREATE INDEX CONCURRENTLY idx_active_problems
    ON problems_app_problem(is_active, slug)
    WHERE is_active = true;
```

#### 3. Fix N+1 Queries
```python
# Before (N+1 problem)
problems = Problem.objects.filter(is_active=True)

# After (single query)
problems = Problem.objects.filter(is_active=True)\
    .select_related('created_by')\
    .prefetch_related('categories', 'test_cases', 'problem_sets')
```

### Optional Performance Improvements

#### Add Basic Caching
```python
# Use Django's cache framework with Redis
from django.core.cache import cache

def get_user_progress(user_id, problem_set_id):
    cache_key = f'progress_{user_id}_{problem_set_id}'
    progress = cache.get(cache_key)
    if not progress:
        progress = UserProgress.objects.filter(
            user_id=user_id,
            problem_set_id=problem_set_id
        ).select_related('problem')
        cache.set(cache_key, progress, 300)  # 5 minutes
    return progress
```

### Database Monitoring
```python
# Add to settings.py
LOGGING = {
    'handlers': {
        'slow_queries': {
            'class': 'logging.FileHandler',
            'filename': 'logs/slow_queries.log',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['slow_queries'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
        },
    },
}

# Monitor slow queries in PostgreSQL:
# SET log_min_duration_statement = 100;  -- Log queries over 100ms
```

### Performance Testing
```bash
# Simple local test
python manage.py test tests.test_database_performance

# Check current connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"

# Find slow queries
psql -c "SELECT query, mean_exec_time FROM pg_stat_statements
         WHERE mean_exec_time > 50 ORDER BY mean_exec_time DESC LIMIT 10"
```

**Expected Results**: < 200ms for 95% of requests, easily handle 2,000 students

## Frontend Logging

Purplex uses a three-layer logging architecture to maintain clean separation between developer logging, Vue component integration, and user notifications.

### Architecture

#### Three Logging Utilities

1. **`utils/logger.ts`** - Core logging engine
   - Framework-agnostic, can be used anywhere
   - Handles log levels, formatting, and buffering
   - Environment-aware (dev vs production)

2. **`composables/useLogger.ts`** - Vue component integration
   - Auto-detects component names
   - Provides reactive logger instance
   - Component-specific convenience methods

3. **`composables/useNotification.ts`** - User notifications
   - Shows visual feedback to users
   - NOT for developer logging
   - Toast/popup messages with different durations

### Usage Patterns

#### Vue Components
```typescript
<script setup lang="ts">
import { useLogger } from '@/composables/useLogger';
import { useNotification } from '@/composables/useNotification';

const logger = useLogger();  // Auto-detects component name
const { notify } = useNotification();

// Basic logging
logger.debug('Component initialized');
logger.info('User action completed');
logger.warn('Deprecated feature used');
logger.error('Component error', error);

// Convenience methods
logger.logApiError('/api/users', error);
logger.logAsyncError('loadUserData', error);
logger.logUserAction('clicked-submit', { formData });
logger.logStateChange(oldState, newState);

// User notifications (separate from logging)
notify.success('Profile updated successfully');
notify.error('Failed to save. Please try again.');
</script>
```

#### Services and Utilities
```typescript
// services/auth.service.ts
import { log } from '@/utils/logger';

class AuthService {
  async validateToken(): Promise<AuthResponse> {
    try {
      const response = await axios.post(API_URL, data);
      log.info('Token validated successfully');
      return response.data;
    } catch (error) {
      log.error('Token validation error', error);
      throw error;
    }
  }
}
```

#### Combined Pattern: Log + Notify
```typescript
async function saveData() {
  try {
    await api.saveUserData(formData);
    logger.info('User data saved successfully');
    notify.success('Your changes have been saved');
  } catch (error) {
    // Log full error for developers
    logger.error('Failed to save user data', error);

    // Show user-friendly message
    notify.error('Unable to save your changes. Please try again.');
  }
}
```

### Best Practices

- **DEBUG**: Detailed information for debugging (dev only)
- **INFO**: General informational messages
- **WARN**: Warning messages for potentially problematic situations
- **ERROR**: Error messages for failures

Always include relevant context with logs and distinguish between what developers need to see vs. what users should see.

## UI/UX Consistency

This section documents the established design system, patterns, and conventions used throughout the Purplex frontend.

### CSS Architecture

The project uses a **CSS Variables-based design system** defined in `App.vue` that provides consistent theming across all components.

#### Color System
```css
/* Primary Brand Colors */
--color-primary: #800080;
--color-primary-hover: #9b009b;
--color-primary-gradient-start: #667eea;
--color-primary-gradient-end: #764ba2;

/* Background Hierarchy */
--color-bg-main: #242424;          /* Main app background */
--color-bg-dark: #1a1a1a;          /* Darker sections */
--color-bg-panel: #1e1e1e;         /* Card/panel backgrounds */
--color-bg-header: #191919;        /* Header backgrounds */
--color-bg-hover: #2a2a2a;         /* Hover states */

/* Text Hierarchy */
--color-text-primary: #ffffff;     /* Main text */
--color-text-secondary: #e0e0e0;   /* Secondary text */
--color-text-muted: #999;          /* Muted/disabled text */

/* Status Colors */
--color-success: #4CAF50;
--color-warning: #FFC107;
--color-error: #dc3545;
--color-info: #2196F3;
```

#### Spacing System
```css
--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 12px;
--spacing-base: 15px;
--spacing-lg: 20px;
--spacing-xl: 30px;
--spacing-xxl: 50px;
```

### Component Styling Patterns

1. **Scoped Styles**: All Vue components use `<style scoped>` to ensure styles don't leak globally
2. **Dark Theme Only**: The application exclusively uses a dark theme
3. **Base Element Styling**: Buttons inherit consistent base styles from `style.css`
4. **Component Structure**: Follow semantic HTML with TypeScript by default

### Interactive Elements & Animations

#### Common Hover Effects
- **Buttons**: Transform with `translateY(-1px)` and shadow increase
- **Cards/Panels**: Subtle shadow increase and border color highlight
- **Navigation Items**: Color transitions and scale transformations

#### Animation Patterns
- **Loading**: Bouncing dots and spinning indicators
- **Modals**: Fade in/out for overlays, slide up/down for content
- **Notifications**: Slide in from right, fade out on dismissal

### Best Practices

1. **Always use CSS variables** for colors, spacing, and shadows
2. **Maintain dark theme consistency** - no light mode variations
3. **Use semantic class names** that describe purpose, not appearance
4. **Keep animations subtle** - prioritize usability over flashiness
5. **Test responsive behavior** at all breakpoints
6. **Ensure accessibility** in all new components
7. **Follow existing patterns** when creating new components

## Field Naming Standards

This section standardizes field naming across models, serializers, and view annotations while ensuring schema consistency throughout the Django backend.

### Naming Rules

#### 1. Count Fields
- **Model properties**: Always plural + `_count` (e.g., `problems_count`, `test_cases_count`)
- **View annotations**: Must match serializer field names exactly
- **Serializer fields**: Use `ReadOnlyField()` referencing model property or annotation

#### 2. Foreign Key References
- **Related object data**: Use nested serializer (e.g., `categories`, `problem_sets`)
- **Write-only IDs**: Use `_ids` suffix (e.g., `category_ids`, `problem_set_ids`)
- **Display names**: Use `_name` suffix (e.g., `created_by_name`, `instructor_name`)

#### 3. Status and State Fields
- **Boolean states**: Use `is_` prefix (e.g., `is_active`, `is_completed`, `is_public`)
- **Enum states**: Use simple noun (e.g., `status`, `difficulty`, `hint_type`)
- **Status Values**: Backend uses underscored format (`not_started`, `in_progress`, `completed`)

#### 4. Time Fields
- **Creation**: `created_at`
- **Updates**: `updated_at`
- **Completion**: `completed_at`
- **Activity**: `last_attempt`, `first_attempt`, `last_activity`
- **Deletion**: `deleted_at`

#### 5. Aggregate Fields
- **Counts**: `*_count` (plural noun + count)
- **Averages**: `average_*` (e.g., `average_score`)
- **Totals**: `total_*` (e.g., `total_problems`, `total_time_spent`)
- **Percentages**: `*_percentage` (e.g., `completion_percentage`)

### Schema Validation Guidelines

#### Model-View Consistency
- Ensure Django ORM queries reference fields that actually exist on target models
- Cross-reference field usage in views against model definitions
- Validate foreign key relationships use correct field names

#### Field Naming Standards Enforcement
- All count fields should follow `{plural_noun}_count` pattern
- Boolean fields must use `is_` prefix for clarity
- Time fields should follow standard conventions
- Foreign key references should use appropriate suffixes

#### Status Naming Consistency
- **Backend (Django)**: Uses underscored format for status values (`not_started`, `in_progress`, `completed`)
- **Frontend (Vue/CSS)**: Uses underscored format for both data values and CSS classes
- **Status**: ✅ Fully consistent across the entire codebase

## Deployment Checklist

### Before Deploying
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Run `python manage.py collectstatic`
- [ ] Run `npm run build` in client/
- [ ] Update environment variables
- [ ] Run migrations on production DB
- [ ] Test with production settings locally

### Production Commands
```bash
# Using Docker
docker-compose -f docker-compose.production.yml up -d

# Manual deployment
gunicorn purplex.wsgi:application
celery -A purplex.celery_simple worker -l info
```
