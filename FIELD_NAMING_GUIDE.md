# Field Naming Standards Guide

This guide maintains consistency in field naming across Purplex's Django models, serializers, and views.

## Model Field Mappings

### UserProfile Model
- **Fields**: `user`, `firebase_uid`, `role`
- **Properties**: `is_admin`, `is_instructor`, `is_instructor_or_admin`

### Problem Model
- **Fields**: `slug`, `problem_type`, `title`, `description`, `difficulty`, `categories`, `function_name`, `function_signature`, `reference_solution`, `memory_limit`, `tags`, `is_active`, `created_by`, `created_at`, `updated_at`, `version`, `completion_threshold`, `completion_criteria`, `segmentation_config`, `max_attempts`, `prerequisites`
- **Properties**: `test_cases_count`, `visible_test_cases_count`, `segmentation_enabled`, `segmentation_threshold`

### ProblemSet Model  
- **Fields**: `slug`, `title`, `description`, `problems`, `icon`, `is_public`, `created_by`, `created_at`, `updated_at`, `version`
- **Properties**: `problems_count`

### UserProgress Model
- **Fields**: `user`, `problem`, `problem_set`, `course`, `problem_version`, `status`, `best_score`, `average_score`, `attempts`, `successful_attempts`, `first_attempt`, `last_attempt`, `completed_at`, `total_time_spent`, `hints_used`, `consecutive_successes`, `days_to_complete`, `is_completed`, `completion_percentage`

### Course Model
- **Fields**: `course_id`, `slug`, `name`, `description`, `instructor`, `problem_sets`, `is_active`, `enrollment_open`, `is_deleted`, `deleted_at`, `created_at`, `updated_at`

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

### Current Status: CLEAN
The authentication system implementation follows Django best practices and maintains consistent field naming conventions.

## Updates Log
- 2025-08-14: Initial field naming guide creation based on authentication system review