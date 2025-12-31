# Technical Debt Registry

Last Updated: 2025-12-26
Originally Generated: 2024-11-28

## Priority Levels
- **P0 Critical**: Security vulnerabilities, data loss risks, breaking bugs
- **P1 High**: Performance bottlenecks, scalability blockers, major inconsistencies
- **P2 Medium**: Code quality issues, pattern violations, maintainability concerns
- **P3 Low**: Style inconsistencies, minor improvements, nice-to-haves

---

## P0 - Critical

### 1. ~~Docker Container Missing Security Hardening~~ FIXED
- **Location**: `purplex/problems_app/services/docker_execution_service.py`
- **Original Issue**: Missing seccomp/AppArmor profiles, `privileged=False` not explicit, `cap_drop=['ALL']` missing
- **Resolution**: Container config now includes:
  - `privileged=False` (explicit at lines 191, 1191)
  - `cap_drop=['ALL']` (lines 192, 1192)
  - `security_opt=['no-new-privileges']` (lines 193, 1193)
  - `cpu_shares=128` for priority control (lines 188, 1188)

### 2. ~~Celery Pipeline Tasks Not Idempotent~~ FIXED
- **Location**: `purplex/problems_app/tasks/pipeline.py`
- **Original Issue**: `execute_eipl_pipeline` and `execute_mcq_pipeline` created duplicate submissions on retry
- **Resolution** (2024-11-29):
  - Added unique constraint on `celery_task_id` field (migration 0007)
  - Added idempotency check at start of both pipelines (lines 682-692, 1097-1109)
  - Passing `celery_task_id` atomically during submission creation
  - Added IntegrityError handling for race conditions (lines 466-479, 1200-1211)
- **Files Modified**:
  - `purplex/submissions/models.py` - unique constraint on celery_task_id (line 134)
  - `purplex/submissions/migrations/0007_add_celery_task_id_unique_constraint.py`
  - `purplex/submissions/services.py` - added celery_task_id parameter
  - `purplex/problems_app/tasks/pipeline.py` - idempotency checks + IntegrityError handling

### 3. Frontend: Oversized Components (Partially Addressed)
- **Location**: Multiple Vue components
- **Current State**:
  - `AdminProblemEditor.vue`: REFACTORED into modular editor system:
    - `AdminProblemEditorShell.vue` (414 lines) - orchestrator
    - Type-specific editors in `admin/editors/` (~200-400 lines each)
    - Shared sections in `admin/editors/shared/` for reuse
  - `ProblemSet.vue`: 2,888 lines (7x limit) - still needs refactoring
  - `Feedback.vue`: 1,472 lines (3.6x limit) - reduced from 1,773
- **Impact**: Maintainability improved for admin editor, other components still large
- **Effort**: Medium (24-32 hours for remaining components)
- **Priority**: Downgrade to P1 given partial progress

### 4. ~~TypeScript: Widespread `:any` Type Usage~~ MOSTLY FIXED
- **Location**: Originally 106 instances across 26 files
- **Current State**: ~20 instances across 7 files
  - `.ts` files: 10 instances (4 files) - mostly test files and composables
  - `.vue` files: 10 instances (3 files) - AdminSubmissions, EiplProblemEditor, PromptProblemEditor
- **Resolution**: Reduced by ~81% from original count
- **Remaining**: Legitimate use cases for mocking in tests and gradual typing in admin components
- **Status**: Considered acceptable technical debt

### 5. Test Coverage Gaps (Deferred)
- **Status**: Intentionally deferred until architecture stabilizes
- **Missing**: SubmissionService, GradingService, DockerExecutionService, AuthenticationService, Celery tasks

---

## P1 - High

### 6. ~~N+1 Queries in Model Properties~~ FIXED
- **Location**: `purplex/problems_app/models/spec.py:86-91` (properties still exist for backward compatibility)
- **Original Issue**: `test_cases_count` and `visible_test_cases_count` properties trigger queries per item
- **Resolution**: `ProblemRepository._with_test_case_counts()` (lines 34-44) uses `annotate()` with `Count()` to pre-compute these values in bulk queries

### 7. ~~Count Defeating Prefetch in Views~~ FIXED
- **Status**: Marked as fixed in Quick Wins section
- **Resolution**: Use `len()` on prefetched list instead of `.filter().count()`

### 8. ~~Celery: Missing Retry Config on Cleanup Tasks~~ FIXED
- **Location**: `purplex/problems_app/tasks/cleanup.py`
- **Resolution**: Both tasks now have retry configuration:
  - `prune_orphaned_containers` (lines 14-18): `autoretry_for=(Exception,)`, `retry_backoff=True`, `max_retries=3`
  - `log_pool_metrics` (lines 97-101): `autoretry_for=(Exception,)`, `retry_backoff=True`, `max_retries=2`

### 9. ~~Celery: GeventPool Not Cleaned on Exception~~ FIXED
- **Location**: `purplex/problems_app/tasks/pipeline.py`
- **Resolution**: `managed_gevent_pool()` context manager (lines 23-29) ensures cleanup on both success and exception paths via `finally` block

### 10. ~~Docker: Resource Exhaustion Risks~~ FIXED
- **Location**: `purplex/problems_app/services/docker_execution_service.py`
- **Resolution**: Container config includes:
  - `mem_limit` and `memswap_limit` (lines 184-185, 1183-1184)
  - `cpu_quota` and `cpu_period` (lines 186-187, 1185-1186)
  - `cpu_shares=128` for priority control (lines 188, 1188)
  - `pids_limit=50` (lines 189, 1189)
  - `ulimits` for file descriptor limits (lines 206-210, 1206-1208)

### 11. Frontend: Inconsistent Vue API Usage (Improved)
- **Location**: All Vue components
- **Current State**: ~55 components now use `<script setup>` (Composition API)
- **Remaining Work**: Some legacy components still use Options API
- **Effort**: Medium (16-24 hours for remaining migration)
- **Priority**: Consider downgrading to P2 given progress

### 12. ~~Frontend: Console.log in Production Code~~ FIXED
- **Resolution**: Only `utils/logger.ts` contains console methods (intentionally, as the logging utility)
- **All other files**: Now use structured `log` utility

### 13. Frontend: No Logging in Critical Services
- **Location**: `problemService.ts`, `router.ts`
- **Issue**: No visibility into API calls or navigation
- **Status**: Still outstanding
- **Effort**: Medium (4-6 hours)

---

## P2 - Medium

### 14. ~~Deprecated `.extra()` Usage~~ FIXED
- **Location**: `purplex/problems_app/repositories/course_enrollment_repository.py`
- **Resolution**: Now uses `TruncDate("enrolled_at")` with `annotate()` (lines 272-276)

### 15. ~~Missing Database Indexes~~ FIXED
- **Resolution**: Comprehensive indexes now exist:
  - `Problem` model (`base.py:87-91`): `is_active+created_at`, `is_active+difficulty`, `created_by+created_at`
  - `Course` model (`course.py:40-43`): `course_id`, `instructor+is_active`, `is_deleted+is_active`
  - `CourseEnrollment` model (`course.py:100-103`): `user+is_active`, `course+is_active`
  - `UserProgress` model (`progress.py:74-78`): multiple query pattern indexes
  - `UserProblemSetProgress` model (`progress.py:108-111`): user+course, problem_set+course indexes
  - `ProgressSnapshot` model (`progress.py:190-193`): user+date, user+problem+date indexes

### 16. No Caching for Instructor Analytics
- **Location**: `purplex/problems_app/services/instructor_analytics_service.py`
- **Issue**: Expensive dashboard queries not cached
- **Status**: Still outstanding - no cache usage found in service
- **Effort**: Medium (2-3 hours)

### 17. Docker: Code Validation Uses Blacklist
- **Location**: `purplex/problems_app/services/docker_execution_service.py:893-938`
- **Issue**: Blacklist-based validation can be bypassed
- **Recommendation**: Add AST-based validation as defense-in-depth
- **Status**: Still outstanding
- **Effort**: Medium (4-6 hours)

### 18. Frontend: Hardcoded Colors
- **Location**: 30+ instances across components
- **Issue**: Bypasses design system CSS variables
- **Status**: Still outstanding
- **Effort**: Low (8-12 hours)

### 19. Frontend: Excessive Animations
- **Location**: Various components
- **Issue**: 177 animation definitions, some aggressive hover effects
- **Status**: Still outstanding
- **Effort**: Medium (12-16 hours)

### 20. Frontend: Inconsistent Modal Implementations
- **Location**: 9 modals with different patterns
- **Recommendation**: Create `BaseModal.vue` component
- **Status**: Still outstanding
- **Effort**: Medium (12-16 hours)

### 21. ~~Celery: Redis Publish Failures Silent~~ FIXED
- **Location**: `purplex/problems_app/tasks/pipeline.py:61-89`
- **Resolution**: `_publish_to_redis()` function now implements:
  - 3 retries with exponential backoff (lines 70-80)
  - Proper logging for all failure scenarios
  - Returns boolean success indicator

---

## P3 - Low

### 22. Repositories Return Lists Instead of QuerySets
- **Location**: Multiple repository classes
- **Issue**: Prevents lazy evaluation and query chaining
- **Status**: Still outstanding
- **Effort**: Medium

### 23. Celery: Hardcoded max_workers
- **Location**: `purplex/problems_app/tasks/pipeline.py:773-775`
- **Issue**: `max_workers = min(variation_count, 6)` should be configurable
- **Status**: Still outstanding
- **Effort**: Low

### 24. Celery: No Circuit Breaker for OpenAI
- **Location**: `purplex/problems_app/tasks/pipeline.py`
- **Issue**: No fast-fail when OpenAI API is degraded
- **Status**: Still outstanding
- **Effort**: Medium (2-3 hours)

### 25. Frontend: Dark Mode Inconsistency
- **Location**: Various components
- **Issue**: Some components reference light mode despite dark-mode-only app
- **Status**: Still outstanding
- **Effort**: Low (2-4 hours)

### 26. Docker: No Container Image Signature Verification
- **Location**: `purplex/problems_app/services/docker_execution_service.py`
- **Issue**: Uses tags instead of digests
- **Status**: Still outstanding
- **Effort**: Low

---

## Quick Wins (< 30 min each)

1. [x] Add Docker hardening (P0) - DONE 2024-11-28
2. [x] Add Celery retry configs (P1) - DONE 2024-11-28
3. [x] Fix GeventPool cleanup (P1) - DONE 2024-11-28 (context manager)
4. [x] Replace `.extra()` with `TruncDate` (P2) - DONE 2024-11-28
5. [x] Add Docker resource limits (P1) - DONE 2024-11-28 (cpu_shares)
6. [x] Fix N+1 queries in ProblemRepository (P1) - DONE 2024-11-28 (annotate helper)
7. [x] Fix count defeating prefetch in views (P1) - DONE 2024-11-28 (use len() on prefetched list)
8. [x] Add missing database indexes (P2) - DONE 2024-11-28 (comprehensive index additions)
9. [x] Redis publish retry logic (P2) - DONE 2024-11-28 (3 retries with backoff, better logging)

## Major Fixes

1. [x] Celery Pipeline Idempotency (P0) - DONE 2024-11-29
   - Unique constraint on `celery_task_id`
   - Early exit check at pipeline start
   - Atomic task_id assignment during submission creation
   - IntegrityError handling for race conditions

2. [x] AdminProblemEditor Refactoring (P0) - DONE (date unknown)
   - Monolithic 5,256-line component split into modular editor system
   - Type-specific editors for each problem type
   - Shared sections for common functionality

---

## Summary

### Completed Items: 15
- P0: 3 of 5 (Docker hardening, Celery idempotency, AdminProblemEditor refactor)
- P1: 7 of 8 (N+1 queries, prefetch fix, Celery retries, GeventPool cleanup, Docker limits, Console.log, Vue API progress)
- P2: 5 of 8 (.extra() usage, database indexes, Redis retry logic)

### Outstanding Items: 11
| Priority | Outstanding | Items |
|----------|-------------|-------|
| P0 | 2 | Component size (ProblemSet/Feedback), Test coverage |
| P1 | 1 | Frontend logging in services |
| P2 | 3 | Analytics caching, Docker blacklist, Hardcoded colors, Animations, Modals |
| P3 | 5 | All P3 items remain |

### Revised Effort Estimate

| Priority | Remaining Issues | Estimated Hours |
|----------|-----------------|-----------------|
| P0 Critical | 2 | 30-40 |
| P1 High | 1 | 4-6 |
| P2 Medium | 5 | 40-55 |
| P3 Low | 5 | 15-25 |
| **Total** | **13** | **89-126** |

*Note: Original estimate was 175-245 hours for 26 issues. Approximately 86-119 hours of work completed.*
