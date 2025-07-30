# Django Field Naming Standards & Schema Validation Guide

This document standardizes field naming across models, serializers, and view annotations while ensuring schema consistency throughout the Django backend.

## ProblemCategory Model

### Base Fields
- `name` (CharField)
- `slug` (SlugField) 
- `description` (TextField)
- `icon` (ImageField)
- `color` (CharField)
- `order` (PositiveIntegerField)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)

### Computed Fields (Serializer Only)
- `problems_count` (ReadOnlyField)

## Problem Model

### Base Fields
- `slug` (SlugField)
- `problem_type` (CharField)
- `title` (CharField)
- `description` (TextField)
- `difficulty` (CharField)
- `function_name` (CharField)
- `function_signature` (TextField)
- `reference_solution` (TextField)
- `memory_limit` (PositiveIntegerField)
- `tags` (JSONField)
- `is_active` (BooleanField)
- `created_by` (ForeignKey)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)
- `version` (PositiveIntegerField)
- `completion_threshold` (IntegerField)
- `completion_criteria` (JSONField)
- `max_attempts` (IntegerField)

### Model Properties
- `test_cases_count` - returns `self.test_cases.count()`
- `visible_test_cases_count` - returns `self.test_cases.filter(is_hidden=False).count()`

### Computed Fields (Serializer Only)
- `categories` (ProblemCategorySerializer, many=True)
- `category_ids` (PrimaryKeyRelatedField, write_only)
- `problem_sets` (SimpleProblemSetSerializer, many=True)
- `test_cases` (TestCaseSerializer, many=True)
- `created_by_name` (CharField from `created_by.username`)

## ProblemSet Model

### Base Fields
- `slug` (SlugField)
- `title` (CharField)
- `description` (TextField)
- `icon` (ImageField)
- `is_public` (BooleanField)
- `created_by` (ForeignKey)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)
- `version` (PositiveIntegerField)

### Model Properties
- `problems_count` - returns `self.problems.count()`

### View Annotations
- `problems_count` - computed using `Count('problems')`

### Computed Fields (Serializer Only)
- `problems_detail` (ProblemSetMembershipSerializer, many=True)
- `created_by_name` (CharField from `created_by.username`)

## TestCase Model

### Base Fields
- `inputs` (JSONField)
- `expected_output` (JSONField)
- `description` (CharField)
- `is_hidden` (BooleanField)
- `is_sample` (BooleanField)
- `order` (PositiveIntegerField)
- `created_at` (DateTimeField)

## UserProgress Model

### Base Fields
- `user` (ForeignKey)
- `problem` (ForeignKey)
- `problem_set` (ForeignKey)
- `course` (ForeignKey)
- `problem_version` (PositiveIntegerField)
- `status` (CharField)
- `best_score` (IntegerField)
- `average_score` (FloatField)
- `attempts` (IntegerField)
- `successful_attempts` (IntegerField)
- `first_attempt` (DateTimeField)
- `last_attempt` (DateTimeField)
- `completed_at` (DateTimeField)
- `total_time_spent` (DurationField)
- `hints_used` (IntegerField)
- `consecutive_successes` (IntegerField)
- `days_to_complete` (IntegerField)
- `is_completed` (BooleanField)
- `completion_percentage` (IntegerField)

## UserProblemSetProgress Model

### Base Fields
- `user` (ForeignKey)
- `problem_set` (ForeignKey)
- `course` (ForeignKey)
- `total_problems` (IntegerField)
- `completed_problems` (IntegerField)
- `in_progress_problems` (IntegerField)
- `average_score` (FloatField)
- `first_attempt` (DateTimeField)
- `last_activity` (DateTimeField)
- `completed_at` (DateTimeField)
- `completion_percentage` (IntegerField)
- `is_completed` (BooleanField)

## Course Model

### Base Fields
- `course_id` (CharField) - user-defined ID
- `slug` (SlugField)
- `name` (CharField)
- `description` (TextField)
- `instructor` (ForeignKey)
- `is_active` (BooleanField)
- `enrollment_open` (BooleanField)
- `is_deleted` (BooleanField)
- `deleted_at` (DateTimeField)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)

### Computed Fields (Serializer Only)
- `instructor_name` (CharField from `instructor.get_full_name`)
- `problem_sets_count` (IntegerField from `problem_sets.count`)
- `enrolled_students_count` (IntegerField from `enrollments.filter(is_active=True).count`)

## CourseProblemSet Model

### Base Fields
- `course` (ForeignKey)
- `problem_set` (ForeignKey)
- `order` (PositiveIntegerField)
- `added_at` (DateTimeField)
- `is_required` (BooleanField)
- `problem_set_version` (IntegerField)

## CourseEnrollment Model

### Base Fields
- `user` (ForeignKey)
- `course` (ForeignKey)
- `enrolled_at` (DateTimeField)
- `is_active` (BooleanField)

## ProblemHint Model

### Base Fields
- `problem` (ForeignKey)
- `hint_type` (CharField)
- `is_enabled` (BooleanField)
- `min_attempts` (IntegerField)
- `content` (JSONField)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)

## Naming Rules

### 1. Count Fields
- **Model properties**: Always plural + `_count` (e.g., `problems_count`, `test_cases_count`)
- **View annotations**: Must match serializer field names exactly
- **Serializer fields**: Use `ReadOnlyField()` referencing model property or annotation

### 2. Foreign Key References
- **Related object data**: Use nested serializer (e.g., `categories`, `problem_sets`)
- **Write-only IDs**: Use `_ids` suffix (e.g., `category_ids`, `problem_set_ids`)
- **Display names**: Use `_name` suffix (e.g., `created_by_name`, `instructor_name`)

### 3. Status and State Fields
- **Boolean states**: Use `is_` prefix (e.g., `is_active`, `is_completed`, `is_public`)
- **Enum states**: Use simple noun (e.g., `status`, `difficulty`, `hint_type`)
- **Status Values**: Backend uses underscored format (`not_started`, `in_progress`, `completed`)

### 4. Time Fields
- **Creation**: `created_at`
- **Updates**: `updated_at`
- **Completion**: `completed_at`
- **Activity**: `last_attempt`, `first_attempt`, `last_activity`
- **Deletion**: `deleted_at`

### 5. Aggregate Fields
- **Counts**: `*_count` (plural noun + count)
- **Averages**: `average_*` (e.g., `average_score`)
- **Totals**: `total_*` (e.g., `total_problems`, `total_time_spent`)
- **Percentages**: `*_percentage` (e.g., `completion_percentage`)

## Schema Validation Guidelines

### Model-View Consistency
- Ensure Django ORM queries reference fields that actually exist on target models
- Cross-reference field usage in views against model definitions
- Validate foreign key relationships use correct field names

### Field Naming Standards Enforcement
- All count fields should follow `{plural_noun}_count` pattern
- Boolean fields must use `is_` prefix for clarity
- Time fields should follow standard conventions (`created_at`, `updated_at`, etc.)
- Foreign key references should use appropriate suffixes (`_ids` for write operations, `_name` for display)

### Serializer Integration
- ReadOnlyFields should match model properties or view annotations exactly
- Write-only fields should follow clear naming patterns
- Computed fields should be properly documented and maintained

## Status Naming Consistency

### Status Value Format (Resolved)
- **Backend (Django)**: Uses underscored format for status values (`not_started`, `in_progress`, `completed`)
- **Frontend (Vue/CSS)**: Uses underscored format for both data values and CSS classes (`not_started`, `in_progress`, `completed`)
- **Status**: ✅ Fully consistent across the entire codebase
- **Note**: All components now use underscored format consistently