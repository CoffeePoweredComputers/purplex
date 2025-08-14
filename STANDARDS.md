# Coding Standards for Purplex

**CRITICAL**: All code must follow these standards. No exceptions for new code.

## Quick Reference Checklist
Before writing ANY code:
- [ ] Using clean pattern, not legacy?
- [ ] Business logic in service layer, not view?
- [ ] Following naming conventions below?
- [ ] Using existing patterns from similar code?

## Python Standards (Django Backend)

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
# views/example_view.py
class ProblemListView(APIView):
    """Thin controller - NO business logic here."""
    
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
```

### Service Pattern (MUST FOLLOW)
```python
# services.py or services/problem_service.py
class ProblemService:
    """All business logic goes here."""
    
    @staticmethod
    def get_filtered_problems(user, filters):
        # Complex logic here
        queryset = Problem.objects.select_related('category')
        
        if user.is_student:
            queryset = queryset.filter(is_published=True)
            
        # More business logic...
        return queryset
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

### Component Structure (Options API - Current Standard)
```vue
<!-- ProblemCard.vue -->
<template>
  <!-- Template here -->
</template>

<script>
// Current codebase uses Options API
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

### State Management Rules
```typescript
// Composables for feature-specific state (PREFERRED)
// composables/useProblemState.ts
export function useProblemState() {
  const problems = ref([])
  // Local to this feature
  return { problems }
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
# tasks/submission_tasks.py
@shared_task(name='submission.process')  # Namespaced
def process_submission(submission_id):
    """Task names use dot notation."""
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

### Using Clean Implementations
- Check for `_clean.py` variants when working with existing code
- Currently available: `sse_clean.py` for Server-Sent Events
- Prefer clean implementations when they exist

### Future Improvements
- [ ] Enhance test coverage for all services
- [ ] Add performance monitoring
- [ ] Implement comprehensive logging

## Enforcement

### Before Every PR/Commit
1. Run: `pytest tests/standards/` (when created)
2. Check: No new legacy patterns introduced
3. Verify: Business logic is in services, not views
4. Confirm: Naming conventions followed

### For Claude Code
**INSTRUCTION**: Always check this file before writing code. Look for existing clean implementations (files ending in `_clean.py`) before modifying legacy code. If uncertain, ask for clarification rather than guessing.