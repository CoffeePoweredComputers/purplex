# Django Model Field Naming Guide

## Purpose
This document serves as the authoritative reference for Django model field names and relationships in the Purplex project. It was created to prevent FieldError exceptions caused by incorrect field naming.

## Critical Rules

### 1. Django ORM Filter Patterns - Objects vs IDs
Django's ORM is flexible and accepts both objects and IDs in filters:
```python
# Both patterns are CORRECT and equivalent:
UserProgress.objects.filter(user=user_object)  # Pass object instance
UserProgress.objects.filter(user_id=user_id)   # Pass ID directly

# Django automatically handles the conversion internally
# Use whichever is more convenient for your use case
```

### 2. Django Related Names - Understanding Object Access vs Query Fields
- **Object access** (ps.field): Uses `_set` for reverse ForeignKey relationships without related_name
- **Query annotations** (Count('field')): Uses lowercase model name WITHOUT `_set`
- **Prefetch operations**: Uses object access pattern (WITH `_set`)
- **Always verify**: Use `python manage.py shell` to test both patterns when in doubt

### 3. How to Check Correct Field Names
```python
# In Django shell:
from purplex.problems_app.models import ProblemSet, Course

# List all available fields on a model
ps = ProblemSet.objects.first()
print([f.name for f in ps._meta.get_fields()])

# Check reverse relations
course = Course.objects.first()
print(dir(course))  # Shows all attributes including reverse relations
```

## Model Relationships Reference

### ProblemSet Model
```python
# Direct fields
- slug
- title
- description
- problems (ManyToMany through 'ProblemSetMembership')
- icon
- is_public
- created_by (ForeignKey to User)
- created_at
- updated_at
- version

# Reverse relations (from other models pointing to ProblemSet)
- problemsetmembership_set (from ProblemSetMembership.problem_set)
  ⚠️ NOTE: Object access uses _set, query annotations do NOT
- courseproblemset (from CourseProblemSet.problem_set)
- courses (from Course.problem_sets)
- userproblemsetprogress (from UserProblemSetProgress.problem_set)
- userprogress (from UserProgress.problem_set)
- progresssnapshot (from ProgressSnapshot.problem_set)
- submissions (from PromptSubmission.problem_set)
```

### Course Model
```python
# Direct fields
- course_id
- slug
- name
- description
- instructor (ForeignKey to User, related_name='instructed_courses')
- problem_sets (ManyToMany through 'CourseProblemSet', related_name='courses')
- is_active
- enrollment_open
- is_deleted
- deleted_at
- created_at
- updated_at

# Reverse relations (for object access)
- courseproblemset_set (from CourseProblemSet.course - NO related_name)
  ✅ Object access uses _set because no related_name specified
- enrollments (from CourseEnrollment.course - related_name='enrollments')
  ✅ Uses explicit related_name, NOT courseenrollment_set

# Query field names (for annotations, no _set for defaults)
- courseproblemset (for Count, filter operations - default reverse name)
- enrollments (for Count, filter operations - explicit related_name)
```

### Problem Model
```python
# Direct fields
- slug
- title
- description
- difficulty
- categories (ManyToMany to ProblemCategory, related_name='problems')
  ⚠️ NOTE: This is ManyToMany, NOT ForeignKey - use prefetch_related, not select_related
- tags (JSONField - list of tag strings, NOT ManyToMany)
- is_active
- created_by (ForeignKey to User)
- created_at
- updated_at
- version
- completion_threshold
- max_attempts
- prerequisites (ManyToMany to self, related_name='unlocks')

# Reverse relations
- problemsetmembership_set (from ProblemSetMembership.problem - NO related_name)
- problem_sets (from ProblemSet.problems ManyToMany - related_name='problem_sets')
```

### User Model Extensions
```python
# Reverse relations added to Django User
- instructed_courses (from Course.instructor with related_name)
- course_enrollments (from CourseEnrollment.user with related_name)
- userprogress_set (from UserProgress.user)
- promptsubmission_set (from PromptSubmission.user)
```

## CRITICAL: Django Has Two Different Naming Patterns!

Django uses DIFFERENT field names for object access vs query construction:

1. **Object Access** (runtime relationship traversal):
   ```python
   # Use _set suffix for reverse ForeignKeys
   problem_set.problemsetmembership_set.all()
   problem_set.problemsetmembership_set.count()
   ```

2. **Query Annotations** (database query construction):
   ```python
   # NO _set suffix in Count, Sum, etc.
   ProblemSet.objects.annotate(
       problem_count=Count('problemsetmembership')  # NO _set here!
   )
   ```

3. **Prefetch Related** (query optimization):
   ```python
   # Use _set suffix (follows object access pattern)
   ProblemSet.objects.prefetch_related('problemsetmembership_set')
   ```

## Common Mistakes and Fixes

### ❌ WRONG: Confusing object access vs query field patterns
```python
# WRONG - mixing up object access and query patterns
# This fails - object access needs _set:
problem_set.problemsetmembership.all()  # AttributeError

# This fails - query annotations don't use _set:
Count('problemsetmembership_set')  # FieldError

# CORRECT - object access uses _set:
problem_set.problemsetmembership_set.all()

# CORRECT - query annotations don't use _set:
Count('problemsetmembership')
```

### ❌ WRONG: Missing _set for default reverse relations (object access)
```python
# WRONG - object access needs _set
course.courseproblemset.all()  # AttributeError

# CORRECT - object access uses _set
course.courseproblemset_set.all()

# BUT in queries, don't use _set:
# WRONG
Course.objects.annotate(count=Count('courseproblemset_set'))  # FieldError

# CORRECT
Course.objects.annotate(count=Count('courseproblemset'))
```

### ✅ CORRECT: Using defined related_names
```python
# These use explicit related_names
user.instructed_courses.all()  # NOT user.course_set.all()
user.course_enrollments.all()  # NOT user.courseenrollment_set.all()
```

## Query Patterns

### Annotating with Counts
```python
# Count related objects through intermediate model
# Query annotations use lowercase name WITHOUT _set
ProblemSet.objects.annotate(
    problem_count=Count('problemsetmembership')  # Correct - no _set in queries
)

# Count through reverse foreign key
# Query annotations still use lowercase name WITHOUT _set
Course.objects.annotate(
    problem_set_count=Count('courseproblemset')  # Correct - no _set in queries
)
```

### Prefetch Related
```python
# Prefetch through intermediate model
# Prefetch uses object access pattern - WITH _set
ProblemSet.objects.prefetch_related(
    'problemsetmembership_set__problem'  # Correct - _set for object access
)

# Prefetch reverse relation
Course.objects.prefetch_related(
    'courseproblemset_set__problem_set'  # Correct - _set for object access
)
```

## Model Field Mappings

### UserProfile Model
- **Fields**: `user` (OneToOneField, related_name='profile'), `firebase_uid`, `role`, `language_preference`
- **Properties**: `is_admin`, `is_instructor`, `is_instructor_or_admin`

### Problem Model (Polymorphic Base)
- **Fields**: `slug`, `title`, `description`, `difficulty`, `categories` (ManyToMany), `tags` (JSONField), `is_active`, `created_by`, `created_at`, `updated_at`, `version`, `completion_threshold`, `max_attempts`, `prerequisites` (ManyToMany to self)
- **Properties**: `polymorphic_type`, `problem_type`
- **Note**: Subclasses (EiplProblem, PromptProblem, etc.) add additional fields

### ProblemSet Model
- **Fields**: `slug`, `title`, `description`, `problems` (ManyToMany through ProblemSetMembership), `icon`, `is_public`, `created_by`, `created_at`, `updated_at`, `version`
- **Properties**: `problems_count`
- **Note**: Field is `is_public`, NOT `is_published`

### UserProgress Model
- **Fields**: `user`, `problem`, `problem_set`, `course`, `problem_version`, `status`, `grade`, `best_score`, `average_score`, `attempts`, `successful_attempts`, `first_attempt`, `last_attempt`, `completed_at`, `total_time_spent`, `hints_used`, `consecutive_successes`, `days_to_complete`, `is_completed`, `completion_percentage`
- **Note**: Uses `best_score`/`average_score`, NOT `score`. Uses `last_attempt`, NOT `last_submission_at`

### UserProblemSetProgress Model
- **Fields**: `user`, `problem_set`, `course`, `total_problems`, `completed_problems`, `in_progress_problems`, `average_score`, `first_attempt`, `last_activity`, `completed_at`, `completion_percentage`, `is_completed`
- **Note**: Uses `last_activity`, NOT `last_updated`

### Course Model
- **Fields**: `course_id`, `slug`, `name`, `description`, `instructor` (related_name='instructed_courses'), `problem_sets` (ManyToMany through CourseProblemSet), `is_active`, `enrollment_open`, `is_deleted`, `deleted_at`, `created_at`, `updated_at`

## Naming Rules

### Count Fields
- **Pattern**: `{plural_noun}_count`
- **Examples**: `problems_count`, `test_cases_count`, `visible_test_cases_count`
- **Avoid**: `problem_count`, `count_problems`

### Boolean Fields
- **Pattern**: `is_{adjective}` or `{verb}_enabled`
- **Examples**: `is_active`, `is_public`, `is_completed`, `enrollment_open`
- **Avoid**: `active`, `public`, `completed`

### Time Fields
- **Pattern**: `{action}_at` for timestamps
- **Examples**: `created_at`, `updated_at`, `completed_at`, `first_attempt`, `last_attempt`
- **Avoid**: `created_on`, `creation_time`

### Foreign Key Display Fields
- **Pattern**: `{related_model}_name` for display names
- **Examples**: `created_by_name`, `instructor_name`
- **Avoid**: `creator_name`, `created_by_username`

### Foreign Key ID Collections
- **Pattern**: `{related_model}_ids` for multiple IDs
- **Examples**: `category_ids`, `problem_ids`
- **Avoid**: `categories_id`, `category_id_list`

## Service Layer Standards

### Authentication Service
- Uses proper transaction management with `@transaction.atomic`
- Follows single responsibility principle for Firebase authentication
- Proper error handling with appropriate exceptions

### User Service
- Centralized user management operations
- Consistent query optimization with `select_related()`
- Transaction protection for critical operations

## Identified Inconsistencies

### ✅ FIXED - UserProfile Related Name (2024-09-06)
- **UserProfile Related Name**: Fixed all instances where code used `userprofile` instead of `profile`
  - permissions.py: All instances now correctly use `user.profile.role`
  - user_repository.py: All instances now correctly use `select_related("profile")` and `profile__role`
- All permission checks now correctly use `user.profile.role`
- **Production Status**: READY

### CURRENT AUDIT RESULTS (2024-12-26)

#### 🚨 ACTIVE ISSUES REQUIRING FIXES

#### ❌ ProblemSet Repository Field Name Errors
**File**: `purplex/problems_app/repositories/problem_set_repository.py`
- **Issue 1**: Uses `is_published` field (lines 49, 75, 130, 230, 252, 262) but `ProblemSet` model has `is_public`
- **Issue 2**: Uses `select_related("category")` (line 102) but `Problem` has `categories` (ManyToMany)
- **Issue 3**: Uses `weight` field in ProblemSetMembership creation (line 243) but model has no `weight` field
- **Runtime Risk**: `FieldError` and `AttributeError` on these code paths

#### ❌ Progress Repository Field Name Errors
**File**: `purplex/problems_app/repositories/progress_repository.py`
- **Issue 1**: Uses `score` field (lines 186-188, 270-272, 299-301) but `UserProgress` has `best_score`/`average_score`
- **Issue 2**: Uses `last_submission_at` (line 536) but `UserProgress` has `last_attempt`
- **Issue 3**: Uses `order_by("-last_updated")` (line 165) but `UserProblemSetProgress` has `last_activity`
- **Runtime Risk**: `FieldError` on these code paths

#### 📊 CURRENT AUDIT STATISTICS
- **UserProfile Field Access**: ✅ FIXED - All repositories/services use correct `profile` related_name
- **ProblemSet Repository**: ❌ 6+ field name issues
- **Progress Repository**: ❌ 6+ field name issues
- **Production Ready**: ❌ **BLOCKED** - Repository field name fixes required

#### 🔧 REQUIRED FIXES FOR PRODUCTION

**Priority 1 - ProblemSet Repository `is_published` -> `is_public`**
```python
# ❌ INCORRECT (causes FieldError)
ProblemSet.objects.filter(is_published=True)
ps.is_published

# ✅ CORRECT
ProblemSet.objects.filter(is_public=True)
ps.is_public
```

**Priority 2 - Problem Category Field (ManyToMany)**
```python
# ❌ INCORRECT (causes FieldError - cannot use select_related on ManyToMany)
Problem.objects.select_related('category')

# ✅ CORRECT
Problem.objects.prefetch_related('categories')
```

**Priority 3 - Progress Repository Score Field**
```python
# ❌ INCORRECT (causes FieldError)
progress_qs.filter(score__isnull=False).aggregate(Avg("score"))

# ✅ CORRECT
progress_qs.filter(best_score__isnull=False).aggregate(Avg("best_score"))
```

**Priority 4 - Progress Repository Timestamp Fields**
```python
# ❌ INCORRECT
order_by("-last_updated")  # UserProblemSetProgress
p.last_submission_at       # UserProgress

# ✅ CORRECT
order_by("-last_activity")  # UserProblemSetProgress
p.last_attempt              # UserProgress
```

### Field Access Patterns Summary
- **Object Access Pattern**: `ps.problemsetmembership_set.all()` ✅
- **Query Annotation Pattern**: `Count('problemsetmembership')` ✅
- **Prefetch Pattern**: `prefetch_related('problemsetmembership_set')` ✅
- **Common Mistake**: Using `problemsetmembership` for object access ❌

## Testing Field Names

Add this test to prevent regressions:

```python
# tests/unit/test_field_names.py
from django.test import TestCase
from purplex.problems_app.models import ProblemSet, Course

class TestFieldNames(TestCase):
    def test_problemset_reverse_relations(self):
        """Verify ProblemSet reverse relation names"""
        ps = ProblemSet.objects.create(title="Test")

        # ProblemSetMembership.problem_set has NO related_name, so default _set suffix applies
        self.assertTrue(hasattr(ps, 'problemsetmembership_set'))  # Object access uses _set
        # Query annotations use lowercase without _set: Count('problemsetmembership')

    def test_course_reverse_relations(self):
        """Verify Course reverse relation names"""
        course = Course.objects.create(
            course_id="TEST101",
            name="Test Course",
            instructor_id=1
        )

        # CourseProblemSet.course has NO related_name, so default _set suffix applies
        self.assertTrue(hasattr(course, 'courseproblemset_set'))  # Object access uses _set
        # CourseEnrollment.course has related_name="enrollments"
        self.assertTrue(hasattr(course, 'enrollments'))  # Explicit related_name
```

## Quick Reference Checklist

Before using a field name:

- [ ] **Object access** (ps.field.all()): Use `modelname_set` for reverse ForeignKeys without related_name
- [ ] **Query operations** (Count, filter): Use lowercase `modelname` WITHOUT `_set`
- [ ] **Prefetch operations**: Use object access pattern (WITH `_set`)
- [ ] **Check explicit related_names**: Use the exact related_name specified in model
- [ ] **Test in Django shell**: Verify both object access and query patterns
- [ ] **Add to this guide** when discovering new relationship patterns

## Updates Log
- 2024-08-14: Initial field naming guide creation based on authentication system review
- 2024-08-14: CRITICAL - Identified UserProfile related_name mismatch causing runtime errors
- 2024-09-05: Complete rewrite with comprehensive Django relationship documentation
- 2024-09-05: Fixed problemsetmembership field naming confusion - clarified object vs query patterns
- 2024-09-05: CRITICAL - Repository code has mixed patterns that need fixing
- 2024-09-05: Added testing guidelines and query patterns
- 2024-09-06: ✅ FIXED - permissions.py and user_repository.py now use correct `profile` field
- 2024-09-06: ❌ CRITICAL DISCOVERY - Problem model field mismatches: `is_draft` vs `is_active`, `category` vs `categories`
- 2024-09-06: ❌ CRITICAL DISCOVERY - ManyToMany misuse: `select_related('category')` on `categories` field
- 2024-12-26: **CODEBASE VERIFICATION** - Audited actual Django models vs repository code:
  - ✅ FIXED: UserProfile access - all repositories now correctly use `profile` (not `userprofile`)
  - ❌ ACTIVE: problem_set_repository.py uses `is_published` but model has `is_public`
  - ❌ ACTIVE: problem_set_repository.py uses `select_related("category")` but Problem has `categories` (ManyToMany)
  - ❌ ACTIVE: progress_repository.py uses `score` but model has `best_score`/`average_score`
  - ❌ ACTIVE: progress_repository.py uses `last_submission_at` but model has `last_attempt`
  - ❌ ACTIVE: progress_repository.py uses `order_by("-last_updated")` but model has `last_activity`
  - **Production Status**: BLOCKED - Repository field name fixes required in problem_set_repository.py and progress_repository.py
