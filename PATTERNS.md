# Implementation Patterns

Copy these patterns exactly when implementing new features. All examples are from the actual Purplex codebase.

## Table of Contents
1. [API Endpoint Pattern](#api-endpoint-pattern)
2. [Service Layer Pattern](#service-layer-pattern)
3. [Celery Task Pattern](#celery-task-pattern)
4. [Vue Component Pattern](#vue-component-pattern)
5. [Model Pattern](#model-pattern)
6. [Authentication Pattern](#authentication-pattern)
7. [Frontend Service Pattern](#frontend-service-pattern)

## API Endpoint Pattern

### Basic Admin View Pattern

```python
# From: purplex/problems_app/views/admin_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction

class AdminProblemListView(APIView):
    """Admin view for listing and creating problems."""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        # Optimize queries with select_related/prefetch_related
        problems = Problem.objects.all().select_related('created_by').prefetch_related('categories', 'test_cases', 'problem_sets')
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
        problem = get_object_or_404(Problem, slug=slug)
        serializer = AdminProblemSerializer(problem)
        return Response(serializer.data)
    
    def put(self, request, slug):
        problem = get_object_or_404(Problem, slug=slug)
        
        # Use service layer to prepare data
        data, problem_sets_slugs = AdminProblemService.prepare_problem_data(request.data)
        
        serializer = AdminProblemSerializer(problem, data=data, partial=True)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem = serializer.save()
                    
                    # Only update problem sets if explicitly provided
                    if 'problem_sets' in request.data:
                        problem_sets = ProblemSet.objects.filter(slug__in=problem_sets_slugs)
                        problem.problem_sets.set(problem_sets)
                    
                    return Response(AdminProblemSerializer(problem).data)
            except Exception as e:
                logger.error(f"Failed to update problem {slug}: {str(e)}")
                return Response({
                    'error': 'Failed to update problem. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### SSE Streaming Pattern

```python
# From: purplex/problems_app/views/sse_clean.py
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

## Service Layer Pattern

### Student Service Pattern

```python
# From: purplex/problems_app/services/student_service.py
import logging
from typing import List, Optional
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

class StudentService:
    """Handle all student-related business logic."""
    
    @staticmethod
    def get_active_problems(user=None) -> QuerySet:
        """Get all active problems visible to students."""
        return Problem.objects.filter(is_active=True).select_related(
            'created_by'
        ).prefetch_related(
            'categories',
            'test_cases',
            'problem_sets'
        ).only(
            'slug', 'title', 'description', 'difficulty', 'problem_type', 
            'function_name', 'tags', 'is_active', 'created_at', 'created_by_id'
        )
    
    @staticmethod
    def get_problem_detail(slug: str) -> Problem:
        """Get detailed problem information for students."""
        return get_object_or_404(Problem, slug=slug, is_active=True)
    
    @staticmethod
    def get_visible_test_cases(problem: Problem) -> QuerySet:
        """Get only non-hidden test cases for a problem."""
        return problem.test_cases.filter(is_hidden=False)
    
    @staticmethod
    def get_problem_set_problems(problem_set: ProblemSet, user=None) -> List[dict]:
        """Get ordered problems for a problem set."""
        # Get problems through membership table to preserve order
        memberships = problem_set.problemsetmembership_set.select_related(
            'problem'
        ).prefetch_related(
            'problem__categories',
            'problem__test_cases'
        ).order_by('order')
        
        problems_data = []
        for membership in memberships:
            problem = membership.problem
            if problem.is_active:
                problem_data = {
                    'slug': problem.slug,
                    'title': problem.title,
                    'description': problem.description,
                    'difficulty': problem.difficulty,
                    'problem_type': problem.problem_type,
                    'segmentation_enabled': problem.segmentation_enabled,
                    'reference_solution': problem.reference_solution,
                    'order': membership.order,
                    'categories': [cat.name for cat in problem.categories.all()],
                    'test_case_count': problem.test_cases.count(),
                    'visible_test_case_count': problem.test_cases.filter(is_hidden=False).count()
                }
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
            course = get_object_or_404(Course, course_id=course_id)
        
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

### Options API Component Pattern

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

### Composable Pattern

```typescript
// From: purplex/client/src/composables/useSSE.ts
import { ref, onUnmounted, Ref } from 'vue';
import { firebaseAuth } from '../firebaseConfig';
import { getIdToken } from 'firebase/auth';

export interface SSEOptions {
  onProgress?: (progress: { current: number; total: number; description: string }) => void;
  onError?: (error: any) => void;
  onTimeout?: () => void;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

export interface TaskResult {
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'retrying';
  result?: any;
  error?: string;
  progress?: {
    current: number;
    total: number;
    description: string;
  };
}

export function useSSE() {
  const isConnected = ref(false);
  const currentStatus = ref<TaskResult | null>(null);
  const error = ref<string | null>(null);
  
  let eventSource: EventSource | null = null;
  let reconnectCount = 0;
  let reconnectTimer: NodeJS.Timeout | null = null;

  const connectToTask = async (
    taskId: string,
    onComplete: (result: TaskResult) => void,
    options: SSEOptions = {}
  ) => {
    const {
      onProgress,
      onError,
      onTimeout,
      reconnectAttempts = 3,
      reconnectDelay = 1000
    } = options;

    try {
      // Get Firebase auth token
      const currentUser = firebaseAuth.currentUser;
      if (!currentUser) {
        throw new Error('User not authenticated');
      }
      
      const token = await getIdToken(currentUser);
      const url = `/api/sse/task/${taskId}/?token=${encodeURIComponent(token)}`;
      
      eventSource = new EventSource(url);
      
      eventSource.onopen = () => {
        isConnected.value = true;
        reconnectCount = 0;
        error.value = null;
      };
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          currentStatus.value = data;
          
          if (data.type === 'update' && onProgress) {
            onProgress({
              current: data.progress * 100,
              total: 100,
              description: data.message
            });
          }
          
          if (data.type === 'completed') {
            onComplete(data);
            disconnect();
          }
          
          if (data.type === 'failed') {
            error.value = data.error;
            if (onError) onError(data.error);
            disconnect();
          }
        } catch (e) {
          console.error('Error parsing SSE data:', e);
        }
      };
      
      eventSource.onerror = () => {
        isConnected.value = false;
        if (reconnectCount < reconnectAttempts) {
          reconnectCount++;
          reconnectTimer = setTimeout(() => {
            connectToTask(taskId, onComplete, options);
          }, reconnectDelay);
        } else if (onError) {
          onError(new Error('Failed to connect after multiple attempts'));
        }
      };
      
    } catch (err) {
      error.value = err.message;
      if (onError) onError(err);
    }
  };

  const disconnect = () => {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    isConnected.value = false;
  };

  onUnmounted(() => {
    disconnect();
  });

  return {
    isConnected,
    currentStatus,
    error,
    connectToTask,
    disconnect
  };
}
```

## Model Pattern

### Core Model with Business Logic in Properties

```python
# From: purplex/problems_app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Problem(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    PROBLEM_TYPE_CHOICES = [
        ('eipl', 'Explain in Plain Language (EiPL)'),
        ('function_redefinition', 'Function Redefinition'),
    ]
    
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    problem_type = models.CharField(max_length=30, choices=PROBLEM_TYPE_CHOICES, default='eipl')
    title = models.CharField(max_length=200)
    description = models.TextField(help_text='Problem description in markdown format')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    categories = models.ManyToManyField(ProblemCategory, related_name='problems', blank=True)
    function_name = models.CharField(max_length=50, help_text='Name of the function students implement')
    function_signature = models.TextField(help_text='Function signature with parameter names and types')
    reference_solution = models.TextField(help_text='Reference implementation')
    memory_limit = models.PositiveIntegerField(default=128, help_text='Memory limit in MB')
    tags = models.JSONField(default=list, blank=True, help_text='Array of tag strings')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    
    # Configuration fields
    completion_threshold = models.IntegerField(default=100, help_text='Minimum score required for completion')
    completion_criteria = models.JSONField(default=dict, blank=True)
    segmentation_config = models.JSONField(default=dict, blank=True)
    max_attempts = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['difficulty', 'title']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.difficulty})"
    
    @property
    def segmentation_enabled(self):
        """Check if segmentation is enabled for this problem."""
        return bool(self.segmentation_config.get('enabled', False))
```

### Submission Model with Relationships

```python
# From: purplex/submissions_app/models.py
from django.db import models
from django.contrib.auth.models import User
from purplex.problems_app.models import Problem, ProblemSet, Course

class PromptSubmission(models.Model):
    # Core relationships - INCLUDING COURSE
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE, related_name='submissions')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='submissions', null=True, blank=True)
    
    # Submission data
    prompt = models.TextField()
    score = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True, null=True)
    
    # EiPL specific fields
    code_variations = models.JSONField(default=list, help_text="List of generated code variations")
    test_results = models.JSONField(default=list, help_text="Test results for each variation")
    passing_variations = models.IntegerField(default=0, help_text="Number of variations that passed all tests")
    total_variations = models.IntegerField(default=0, help_text="Total number of variations generated")
    
    # Performance tracking
    execution_time = models.FloatField(null=True, blank=True, help_text="Total execution time in seconds")
    time_spent = models.DurationField(null=True, blank=True, help_text="Time user spent on this attempt")

    class Meta:
        indexes = [
            models.Index(fields=['user', 'problem', 'course', '-submitted_at']),
            models.Index(fields=['user', 'problem_set', 'course', '-submitted_at']),
            models.Index(fields=['course', 'problem_set', 'problem', '-score']),
        ]
        ordering = ['-submitted_at']
    
    def __str__(self):
        course_context = f" ({self.course.course_id})" if self.course else ""
        return f"{self.user.username} - {self.problem_set.title}{course_context} - {self.problem.title} - {self.score}%"
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

## Frontend Service Pattern

### TypeScript Service with Error Handling

```typescript
// From: purplex/client/src/services/problemService.ts
import axios, { AxiosResponse } from 'axios';
import {
  APIError,
  ProblemDetailed,
  ProblemCreateRequest,
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

  async testProblem(slug: string, data: TestProblemRequest): Promise<TestExecutionResult> {
    try {
      const response: AxiosResponse<TestExecutionResult> = await axios.post(
        `${this.baseURL}/${slug}/test/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to test problem');
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