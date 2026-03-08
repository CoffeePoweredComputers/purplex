# Data Model Cleanup Plan

**Branch:** `worktree-tech-debt/data-model-cleanup`
**Created:** 2026-03-07
**Status:** Planning

## Fixes

| # | Fix | Priority | Effort | Status |
|---|-----|----------|--------|--------|
| 1 | Fix repository field-name bugs (`is_published`, `score`, `last_submission_at`, etc.) | P0 | Low | Done |
| 2 | Extract `ProbeConfigMixin` from duplicated probe fields | P1 | Low | Pending |
| 3 | Migrate `unique_together` → `UniqueConstraint` (10 models) | P1 | Low | Pending |
| 4 | Add soft-delete manager to `Course` | P2 | Low | Done |
| 5 | Remove `TestCase` order uniqueness constraint | P2 | Low | Done |
| 6 | Normalize comprehension level vocabulary | P2 | Low | Pending |
| 7 | Clean up `new_submissions` related names | P2 | Medium | Done |
| 8 | Fix slug collision handling (ProblemSet, Course, Category) | P2 | Low | Done |
| 9 | Update stale FIELD_NAMING_GUIDE.md | P3 | Low | Pending |

## Details

### 1. Fix repository field-name bugs
**Files:** `problem_set_repository.py`, `progress_repository.py`

| Wrong Field | Correct Field | File | Lines |
|------------|---------------|------|-------|
| `is_published` | `is_public` | problem_set_repository.py | 49, 75, 244, 266, 279 |
| `select_related("category")` | `prefetch_related("categories")` | problem_set_repository.py | 102 |
| `weight` (membership create) | field doesn't exist | problem_set_repository.py | 256 |
| `score` | `best_score` | progress_repository.py | 186-188, 270-272, 299-301 |
| `last_submission_at` | `last_attempt` | progress_repository.py | 536 |
| `order_by("-last_updated")` | `order_by("-last_activity")` | progress_repository.py | 164 |

### 2. Extract ProbeConfigMixin
**Files:** `problems_app/models/spec.py`

`ProbeableCodeProblem` and `ProbeableSpecProblem` share 5 identical fields:
- `show_function_signature`
- `probe_mode` + `PROBE_MODE_CHOICES`
- `max_probes`
- `cooldown_attempts`
- `cooldown_refill`

Extract to an abstract `ProbeConfigMixin`.

### 3. Migrate unique_together → UniqueConstraint
**Files:** All model files with `unique_together` in Meta

Models affected: `CourseProblemSet`, `CourseEnrollment`, `CourseInstructor`, `ProblemSetMembership`, `TestCase`, `ProblemHint`, `UserProgress`, `UserProblemSetProgress`, `ProgressSnapshot`, `HintActivation`, `CodeVariation`

### 4. Add soft-delete manager to Course
**File:** `problems_app/models/course.py`

Add `ActiveCourseManager` as default `objects` manager (filters `is_deleted=False`). Add `all_objects = models.Manager()` escape hatch.

### 5. Remove TestCase order uniqueness constraint
**File:** `problems_app/models/test_case.py`

Drop `unique_together = ["problem", "order"]` — makes reordering painful. `ordering = ["order", "id"]` in Meta is sufficient.

### 6. Normalize comprehension level vocabulary
**Files:** `submissions/models.py`

`Submission.comprehension_level` uses `"high-level"/"low-level"/"not_evaluated"`.
`SegmentationAnalysis.comprehension_level` uses `"relational"/"multi_structural"`.
Align to single vocabulary.

### 7. Clean up `new_submissions` related names
**File:** `submissions/models.py`

Rename `related_name="new_submissions"` to `related_name="submissions"` on all FKs in Submission model (migration artifact).

### 8. Fix slug collision handling
**Files:** `problem_set.py`, `course.py`, `category.py`

`Problem.save()` handles slug collisions with a counter loop. The other three models don't — they'll get `IntegrityError` on duplicate slugs.

### 9. Update stale FIELD_NAMING_GUIDE.md
**File:** `docs/development/FIELD_NAMING_GUIDE.md`

Still references `Course.instructor` FK which was dropped. Update Course Model section to reflect `CourseInstructor` through-table.
