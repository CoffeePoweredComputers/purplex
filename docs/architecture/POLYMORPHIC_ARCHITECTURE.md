# Purplex Architecture Overview (Post-Polymorphic Migration)

**Last Updated:** December 2024
**Status:** Current - Post migrations 0012-0022

This document provides a comprehensive architectural overview of the Purplex educational platform following the major polymorphic Django migration.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Polymorphic Model Architecture](#2-polymorphic-model-architecture)
3. [Activity Handler System](#3-activity-handler-system)
4. [Service Layer](#4-service-layer)
5. [Repository Pattern](#5-repository-pattern)
6. [Celery Task Architecture](#6-celery-task-architecture)
7. [Frontend Architecture](#7-frontend-architecture)
8. [Docker Sandbox Security](#8-docker-sandbox-security)
9. [Quality Assessment](#9-quality-assessment)
10. [Recommendations](#10-recommendations)

---

## 1. System Overview

### Tech Stack
- **Backend:** Django 5.0 + Django REST Framework + django-polymorphic
- **Frontend:** Vue 3 + TypeScript + Vite + Vuex 4
- **Database:** PostgreSQL 15
- **Task Queue:** Celery 5.x with Redis broker + gevent workers
- **Auth:** Firebase Authentication (mock in dev)
- **Code Execution:** Docker containers via Docker-in-Docker
- **AI:** OpenAI GPT-4 API

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     Vue 3 Frontend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐│
│  │   Vuex      │  │  Services   │  │ Activity Components  ││
│  │   Store     │  │   Layer     │  │ (Input/Feedback)     ││
│  └─────────────┘  └─────────────┘  └──────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                            │
                     REST API + SSE
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Django Backend                            │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐│
│  │   Views     │  │  Services   │  │  Activity Handlers   ││
│  │ (DRF Views) │  │   Layer     │  │ (7 problem types)    ││
│  └─────────────┘  └─────────────┘  └──────────────────────┘│
│                            │                                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   Repositories                          ││
│  │     (Data Access Layer - Returns Model Instances)       ││
│  └─────────────────────────────────────────────────────────┘│
│                            │                                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Polymorphic Django Models                  ││
│  │    Problem → Eipl/Mcq/Prompt/Refute/DebugFix/Probeable  ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
     ┌──────▼──────┐               ┌────────▼────────┐
     │   Celery    │               │    Docker       │
     │   Workers   │───────────────│    Sandbox      │
     │  (gevent)   │               │  (Code Exec)    │
     └─────────────┘               └─────────────────┘
```

---

## 2. Polymorphic Model Architecture

### Model Hierarchy

```
Problem (PolymorphicModel base)
│
├── StaticProblem (abstract) - No code execution
│   ├── McqProblem (concrete) - Multiple choice questions
│   └── RefuteProblem (concrete) - Find counterexample to disprove a claim
│
└── SpecProblem (abstract) - NL -> LLM -> code -> test
    ├── EiplProblem (concrete) - Explain in Plain Language
    ├── PromptProblem (concrete) - Image-based EiPL variant
    ├── DebugFixProblem (concrete) - Fix buggy code to pass tests
    ├── ProbeableCodeProblem (concrete) - Discover behavior via oracle, write code
    └── ProbeableSpecProblem (concrete) - Discover behavior via oracle, write NL explanation
```

### Package Structure

```
purplex/problems_app/models/
├── __init__.py      # Exports all models
├── base.py          # Problem (PolymorphicModel)
├── static.py        # StaticProblem, McqProblem
├── spec.py          # SpecProblem, EiplProblem, PromptProblem
├── test_case.py     # TestCase
├── hint.py          # ProblemHint
├── category.py      # ProblemCategory
├── problem_set.py   # ProblemSet, ProblemSetMembership
├── course.py        # Course, CourseEnrollment, CourseProblemSet
└── progress.py      # UserProgress, UserProblemSetProgress, ProgressSnapshot
```

### Key Fields by Model Type

| Model | Unique Fields |
|-------|---------------|
| **Problem (base)** | slug, title, description, difficulty, tags, is_active, completion_threshold, max_attempts, prerequisites |
| **StaticProblem (abstract)** | question_text, grading_mode |
| **McqProblem** | options (JSON), allow_multiple, shuffle_options |
| **RefuteProblem** | claim_text, claim_predicate, reference_solution, function_signature, expected_counterexample |
| **SpecProblem (abstract)** | reference_solution, function_signature, function_name, memory_limit, llm_config, segmentation_config, segmentation_threshold, requires_highlevel_comprehension |
| **EiplProblem** | (inherits all SpecProblem fields) |
| **PromptProblem** | image_url, image_alt_text |
| **DebugFixProblem** | buggy_code, bug_hints, allow_complete_rewrite |
| **ProbeableCodeProblem** | show_function_signature, probe_mode, max_probes, cooldown_attempts, cooldown_refill |
| **ProbeableSpecProblem** | show_function_signature, probe_mode, max_probes, cooldown_attempts, cooldown_refill |

### Polymorphic Query Behavior

```python
# Automatically returns correct subclass instances
problems = Problem.objects.all()
for problem in problems:
    print(problem.polymorphic_type)  # 'eipl', 'mcq', 'prompt', 'refute', 'debug_fix', 'probeable_code', 'probeable_spec'
    # problem is already the correct subclass (EiplProblem, etc.)
```

---

## 3. Activity Handler System

### Handler ABC Contract

All handlers implement `ActivityHandler` from `handlers/base.py`:

```python
class ActivityHandler(ABC):
    @property
    @abstractmethod
    def type_name(self) -> str: ...

    # Input validation
    def validate_input(self, raw_input: str, problem: Problem) -> ValidationResult: ...

    # Submission processing
    def process_submission(self, submission, raw_input, problem) -> ProcessingResult: ...

    # Grading
    def calculate_grade(self, submission) -> str: ...  # 'complete'|'partial'|'incomplete'
    def is_correct(self, submission) -> bool: ...
    def evaluate_completion(self, submission, problem) -> str: ...

    # Data extraction
    def extract_variations(self, submission) -> list[str]: ...
    def extract_test_results(self, submission, problem) -> list[dict]: ...
    def count_variations(self, submission) -> int: ...
    def count_passing_variations(self, submission) -> int: ...

    # Configuration for frontend/admin
    def get_problem_config(self, problem) -> dict: ...
    def get_admin_config(self) -> dict: ...
    def serialize_result(self, submission) -> dict: ...

    # Full submission lifecycle
    def submit(self, submission, raw_input, problem, context) -> SubmissionOutcome: ...

    # Optional hooks
    def on_submission_created(self, submission) -> None: ...
    def on_submission_complete(self, submission) -> None: ...
```

### Handler Registry

```python
# Registration via decorator
@register_handler('eipl')
class EiPLHandler(ActivityHandler):
    ...

# Lookup
handler = get_handler('eipl')  # Returns EiPLHandler instance
registered_types = get_registered_types()  # ['eipl', 'mcq', 'prompt', 'refute', 'debug_fix', 'probeable_code', 'probeable_spec']
```

### Handler Patterns

| Pattern | Types | Execution | Processing |
|---------|-------|-----------|------------|
| **Simple (Sync)** | MCQ, Refute | Synchronous | `execute_mcq_pipeline` or inline |
| **Complex (Async)** | EiPL, Prompt, ProbeableSpec | Async (Celery) | `execute_eipl_pipeline` task |
| **Code Execution (Async)** | DebugFix, ProbeableCode | Async (Celery) | `execute_debug_fix_pipeline`, `execute_probeable_code_pipeline` |

---

## 4. Service Layer

### Service Inventory (15 core services)

| Service | Responsibility |
|---------|----------------|
| **StudentService** | Problem fetching, handler config integration |
| **AdminProblemService** | CRUD operations, problem management |
| **ProgressService** | User progress tracking, row-level locking |
| **SubmissionValidationService** | Input validation, handler delegation |
| **HintService** | Hint availability, content delivery, usage tracking |
| **CourseService** | Course management, enrollment, progress |
| **SubmissionService** | Submission lifecycle, result recording |
| **DockerExecutionService** | Secure code execution in containers |
| **SegmentationService** | Code comprehension analysis |

### Data Flow Pattern

```
View → Service → Repository → Model

Example:
StudentView.get_problem_set()
  └→ StudentService.get_problem_set_problems()
       ├→ ProblemSetMembershipRepository.get_with_categories()
       └→ handler.get_problem_config() for each problem
```

### Transaction Safety

- `@transaction.atomic` on all write operations
- Row-level locking with `SELECT FOR UPDATE` for progress updates
- Retry logic for race conditions (100ms delay, 1 retry)

---

## 5. Repository Pattern

### Core Philosophy

- All public methods return **Model instances or Python types**, never QuerySets
- Services should NEVER import `django.db.models`
- All database logic encapsulated in repositories

### Base Repository Methods

```python
class BaseRepository(Generic[T]):
    def get_by_id(cls, id: int) -> Optional[T]
    def get_all(cls) -> List[T]
    def filter(cls, **kwargs) -> List[T]
    def create(cls, **kwargs) -> T
    def paginate(cls, page: int, per_page: int) -> Dict
    # ... and more
```

### N+1 Query Prevention

- `_with_test_case_counts()` annotation pattern
- `prefetch_related()` with custom `Prefetch()` for polymorphic models
- `.aggregate()` for statistics instead of Python loops

---

## 6. Celery Task Architecture

### Task Configuration

| Task | Timeout | Retry | Idempotency |
|------|---------|-------|-------------|
| `execute_eipl_pipeline` | 5min (dev) / 30min (prod) | None (ISSUE) | celery_task_id unique |
| `execute_mcq_pipeline` | Global default | max_retries=1 | celery_task_id unique |
| `execute_debug_fix_pipeline` | Global default | None | celery_task_id unique |
| `execute_probeable_code_pipeline` | Global default | None | celery_task_id unique |
| `prune_orphaned_containers` | - | 3 retries + backoff | N/A |

### Pipeline Flow (EiPL)

```
1. Idempotency Check (DB query for task_id)
2. AI Code Generation (OpenAI API - 3 variations)
3. Parallel Code Testing (GeventPool size=6)
4. Segmentation Analysis (if all tests pass)
5. Save Submission (atomic transaction)
6. Publish SSE Completion Event
```

### Reliability Score: 6/10

**Issues Identified:**
- Missing retry policies on pipeline tasks
- No task-level timeout overrides
- Distributed lock needed before expensive operations

---

## 7. Frontend Architecture

### Component Registry

```typescript
// Dynamic activity component loading
ACTIVITY_COMPONENTS = {
  eipl: {
    input: () => import('./inputs/EiplInput.vue'),
    feedback: () => import('./feedback/EiplFeedback.vue')
  },
  mcq: { ... },
  prompt: { ... },
  refute: { ... },
  debug_fix: { ... },
  probeable_code: { ... },
  probeable_spec: { ... }
}
```

### State Management

| Store | State |
|-------|-------|
| **auth.module** | User, loggedIn, authReady |
| **courses.module** | enrolledCourses, currentCourse, studentProgress |

### Key Composables

- `useEditorHints` - Hint application to code editor
- `useSubmissionTracking` - In-flight submissions + SSE cleanup
- `useFeedbackState` - Atomic feedback state management
- `useOptimisticProgress` - Optimistic UI updates

### Submission Flow

```
Sync (MCQ): Submit → API → Immediate response → Display feedback
Async (EiPL): Submit → API → SSE connection → Poll updates → Display feedback
```

---

## 8. Docker Sandbox Security

### Security Score: 86% (18/21 checks pass)

### Configuration Summary

| Control | Setting | Status |
|---------|---------|--------|
| Network | `network_mode='none'` | ✅ |
| Filesystem | `read_only=True` + limited tmpfs | ✅ |
| User | `user='1000:1000'` (non-root) | ✅ |
| Memory | `mem_limit='256m'`, no swap | ✅ |
| CPU | 50% quota, low priority | ✅ |
| Capabilities | `cap_drop=['ALL']` | ✅ |
| Privileges | `no-new-privileges` | ✅ |
| PID Limit | 50 (recommend 10) | ⚠️ |
| Seccomp | Default only | ⚠️ |
| Input Validation | String-based (recommend AST) | ⚠️ |

### Key Recommendations

1. **Custom seccomp profile** - Restrict syscalls to essential only
2. **Lower PID limit to 10** - Reduce fork bomb effectiveness
3. **AST-based code validation** - Prevent obfuscation bypasses

---

## 9. Quality Assessment

### Test Coverage

| Area | Score | Notes |
|------|-------|-------|
| Handlers | 9/10 | Excellent validation/grading coverage |
| Services | 4/10 | 50% have NO tests |
| Repositories | 3/10 | Architectural tests only |
| Views/API | 2/10 | Almost no endpoint tests |
| Celery Tasks | 0/10 | NO tests |
| Frontend Components | 3/10 | Service tests only |
| **Architecture Tests** | 10/10 | **Outstanding** AST-based enforcement |

### Documentation Accuracy

| Document | Accuracy |
|----------|----------|
| HANDLER_IMPLEMENTATION_DETAILS.md | 100% - Current |
| CLAUDE.md | 100% - Current |
| NEW_PROBLEM_TYPE_GUIDE.md | 95% - Minor model ref updates needed |
| CAPABILITY_ARCHITECTURE.md | 0% - Obsolete (describes unimplemented design) |
| POLYMORPHIC_MODELS_PLAN.md | 80% - Shows "Planning" but work is done |

---

## 10. Recommendations

### Priority 1: Critical (Immediate)

1. **Add Celery retry policies:**
   ```python
   @shared_task(
       autoretry_for=(ConnectionError, TimeoutError),
       retry_backoff=True,
       max_retries=3
   )
   ```

2. **Add task-level timeouts:**
   ```python
   time_limit=180,      # 3 minutes
   soft_time_limit=150  # 2.5 minutes
   ```

3. **Archive CAPABILITY_ARCHITECTURE.md** - Completely obsolete

### Priority 2: High (Next Sprint)

4. **Create POLYMORPHIC_MODEL_PACKAGE.md** - Document model package structure
5. **Update NEW_PROBLEM_TYPE_GUIDE.md** - Fix model path references
6. **Add distributed locks** for Celery task idempotency
7. **Implement AST-based code validation** in DockerExecutionService

### Priority 3: Medium (Ongoing)

8. **Add API endpoint tests** - Critical gap
9. **Add service layer unit tests** - 10+ untested services
10. **Consolidate test structure** - Move legacy tests to `/tests/`
11. **Add Vue component tests** - 102 of 103 untested
12. **Custom seccomp profile** for Docker sandbox

### Priority 4: Nice to Have

13. Add Celery task monitoring with failure alerting
14. Create API specification documentation
15. Add E2E tests with Playwright
16. Performance testing for N+1 query detection

---

## Architecture Diagram

```
                         ┌──────────────────┐
                         │    Firebase      │
                         │     Auth         │
                         └────────┬─────────┘
                                  │
┌─────────────────────────────────┼─────────────────────────────────┐
│                                 │                Vue 3 Frontend   │
│  ┌──────────┐  ┌──────────┐  ┌──┴───────┐  ┌───────────────────┐ │
│  │  Vuex    │  │ Services │  │  Router  │  │ Activity Registry │ │
│  │  Store   │  │  Layer   │  │          │  │ Input/Feedback    │ │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────────┘ │
└─────────────────────────────────┬─────────────────────────────────┘
                                  │ REST + SSE
┌─────────────────────────────────┼─────────────────────────────────┐
│                                 │                Django Backend   │
│  ┌──────────┐  ┌──────────┐  ┌──┴───────┐  ┌───────────────────┐ │
│  │  Views   │→ │ Services │→ │  Repos   │→ │ Polymorphic       │ │
│  │  (DRF)   │  │          │  │          │  │ Models            │ │
│  └──────────┘  └────┬─────┘  └──────────┘  └───────────────────┘ │
│                     │                                             │
│            ┌────────┴────────┐                                    │
│            │   Handlers      │                                    │
│            │ (7 problem types)│                                    │
│            └────────┬────────┘                                    │
└─────────────────────┼─────────────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
   ┌─────▼─────┐            ┌──────▼──────┐
   │  Celery   │            │   Docker    │
   │  Workers  │───────────→│   Sandbox   │
   │ (gevent)  │            │ (isolated)  │
   └───────────┘            └─────────────┘
         │                         │
   ┌─────▼─────┐            ┌──────▼──────┐
   │   Redis   │            │  PostgreSQL │
   │  (broker) │            │     15      │
   └───────────┘            └─────────────┘
```

---

## File Quick Reference

| Area | Key Files |
|------|-----------|
| Models | `problems_app/models/{base,static,spec}.py` |
| Handlers | `problems_app/handlers/{eipl,mcq,prompt,refute,debug_fix,probeable_code,probeable_spec}/handler.py` |
| Services | `problems_app/services/*.py`, `submissions/services.py` |
| Repositories | `problems_app/repositories/*.py` |
| Tasks | `problems_app/tasks/pipeline.py`, `problems_app/tasks/cleanup.py` |
| Frontend Registry | `client/src/components/activities/index.ts` |
| Frontend Types | `client/src/types/index.ts` |

---

*Generated by multi-agent architectural review - December 2024*
