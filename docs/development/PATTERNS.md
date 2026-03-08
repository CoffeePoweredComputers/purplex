# Implementation Patterns

Copy these patterns exactly when implementing new features. All examples are from the actual Purplex codebase.

## Table of Contents
1. [API Endpoint Pattern](#api-endpoint-pattern)
2. [Service Layer Pattern](#service-layer-pattern)
3. [Repository Pattern](#repository-pattern) **NEW**
4. [Celery Task Pattern](#celery-task-pattern)
5. [Vue Component Pattern](#vue-component-pattern)
6. [Model Pattern](#model-pattern)
7. [Authentication Pattern](#authentication-pattern)
8. [Frontend Service Pattern](#frontend-service-pattern)

## API Endpoint Pattern

### Basic Admin View Pattern

```python
# From: purplex/problems_app/views/admin_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from ..services.admin_service import AdminProblemService

class AdminProblemListView(APIView):
    """Admin view for listing and creating problems."""
    permission_classes = [IsAdmin]

    def get(self, request):
        # Use service layer - NEVER query models directly
        problems = AdminProblemService.get_all_problems_optimized()
        serializer = AdminProblemSerializer(problems, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Use service layer to prepare data
        data, problem_set_slugs = AdminProblemService.prepare_problem_data(request.data)

        serializer = AdminProblemSerializer(data=data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem = serializer.save(created_by=request.user)

                    # Use service layer to handle relations
                    if problem_set_slugs:
                        AdminProblemService.create_problem_with_relations(
                            problem, problem_set_slugs
                        )

                    return Response(AdminProblemSerializer(problem).data, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Failed to create problem: {str(e)}")
                return Response({
                    'error': 'Failed to create problem. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminProblemDetailView(APIView):
    """Admin view for getting, updating, and deleting specific problems."""
    permission_classes = [IsAdmin]

    def get(self, request, slug):
        # Use service layer to get problem (supports polymorphic types)
        problem = AdminProblemService.get_problem_by_slug(slug)
        if not problem:
            return Response(
                {"error": f"Problem with slug {slug} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = AdminProblemSerializer(problem)
        return Response(serializer.data)

    def put(self, request, slug):
        problem = AdminProblemService.get_problem_by_slug(slug)
        if not problem:
            return Response(
                {"error": f"Problem with slug {slug} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Use service layer to prepare data
        data, problem_sets_slugs = AdminProblemService.prepare_problem_data(request.data)

        serializer = AdminProblemSerializer(problem, data=data, partial=True)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem = serializer.save()

                    # Only update problem sets if explicitly provided
                    if 'problem_sets' in request.data:
                        problem_sets = AdminProblemService.get_problem_sets_by_slugs(problem_sets_slugs)
                        AdminProblemService.update_problem_set_relations(problem, problem_sets)

                    return Response(AdminProblemSerializer(problem).data)
            except Exception as e:
                logger.error(f"Failed to update problem {slug}: {str(e)}")
                return Response({
                    'error': f'Failed to update problem: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### SSE Streaming Pattern

```python
# From: purplex/problems_app/views/sse.py
import json
import redis
from django.http import StreamingHttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

class CleanTaskSSEView(View):
    """Stream task status updates via Server-Sent Events."""

    @method_decorator(never_cache)
    def get(self, request, task_id):
        """Stream SSE events for a specific task."""
        # Handle authentication for SSE (EventSource cannot send custom headers)
        token = request.GET.get('token')
        user = None

        if token:
            try:
                decoded_token = auth.verify_id_token(token)
                firebase_uid = decoded_token['uid']
                user_profile = UserProfile.objects.get(firebase_uid=firebase_uid)
                user = user_profile.user
            except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError) as e:
                if not settings.DEBUG:
                    return HttpResponseForbidden('Invalid authentication token')

        # Create streaming response
        response = StreamingHttpResponse(
            self._event_stream(task_id),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive'
        response['Access-Control-Allow-Origin'] = '*'
        return response

    def _event_stream(self, task_id):
        """Generate SSE events."""
        redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        pubsub = redis_client.pubsub()
        channel = f'task:{task_id}'

        try:
            pubsub.subscribe(channel)

            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f"data: {message['data']}\n\n"

        except Exception as e:
            logger.error(f"SSE stream error: {e}")
        finally:
            pubsub.close()
```

## Service Layer Pattern (Services Use Repositories for Database Access)

### Student Service Pattern (Using Repository Layer)

```python
# From: purplex/problems_app/services/student_service.py
import logging
from typing import TYPE_CHECKING

from django.http import Http404

from ..repositories import (
    ProblemCategoryRepository,
    ProblemRepository,
    ProblemSetMembershipRepository,
    TestCaseRepository,
)

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from ..models import Problem, ProblemSet

logger = logging.getLogger(__name__)


class StudentService:
    """Handle all student-related business logic.

    CRITICAL RULES:
    - Services use REPOSITORIES for all database access
    - Views call services, services call repositories
    - Business logic and validation in services, not views or repositories
    """

    @staticmethod
    def get_active_problems(user=None) -> list["Problem"]:
        """Get all active problems visible to students."""
        return ProblemRepository.get_active_problems()

    @staticmethod
    def get_problem_detail(slug: str) -> "Problem":
        """Get detailed problem information for students."""
        problem = ProblemRepository.get_problem_by_slug(slug)
        if not problem or not problem.is_active:
            raise Http404("Problem not found")
        return problem

    @staticmethod
    def get_visible_test_cases(problem: "Problem") -> "QuerySet":
        """Get only non-hidden test cases for a problem."""
        return TestCaseRepository.get_visible_test_cases(problem)

    @staticmethod
    def get_problem_set_problems(problem_set: "ProblemSet", user=None) -> list[dict]:
        """Get ordered problems for a problem set with handler configs.

        Uses repository layer for optimized queries.
        Enriches with handler-provided configs for frontend rendering.
        """
        from ..handlers import get_handler, is_registered

        # Get problems through membership repository (optimized queries)
        memberships_data = ProblemSetMembershipRepository.get_problem_set_memberships_with_categories(problem_set)

        problems_data = []
        for membership in memberships_data:
            problem = membership["problem"]
            problem_obj = membership["problem_obj"]

            if problem["is_active"]:
                problem_data = {
                    "slug": problem["slug"],
                    "title": problem["title"],
                    "difficulty": problem["difficulty"],
                    "problem_type": problem["problem_type"],
                    "order": membership["order"],
                    "categories": problem["categories"],
                    "test_cases": problem["test_cases"],
                }

                # Enrich with handler-provided configs
                problem_type = problem["problem_type"]
                if is_registered(problem_type):
                    handler = get_handler(problem_type)
                    config = handler.get_problem_config(problem_obj)
                    problem_data["display_config"] = config.get("display", {})
                    problem_data["input_config"] = config.get("input", {})

                problems_data.append(problem_data)

        return problems_data
```

### Hint Service Pattern

```python
# From: purplex/problems_app/services/hint_service.py
from typing import Dict, List, Optional, Any
from django.shortcuts import get_object_or_404
from django.core.cache import cache

class HintService:
    """Handle all hint-related business logic."""

    @staticmethod
    def get_hint_availability(
        user,
        problem_slug: str,
        course_id: Optional[str] = None,
        problem_set_slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check hint availability for a user on a specific problem."""
        problem = get_object_or_404(Problem, slug=problem_slug)

        # Get context objects
        problem_set = None
        course = None

        if problem_set_slug:
            problem_set = get_object_or_404(ProblemSet, slug=problem_set_slug)
        if course_id:
            # Use CourseService for course operations
            from .course_service import CourseService
            course = CourseService.get_course_by_id(course_id)

        # Get user progress with context
        try:
            if problem_set:
                progress = UserProgress.objects.get(
                    user=user,
                    problem=problem,
                    problem_set=problem_set,
                    course=course
                )
            else:
                progress = UserProgress.objects.get(user=user, problem=problem)
            attempts = progress.attempts
        except UserProgress.DoesNotExist:
            attempts = 0

        # Get enabled hints
        hints = ProblemHint.objects.filter(
            problem=problem,
            is_enabled=True
        ).values('id', 'hint_type', 'min_attempts')

        # Build availability response
        availability = {
            'problem_slug': problem_slug,
            'user_attempts': attempts,
            'hints': []
        }

        for hint in hints:
            hint_info = {
                'id': hint['id'],
                'type': hint['hint_type'],
                'min_attempts': hint['min_attempts'],
                'available': attempts >= hint['min_attempts'],
                'attempts_needed': max(0, hint['min_attempts'] - attempts)
            }
            availability['hints'].append(hint_info)

        return availability

    @staticmethod
    def get_cached_hint_availability(user, problem_slug: str) -> Optional[Dict[str, Any]]:
        """Get cached hint availability or compute and cache it."""
        cache_key = f'hint_availability:{user.id}:{problem_slug}'
        availability = cache.get(cache_key)

        if availability is None:
            availability = HintService.get_hint_availability(user, problem_slug)
            cache.set(cache_key, availability, 300)  # Cache for 5 minutes

        return availability
```

## Repository Pattern

### Base Repository (Provides Common CRUD Operations)

```python
# From: purplex/problems_app/repositories/base_repository.py
from typing import Any, Generic, TypeVar
from django.core.paginator import Paginator
from django.db.models import Model, QuerySet

T = TypeVar("T", bound=Model)


class BaseRepository(Generic[T]):
    """
    Base repository with common database operations.

    IMPORTANT: All public methods return domain objects (Model instances) or
    Python data types (list, dict, etc), NEVER QuerySets.

    Services should NEVER import django.db.models or perform ORM operations.
    All database logic must be encapsulated in repositories.
    """

    model_class: type[T] | None = None

    @classmethod
    def get_by_id(cls, id: int) -> T | None:
        """Get a single record by primary key."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        try:
            return cls.model_class.objects.get(pk=id)
        except cls.model_class.DoesNotExist:
            return None

    @classmethod
    def get_all(cls) -> list[T]:
        """Get all records as a list."""
        return list(cls.model_class.objects.all())

    @classmethod
    def create(cls, **kwargs) -> T:
        """Create a new record."""
        return cls.model_class.objects.create(**kwargs)
```

### Domain-Specific Repository

```python
# From: purplex/problems_app/repositories/course_repository.py
from typing import Any
from django.contrib.auth.models import User
from django.db.models import Count, Q

from purplex.problems_app.models import Course, CourseEnrollment, CourseProblemSet
from .base_repository import BaseRepository


class CourseRepository(BaseRepository):
    """
    Repository for all Course-related database queries.

    RULES:
    - ONLY place for .objects queries for this model
    - NO business logic, only data access
    - Return model instances or Python data types (list, dict)
    - Used by services, NEVER by views directly
    """

    model_class = Course

    @classmethod
    def get_active_course(cls, course_id: str) -> Course | None:
        """Get an active, non-deleted course by course_id (case-insensitive)."""
        return Course.objects.filter(
            course_id__iexact=course_id,
            is_active=True,
            is_deleted=False
        ).first()

    @classmethod
    def user_is_enrolled(cls, user: User, course: Course) -> bool:
        """Check if a user is enrolled in a specific course."""
        return CourseEnrollment.objects.filter(
            user=user,
            course=course,
            is_active=True
        ).exists()

    @classmethod
    def get_all_courses_with_stats(cls):
        """Get all courses with statistics for admin view."""
        return (
            Course.objects.select_related("instructor")
            .annotate(
                problem_sets_count=Count("problem_sets"),
                enrolled_students_count=Count("enrollments", filter=Q(enrollments__is_active=True)),
            )
            .order_by("-created_at")
        )
```

### Service Using Repository (CORRECT PATTERN)

```python
# From: purplex/problems_app/services/course_service.py
from ..repositories import CourseRepository

class CourseService:
    """Service using repository for data access."""

    @staticmethod
    def validate_course_enrollment(user, course_id: str) -> Dict[str, Any]:
        """
        Business logic using repository for data.
        Note: NO direct .objects queries here!
        """
        # Use repository for data access
        course = CourseRepository.get_active_course(course_id)

        if not course:
            return {
                'success': False,
                'error': 'Course not found'
            }

        # Use repository for enrollment check
        if not CourseRepository.user_is_enrolled(user, course):
            return {
                'success': False,
                'error': 'Not enrolled'
            }

        return {'success': True, 'course': course}
```

## Celery Task Pattern

### Single Orchestrator Task Pattern

```python
# From: purplex/problems_app/tasks/pipeline.py
from celery import shared_task
import json
import logging
import redis
from typing import Dict, List, Any, Optional
from django.db import transaction

logger = logging.getLogger(__name__)

def publish_progress(task_id: str, progress: float, message: str, extra_data: dict = None):
    """Publish a progress event to the Redis channel."""
    channel = f'task:{task_id}'
    event_data = {
        'type': 'update',
        'timestamp': time.time(),
        'status': 'processing',
        'progress': progress / 100.0,  # Convert to 0-1 range
        'message': message
    }
    if extra_data:
        event_data.update(extra_data)

    try:
        redis_client.publish(channel, json.dumps(event_data))
        logger.debug(f"Published progress {progress}%: {message}")
    except Exception as e:
        logger.error(f"Failed to publish progress event: {e}")

@shared_task(bind=True, name='pipeline.execute_eipl')
def execute_eipl_pipeline(
    self,
    problem_id: int,
    user_prompt: str,
    user_id: int,
    problem_set_id: Optional[int] = None,
    course_id: Optional[int] = None
) -> Dict[str, Any]:
    """Single orchestrator task for the entire EiPL pipeline."""
    task_id = self.request.id
    logger.info(f"Starting EiPL pipeline {task_id} for problem {problem_id}")

    try:
        # Initialize
        publish_progress(task_id, 0, "Starting pipeline...")

        # Step 1: Generate variations (0-20% progress)
        publish_progress(task_id, 5, "Generating code variations from your prompt...")
        variations = generate_variations_helper(problem_id, user_prompt)
        variation_count = len(variations)
        publish_progress(task_id, 20, f"Generated {variation_count} code variations")

        # Step 2: Test each variation (20-70% progress)
        test_results = []
        for i, code in enumerate(variations):
            test_progress = 20 + (50 * i / variation_count)
            publish_progress(task_id, test_progress, f"Testing variation {i+1} of {variation_count}...")

            result = test_variation_helper(code, problem_id, i)
            test_results.append(result)

        # Step 3: Calculate score (70-80% progress)
        publish_progress(task_id, 70, "Aggregating test results...")
        successful_variations = sum(1 for r in test_results if r.get('success', False))
        score = int((successful_variations / variation_count * 100) if variation_count > 0 else 0)
        publish_progress(task_id, 80, f"Score calculated: {score}%")

        # Step 4: Save submission (90-100% progress)
        publish_progress(task_id, 95, "Saving submission...")
        submission_result = save_submission_helper(
            user_id=user_id,
            problem_id=problem_id,
            problem_set_id=problem_set_id,
            course_id=course_id,
            user_prompt=user_prompt,
            variations=variations,
            test_results=test_results,
            segmentation=None
        )

        publish_progress(task_id, 100, f"Submission complete! Score: {score}%")
        publish_completion(task_id, submission_result)

        return submission_result

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Pipeline failed: {error_msg}", exc_info=True)
        publish_error(task_id, error_msg)
        raise
```

## Vue Component Pattern

**Note**: The codebase contains both Options API (legacy) and Composition API (preferred for new components) patterns. See STANDARDS.md for when to use each.

### Options API Pattern (Existing Components)

```vue
<!-- From: purplex/client/src/features/problems/ProblemSet.vue -->
<template>
  <div v-if="isLoading" class="loading-container">
    <div class="loading-message">Loading problem set...</div>
  </div>
  <div v-else-if="!problems || problems.length === 0" class="loading-container">
    <div class="loading-message">No problems found in this set.</div>
  </div>
  <div v-else class="problem-set-container">
    <div class="problem-navigation">
      <div class="problem-selector">
        <button class="nav-button" @click="prevProblem">
          <span class="arrow-left">‹</span>
        </button>
        <div class="problem-info">
          <div class="progress-summary">
            <span class="progress-stat completed">{{ completedCount }} completed</span>
            <span class="progress-stat in_progress">{{ inProgressCount }} in progress</span>
            <span class="progress-stat remaining">{{ remainingCount }} remaining</span>
          </div>
          <div class="problem-progress">
            <div
              v-for="(problem, index) in problems"
              :key="problem.slug"
              :class="['progress-bar',
                       { 'active': index === currentProblem },
                       { 'completed': getProblemStatus(problem.slug) === 'completed' }
              ]"
              @click="setProblem(index)"
            >
            </div>
          </div>
        </div>
        <button class="nav-button" @click="nextProblem">
          <span class="arrow-right">›</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'

export default {
  name: 'ProblemSet',
  data() {
    return {
      isLoading: false,
      currentProblem: 0,
      problems: []
    }
  },
  computed: {
    ...mapState('progress', ['progressData']),
    completedCount() {
      return this.problems.filter(p => this.getProblemStatus(p.slug) === 'completed').length
    },
    inProgressCount() {
      return this.problems.filter(p => this.getProblemStatus(p.slug) === 'in_progress').length
    },
    remainingCount() {
      return this.problems.filter(p => this.getProblemStatus(p.slug) === 'not_started').length
    }
  },
  methods: {
    ...mapActions('progress', ['fetchProgress']),
    getProblemStatus(slug) {
      const progress = this.progressData[slug]
      if (!progress) return 'not_started'
      return progress.best_score >= 100 ? 'completed' :
             progress.attempts > 0 ? 'in_progress' : 'not_started'
    },
    prevProblem() {
      if (this.currentProblem > 0) {
        this.currentProblem--
      }
    },
    nextProblem() {
      if (this.currentProblem < this.problems.length - 1) {
        this.currentProblem++
      }
    }
  }
}
</script>
```

### Composition API Pattern (New Components - Preferred)

```vue
<!-- New implementation pattern for ProblemSet.vue using Composition API -->
<template>
  <div v-if="isLoading" class="loading-container">
    <div class="loading-message">Loading problem set...</div>
  </div>
  <div v-else-if="!problems || problems.length === 0" class="loading-container">
    <div class="loading-message">No problems found in this set.</div>
  </div>
  <div v-else class="problem-set-container">
    <div class="problem-navigation">
      <div class="problem-selector">
        <button class="nav-button" @click="prevProblem">
          <span class="arrow-left">‹</span>
        </button>
        <div class="problem-info">
          <div class="progress-summary">
            <span class="progress-stat completed">{{ completedCount }} completed</span>
            <span class="progress-stat in_progress">{{ inProgressCount }} in progress</span>
            <span class="progress-stat remaining">{{ remainingCount }} remaining</span>
          </div>
          <div class="problem-progress">
            <div
              v-for="(problem, index) in problems"
              :key="problem.slug"
              :class="['progress-bar',
                       { 'active': index === currentProblem },
                       { 'completed': getProblemStatus(problem.slug) === 'completed' }
              ]"
              @click="setProblem(index)"
            >
            </div>
          </div>
        </div>
        <button class="nav-button" @click="nextProblem">
          <span class="arrow-right">›</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useStore } from 'vuex'
import type { Problem } from '@/types'

// Props
interface Props {
  problemSetSlug?: string
}

const props = withDefaults(defineProps<Props>(), {
  problemSetSlug: ''
})

// Store
const store = useStore()

// Reactive state
const isLoading = ref(false)
const currentProblem = ref(0)
const problems = ref<Problem[]>([])

// Computed properties
const progressData = computed(() => store.state.progress.progressData)

const completedCount = computed(() =>
  problems.value.filter(p => getProblemStatus(p.slug) === 'completed').length
)

const inProgressCount = computed(() =>
  problems.value.filter(p => getProblemStatus(p.slug) === 'in_progress').length
)

const remainingCount = computed(() =>
  problems.value.filter(p => getProblemStatus(p.slug) === 'not_started').length
)

// Methods
const getProblemStatus = (slug: string): string => {
  const progress = progressData.value[slug]
  if (!progress) return 'not_started'
  return progress.best_score >= 100 ? 'completed' :
         progress.attempts > 0 ? 'in_progress' : 'not_started'
}

const prevProblem = (): void => {
  if (currentProblem.value > 0) {
    currentProblem.value--
  }
}

const nextProblem = (): void => {
  if (currentProblem.value < problems.value.length - 1) {
    currentProblem.value++
  }
}

const setProblem = (index: number): void => {
  currentProblem.value = index
}

// Actions
const fetchProgress = () => store.dispatch('progress/fetchProgress')
</script>
```

### Service Pattern (SSE)

```typescript
// From: purplex/client/src/services/sseService.ts
// Singleton service for SSE connections - caller manages cleanup via returned disconnect function

import { log } from '../utils/logger';
import { firebaseAuth } from '../firebaseConfig';
import type { UnifiedSubmissionResult } from '../types';

class SSEService {
  private completedTasks: Set<string> = new Set();

  /**
   * Unified submission SSE handler for all activity types.
   * Returns a disconnect function - caller must call it for cleanup.
   */
  connectToSubmission(
    requestId: string,
    onSuccess: (result: UnifiedSubmissionResult) => void,
    options: SSEOptions = {}
  ): Promise<() => void> {
    return this.connectToTask(
      requestId,
      (taskResult) => {
        if (taskResult.status === 'completed' && taskResult.result) {
          const unified = taskResult.result as UnifiedSubmissionResult;
          if (unified.submission_id) {
            onSuccess(unified);
          } else if (options.onError) {
            options.onError({ error: 'Submission failed' });
          }
        }
      },
      options
    );
  }
}

export const sseService = new SSEService();

// Usage in component:
const disconnect = await sseService.connectToSubmission(
  taskId,
  (result) => {
    // Handle unified result - dispatch on result.problem_type
    if (result.problem_type === 'mcq') {
      // MCQ handling
    } else {
      // EiPL handling
    }
  },
  { onError: (err) => console.error(err) }
);

// Important: Call disconnect() on component unmount or when done
```

## Model Pattern

### Polymorphic Base Model Pattern

The codebase uses django-polymorphic for problem types. Models are organized in a subdirectory.

```python
# From: purplex/problems_app/models/base.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from polymorphic.models import PolymorphicModel

from .category import ProblemCategory

class Problem(PolymorphicModel):
    """
    Polymorphic base class for all problem types.

    Problem.objects.all() returns correct subtypes automatically.

    Hierarchy:
    - Problem (this class)
      - StaticProblem (abstract) - no code execution
        - McqProblem
      - SpecProblem - has code specification fields
        - EiplProblem - NL -> LLM -> code -> test
        - PromptProblem - image-based variant of EiPL
        - ProbeableCodeProblem
        - DebugFixProblem
      - (Future) CodeProblem - student code -> execute
    """

    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    # Identity
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="", help_text="Problem description in markdown format")

    # Classification
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="beginner")
    categories = models.ManyToManyField(ProblemCategory, related_name="problems", blank=True)
    tags = models.JSONField(default=list, blank=True, help_text="Array of tag strings")

    # Status
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    # Completion configuration
    completion_threshold = models.IntegerField(default=100, help_text="Minimum score required for completion")
    max_attempts = models.IntegerField(null=True, blank=True)

    class Meta:
        app_label = "problems_app"
        ordering = ["difficulty", "title"]

    @property
    def polymorphic_type(self) -> str:
        """Return the problem type identifier for handler lookup."""
        raise NotImplementedError("Subclasses must define polymorphic_type")

    @property
    def problem_type(self) -> str:
        """Alias for polymorphic_type for backward compatibility."""
        return self.polymorphic_type

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Problem.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.difficulty})"
```

### Unified Submission Model

```python
# From: purplex/submissions/models.py
import uuid
from django.db import models
from django.contrib.auth.models import User


class Submission(models.Model):
    """
    Unified submission model for all submission types.
    Single source of truth for student work.
    """

    # Unique identifier for external references
    submission_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)

    # Core relationships
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="submissions")
    problem = models.ForeignKey("problems_app.Problem", on_delete=models.PROTECT, related_name="submissions")
    problem_set = models.ForeignKey("problems_app.ProblemSet", on_delete=models.PROTECT, related_name="submissions")
    course = models.ForeignKey("problems_app.Course", on_delete=models.PROTECT, null=True, blank=True, related_name="submissions")

    # Submission metadata
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    submission_type = models.CharField(
        max_length=20,
        choices=[
            ("eipl", "Explain in Plain Language"),
            ("mcq", "Multiple Choice Question"),
            ("prompt", "Prompt (Image-based)"),
            ("refute", "Refute (Counterexample)"),
            ("debug_fix", "Debug Fix"),
            ("probeable_code", "Probeable Code"),
            ("probeable_spec", "Probeable Spec"),
        ],
        db_index=True,
    )

    # Submission content
    raw_input = models.TextField(help_text="Original user input (code or natural language)")
    processed_code = models.TextField(help_text="Final code that was executed", blank=True)

    # Results
    score = models.IntegerField(default=0, db_index=True, help_text="Overall score (0-100)")
    passed_all_tests = models.BooleanField(default=False, db_index=True)
    is_correct = models.BooleanField(default=False, help_text="Whether the submission passes all test cases")
    completion_status = models.CharField(
        max_length=20,
        choices=[("incomplete", "Incomplete"), ("partial", "Partial Success"), ("complete", "Complete Success")],
        default="incomplete",
    )

    # Async processing - unique constraint prevents duplicate submissions on task retry
    celery_task_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "problem", "course", "-submitted_at"]),
            models.Index(fields=["user", "problem_set", "course", "-submitted_at"]),
            models.Index(fields=["course", "problem_set", "-score"]),
        ]
        ordering = ["-submitted_at"]

    def __str__(self):
        course_context = f" ({self.course.course_id})" if self.course else ""
        return f"{self.user.username} - {self.problem.title}{course_context} - {self.score}%"
```

## Authentication Pattern

### Service-Layer Authentication

```python
# From: purplex/users_app/authentication.py
from typing import Optional, Tuple, Any
from rest_framework import authentication, exceptions
from django.contrib.auth.models import User
from .services.authentication_service import AuthenticationService
import logging

logger = logging.getLogger(__name__)

class PurplexAuthentication(authentication.BaseAuthentication):
    """
    Single authentication class for ALL endpoints.

    Handles both header and query parameter tokens (for SSE).
    All Firebase logic is delegated to AuthenticationService.
    """

    def authenticate(self, request) -> Optional[Tuple[User, Any]]:
        """
        Authenticate the request using Firebase tokens.

        Tries header first, then query parameter (for SSE).
        """
        # Try header first
        token = self._extract_header_token(request)

        # Try query parameter if no header (for SSE)
        if not token:
            token = self._extract_query_token(request)

        # Try service account if no user token
        if not token:
            service_user = self._check_service_account(request)
            if service_user:
                return (service_user, None)

        # No authentication attempted
        if not token:
            return None

        # Authenticate the token
        try:
            user, auth_data = AuthenticationService.authenticate_token(token)
            return (user, auth_data)
        except ValueError as e:
            logger.warning(f"Authentication failed: {e}")
            raise exceptions.AuthenticationFailed(str(e))
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            raise exceptions.AuthenticationFailed('Authentication failed')

    def _extract_header_token(self, request) -> Optional[str]:
        """Extract token from Authorization header."""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            return None

        # Support both 'Bearer' and 'Token' prefixes
        parts = auth_header.split()
        if len(parts) != 2:
            return None

        auth_type, token = parts
        if auth_type.lower() in ['bearer', 'token']:
            return token

        return None

    def _extract_query_token(self, request) -> Optional[str]:
        """Extract token from query parameter (for SSE/EventSource)."""
        return request.GET.get('token')

    def _check_service_account(self, request) -> Optional[User]:
        """Check for service account authentication."""
        service_key = request.META.get('HTTP_X_SERVICE_KEY', '')
        if service_key:
            return AuthenticationService.verify_service_account(service_key)
        return None
```

### Authentication Service Pattern

```python
# From: purplex/users_app/services/authentication_service.py
from typing import Optional, Tuple, Dict, Any
from django.contrib.auth.models import User
from django.db import transaction
from config.environment import config
from purplex.users_app.models import UserProfile
import logging

logger = logging.getLogger(__name__)

class AuthenticationService:
    """
    Central authentication service - single source of truth.

    This service handles:
    - Token verification (Firebase or mock)
    - User creation and updates
    - Profile management
    - All authentication-related logic
    """

    # Cache for Firebase initialization
    _firebase_initialized = False
    _firebase_auth = None

    @classmethod
    def authenticate_token(cls, token: str) -> Tuple[User, Dict[str, Any]]:
        """
        Authenticate a Firebase token and return user.

        This is the ONLY method that verifies Firebase tokens.
        Handles both mock (dev) and real (prod) Firebase.
        """
        if not token:
            raise ValueError("No token provided")

        # Get Firebase auth module (mock or real)
        auth_module = cls._initialize_firebase()

        try:
            # Verify the token (same interface for mock and real)
            decoded_token = auth_module.verify_id_token(token)

            # Extract user information
            firebase_uid = decoded_token['uid']
            email = decoded_token.get('email', '')
            display_name = decoded_token.get('name', '')

            # Get or create the user
            user = cls.get_or_create_user(firebase_uid, email, display_name)

            return (user, decoded_token)

        except Exception as e:
            # Handle different exception types
            error_name = e.__class__.__name__
            if 'InvalidIdTokenError' in error_name:
                raise ValueError(f"Invalid authentication token: {str(e)}")
            elif 'ExpiredIdTokenError' in error_name:
                raise ValueError("Authentication token has expired")
            else:
                logger.error(f"Authentication error: {e}")
                raise ValueError(f"Authentication failed: {str(e)}")

    @classmethod
    @transaction.atomic
    def get_or_create_user(cls, firebase_uid: str, email: str, display_name: str) -> User:
        """
        Get existing user or create new one.

        Uses database transaction to prevent race conditions.
        """
        # Try to get existing user profile
        try:
            user_profile = UserProfile.objects.select_for_update().get(firebase_uid=firebase_uid)
            user = user_profile.user

            # Update user info if changed
            cls._update_user_if_needed(user, email, display_name)

            return user

        except UserProfile.DoesNotExist:
            # Create new user
            user = cls._create_django_user(firebase_uid, email, display_name)

            # Create user profile
            user_profile = UserProfile.objects.create(
                user=user,
                firebase_uid=firebase_uid,
                role='user'
            )

            # Apply test user permissions in development
            if config.is_development and email:
                cls._apply_test_user_permissions(user, user_profile, email)

            logger.info(f"Created new user: {user.username} (Firebase UID: {firebase_uid})")
            return user
```

### Authentication View Pattern

```python
# From: purplex/users_app/user_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .permissions import IsAuthenticated
from .services.authentication_service import AuthenticationService
from .services.rate_limit_service import RateLimitService
import logging

logger = logging.getLogger(__name__)

class SSETokenView(APIView):
    """
    View for exchanging Firebase tokens for short-lived SSE session tokens.

    This demonstrates the consolidated authentication pattern:
    - Class-based view (no function-based views)
    - Thin controller delegating to services
    - Multiple HTTP methods in one class
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a new SSE session token"""
        try:
            user = request.user

            # Delegate to service for rate limiting
            if not RateLimitService.check_sse_token_rate_limit(user.id):
                logger.warning(f"SSE token rate limit exceeded for user {user.username}")
                return Response({
                    'error': 'Rate limit exceeded. Please wait before requesting another token.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # Delegate to service for token creation
            session_token = AuthenticationService.create_sse_session(user)

            return Response({
                'sse_token': session_token,
                'expires_in': 300  # 5 minutes
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to create SSE token: {e}")
            return Response({
                'error': 'Failed to create session token'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        """Revoke an SSE session token"""
        try:
            sse_token = request.data.get('sse_token')

            if not sse_token:
                return Response({
                    'error': 'SSE token required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Delegate to service for token revocation
            revoked = AuthenticationService.revoke_sse_session(sse_token)

            if revoked:
                return Response({
                    'message': 'Session revoked successfully'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': 'Session not found or already expired'
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Failed to revoke SSE token: {e}")
            return Response({
                'error': 'Failed to revoke session'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

## Frontend Service Pattern

### TypeScript Service with Error Handling

```typescript
// From: purplex/client/src/services/problemService.ts
import axios, { AxiosResponse } from 'axios';
import {
  APIError,
  ProblemDetailed,
  ProblemCreateRequest,
  TestProblemRequest,
  TestExecutionResult
} from '../types';

class ProblemServiceImpl {
  private readonly baseURL = '/api/admin/problems';

  async loadProblem(slug: string): Promise<ProblemDetailed> {
    try {
      const response: AxiosResponse<ProblemDetailed> = await axios.get(
        `${this.baseURL}/${slug}/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to load problem: ${slug}`);
    }
  }

  async createProblem(data: ProblemCreateRequest): Promise<ProblemDetailed> {
    try {
      // Validate data before sending
      this._validateProblemData(data);

      const response: AxiosResponse<ProblemDetailed> = await axios.post(
        this.baseURL + '/',
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to create problem');
    }
  }

  async testProblem(data: TestProblemRequest): Promise<TestExecutionResult> {
    try {
      const response: AxiosResponse<TestExecutionResult> = await axios.post(
        '/api/admin/test-problem/',
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to test problem solution');
    }
  }

  private _validateProblemData(data: ProblemCreateRequest): void {
    if (!data.title?.trim()) {
      throw new Error('Problem title is required');
    }
    if (!data.function_name?.trim()) {
      throw new Error('Function name is required');
    }
    if (!data.test_cases || data.test_cases.length === 0) {
      throw new Error('At least one test case is required');
    }
  }

  private _handleError(error: any, context: string): APIError {
    if (error.response?.data?.error) {
      return new APIError(error.response.data.error, error.response.status);
    }
    return new APIError(`${context}: ${error.message}`, error.response?.status || 500);
  }
}

export const problemService = new ProblemServiceImpl();
```
