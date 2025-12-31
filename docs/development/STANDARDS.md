# Coding Standards for Purplex

**CRITICAL**: All code must follow these standards. No exceptions for new code.

## Quick Reference Checklist
Before writing ANY code:
- [ ] Using clean pattern, not legacy?
- [ ] Business logic in service layer, not view?
- [ ] Service using repository for data access?
- [ ] Following naming conventions below?
- [ ] Using existing patterns from similar code?
- [ ] NO direct model queries in views (ENFORCED)
- [ ] NO direct model queries in services (use repositories)

## Python Standards (Django Backend)

### View Architecture Rules
1. **ALL views MUST be class-based** - Use `APIView` or DRF generic views
2. **NO function-based views** - `@api_view` decorator is deprecated
3. **Consolidate related views** - Group auth views in `user_views.py`, problem views in `problem_views.py`
4. **Always specify permissions** - Every view must have `permission_classes`
5. **Views are thin controllers** - No business logic, only HTTP handling

### Naming Conventions
```python
# Classes: PascalCase
class UserProgressTracker:
    pass

# Functions/Methods: snake_case
def calculate_problem_score():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_SUBMISSION_ATTEMPTS = 5

# Private methods: leading underscore
def _internal_helper():
    pass

# Files: snake_case.py
user_progress_service.py  # ✓
UserProgressService.py    # ✗
```

### View Pattern (MUST FOLLOW)
```python
# views/example_view.py or user_views.py
from rest_framework.views import APIView
from rest_framework.response import Response

class ProblemListView(APIView):
    """
    REQUIRED: All views MUST be class-based using APIView.
    Thin controller - NO business logic here.
    """
    permission_classes = [IsAuthenticated]  # Always specify permissions

    def get(self, request):
        # 1. Parse request
        filters = request.query_params

        # 2. Call service
        problems = ProblemService.get_filtered_problems(
            user=request.user,
            filters=filters
        )

        # 3. Return response
        serializer = ProblemSerializer(problems, many=True)
        return Response(serializer.data)

# ❌ NEVER USE: Function-based views are deprecated
# @api_view(['GET'])  # Don't use this pattern
# def problem_list(request):
#     pass
```

### Service Pattern (ENFORCED)
```python
# services.py or services/problem_service.py
class ProblemService:
    """All business logic goes here - NO EXCEPTIONS.

    PATTERN:
    - Views NEVER access models directly (enforced)
    - Services use repositories for data access
    - Services contain ONLY business logic
    - Repositories handle ALL database queries
    """

    @staticmethod
    def get_filtered_problems(user, filters):
        # Use repository for all data access
        from ..repositories import ProblemRepository
        problems = ProblemRepository.get_active_problems()

        if user.is_student:
            # Business logic here - services filter/transform data
            problems = [p for p in problems if p.is_published]

        return problems

    @staticmethod
    def validate_course_enrollment(user, course_id):
        """Example: Course validation using repository (CORRECT)"""
        from ..repositories import CourseRepository

        course = CourseRepository.get_active_course(course_id)
        if not course:
            return {'success': False, 'error': 'Course not found'}

        if not CourseRepository.user_is_enrolled(user, course):
            return {'success': False, 'error': 'Not enrolled'}

        return {'success': True, 'course': course}
```

### Repository Pattern
```python
# repositories/course_repository.py
class CourseRepository(BaseRepository):
    """Handle ALL database queries for Course model.

    RULES:
    - Only place for .objects queries
    - No business logic, only data access
    - Return model instances or Python data types (list, dict)
    - Used by services, NEVER by views
    """

    @classmethod
    def get_active_course(cls, course_id: str):
        """Get active, non-deleted course."""
        return Course.objects.filter(
            course_id=course_id,
            is_active=True,
            is_deleted=False
        ).first()

    @classmethod
    def user_is_enrolled(cls, user, course):
        """Check enrollment status."""
        return CourseEnrollment.objects.filter(
            user=user,
            course=course,
            is_active=True
        ).exists()
```

### Model Pattern
```python
# models.py
class Problem(models.Model):
    """Only data definition and simple properties."""

    title = models.CharField(max_length=200)

    @property
    def is_active(self):
        """Simple property OK, complex logic goes in service."""
        return self.status == 'active'
```

## Vue.js Standards (Frontend)

### Component Naming
```vue
<!-- Components: PascalCase.vue -->
ProblemCard.vue       ✓
problem-card.vue      ✗
problemCard.vue       ✗
```

### Component Structure

#### For New Components (Preferred - Composition API)
```vue
<!-- ProblemCard.vue -->
<template>
  <!-- Template here -->
</template>

<script setup lang="ts">
// New components should use Composition API with <script setup>
import { ref, computed, onMounted } from 'vue'
import { useStore } from 'vuex'
import { useFeedbackState } from '@/composables/useFeedbackState'

interface Props {
  problemId: number
}

const props = defineProps<Props>()
const store = useStore()

// Local state using composables (preferred)
const { feedback, clear, set } = useFeedbackState()

// Global state access when needed
const progressData = computed(() => store.state.progress.progressData)
</script>
```

#### For Existing Components (Options API)
```vue
<!-- ProblemCard.vue -->
<template>
  <!-- Template here -->
</template>

<script>
// Existing codebase uses Options API - keep during maintenance
import { mapState, mapActions } from 'vuex'

export default {
  name: 'ProblemCard',
  props: {
    problemId: {
      type: Number,
      required: true
    }
  },
  data() {
    return {
      userCode: '',
      isSubmitting: false
    }
  },
  computed: {
    ...mapState('progress', ['progressData'])
  },
  methods: {
    ...mapActions('progress', ['fetchProgress']),
    async handleSubmit() {
      this.isSubmitting = true
      // Handle submission
      this.isSubmitting = false
    }
  }
}
</script>
```

### Component API Migration Strategy
- **New Features**: Always use Composition API with `<script setup>` for new components
- **Existing Components**: Most components now use Composition API; only 4 legacy Options API components remain (ProblemSet.vue, AddEditProblemSetModal.vue, HintButton.vue, Login.vue)
- **Logic Sharing**: Use composables (e.g., `useFeedbackState`, `useSubmissionTracking`, `useNotification`) or services (e.g., `sseService`) instead of mixins
- **Migration Timing**: Only migrate remaining Options API components during significant feature additions or bug fixes
- **TypeScript**: Strongly encouraged for new Composition API components

### State Management Rules
```typescript
// Composables for feature-specific state (PREFERRED)
// composables/useFeedbackState.ts
export function useFeedbackState() {
  const feedback = reactive<FeedbackState>(createInitialState())
  const clear = () => { /* reset state */ }
  const set = (data: FeedbackSetData) => { /* update state */ }
  return { feedback: readonly(feedback), clear, set }
}

// Vuex ONLY for true global state (user, auth, app-wide settings)
// store/modules/user.ts
```

## API Standards

### Endpoint Naming (REST Best Practices)
```
GET    /api/problems/           # List (plural, kebab-case)
POST   /api/problems/           # Create
GET    /api/problems/{id}/      # Retrieve
PUT    /api/problems/{id}/      # Update
DELETE /api/problems/{id}/      # Delete

# Nested resources
GET    /api/courses/{id}/problem-sets/    # Kebab-case
POST   /api/problems/{id}/submit-solution/ # Action endpoints
```

### Response Format
```json
// Success
{
  "success": true,
  "data": { ... },
  "message": "Optional success message"
}

// Error
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "User-friendly message",
    "details": { ... }
  }
}
```

## Celery Task Standards

### Task Naming
```python
# tasks/pipeline.py
@shared_task(bind=True, name="pipeline.execute_eipl")  # Namespaced with module prefix
def execute_eipl_pipeline(self, submission_id: str, **kwargs):
    """Task names use dot notation: module.action_name."""
    pass

# tasks/cleanup.py
@shared_task(name="cleanup.prune_orphaned_containers")
def prune_orphaned_containers():
    """Cleanup tasks follow same naming pattern."""
    pass
```

## Testing Standards

### Use Pytest Exclusively
```python
# tests/unit/test_problem_service.py
import pytest

class TestProblemService:
    """Group related tests in classes."""

    @pytest.fixture
    def sample_problem(self):
        """Use fixtures for test data."""
        return Problem.objects.create(...)

    def test_calculate_score_returns_percentage(self, sample_problem):
        """Descriptive test names."""
        score = ProblemService.calculate_score(sample_problem)
        assert 0 <= score <= 100
```

## Clean Code Patterns

### SSE (Server-Sent Events) Implementation
- Use `CleanTaskSSEView` and `CleanBatchSSEView` from `views/sse.py`
- These provide real-time task status updates via Redis pub/sub
- Views use Django's standard `View` class with custom authentication

### Future Improvements
- [ ] Enhance test coverage for all services
- [ ] Add performance monitoring
- [ ] Implement comprehensive logging

## Enforcement

### Before Every PR/Commit
1. Run: `pytest` to verify all tests pass
2. Run: `make lint` to check code style
3. Verify: Business logic is in services, not views
4. Confirm: Naming conventions followed
5. Check: No direct model access in views (use services/repositories)

### For Claude Code
**INSTRUCTION**: Always check this file before writing code. Follow the established patterns for views, services, and repositories. If uncertain, ask for clarification rather than guessing.
