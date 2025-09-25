# Comprehensive Testing Framework for Purplex

## Overview
This testing framework provides comprehensive coverage for the submission pipeline, hint system, and progress tracking functionality. Tests are organized using Django TestCase classes and pytest markers for different test types.

**⚠️ CURRENT STATUS**: Most tests are blocked by authentication issues. Only basic infrastructure tests are fully working. The test framework is well-structured but needs authentication mocking fixes to be functional.

## Working Test Setup

### Commands That Work
```bash
# Required environment setup (MUST RUN FIRST)
source env/bin/activate
export DJANGO_SETTINGS_MODULE=purplex.settings

# Basic tests that pass
pytest tests/test_setup.py         # 3/3 passing - infrastructure tests

# Test categories (with significant issues)
pytest -m unit                     # 12/32 passing - authentication errors (403)
pytest -m integration              # 1/27 passing - authentication errors (403)
pytest -m "not slow"               # Skip slow tests

# Specific modules with issues
pytest tests/unit/                 # Most fail: authentication errors (403)
pytest tests/integration/           # All fail: authentication errors (403)
```

## Actual Test Structure

### 1. Test Configuration (`tests/conftest.py`)
- **api_client**: Django test client for API testing
- **test_user**: Creates authenticated test user
- **authenticated_client**: Pre-authenticated test client
- **test_problem**: Creates problem with test cases
- **test_problem_set**: Creates problem set with problems
- **test_course**: Creates test course
- **mock_openai**: Mocks OpenAI API calls

### 2. Test Factories (`tests/factories.py`)
- **ProblemFactory**: Creates problems with configurable test cases
- **ProblemSetFactory**: Creates problem sets with optional problems
- **CourseFactory**: Creates courses with instructor and problem sets
- **UserFactory**: Creates test users with counter to avoid duplicates
- **UserProgressFactory**: Creates/updates progress records
- **SubmissionFactory**: Creates test submissions with results
- **HintFactory**: Creates all three hint types (Variable Fade, Subgoal, Trace)
- **CourseEnrollmentFactory**: Enrolls users in courses

### 3. Test Markers (from `pytest.ini`)
- **slow**: Mark tests as slow (deselect with `-m "not slow"`)
- **integration**: Mark tests as integration tests
- **unit**: Mark tests as unit tests
- **django_db**: Mark tests that require database access

## Test Coverage

### Test Module Status

#### ✅ Fully Working
- `tests/test_setup.py` - Infrastructure validation (3/3 tests pass)

#### ⚠️ Partially Working  
- `tests/unit/test_progress_tracking.py` - Business logic works, course isolation has issues (9/13 pass)
- `tests/unit/test_validation.py` - Service layer works, API endpoints blocked by auth (2/6 pass)

#### 🚫 Blocked by Authentication
- `tests/unit/test_hint_system.py` - All hint functionality tests (0/13 pass)
- `tests/integration/test_submission_pipeline.py` - Full submission workflow (0/20 pass)
- `tests/integration/test_full_workflow.py` - End-to-end scenarios (1/6 pass)
- `tests/integration/test_rate_limiting.py` - Rate limiting functionality (0/4 pass)

### Planned Test Modules (Referenced in Documentation)

#### Submission Pipeline (`tests/integration/test_submission_pipeline.py`)
**Input Validation (TestSubmissionInputValidation)**
- `test_code_size_validation`: 50KB limit enforcement
- `test_prompt_length_validation`: 10-2000 character limits
- `test_script_injection_prevention`: Security validation
- `test_missing_required_fields`: Required field validation

**Authorization (TestSubmissionAuthorization)**
- `test_course_enrollment_required`: Course enrollment validation
- `test_problem_set_membership_validation`: Problem set access
- `test_course_problem_set_validation`: Course-problem set linking

**Code Execution (TestCodeExecution)**
- `test_successful_execution`: Normal execution flow
- `test_partial_success`: Partial test case success
- `test_execution_timeout`: Timeout handling
- `test_syntax_error_handling`: Error handling

**Scoring and Results (TestScoringAndResults)**
- `test_score_calculation`: Score calculation (passed/total * 100)
- `test_hidden_test_case_filtering`: Hidden test filtering
- `test_progress_update_on_submission`: Progress tracking

**EiPL Submissions (TestEiPLSubmission)**
- `test_successful_eipl_submission`: AI generation mocking
- `test_ai_timeout_handling`: Timeout scenarios

#### Hint System (`tests/unit/test_hint_system.py`)
**Availability (TestHintAvailability)**
- `test_hints_locked_with_insufficient_attempts`: Attempt-based gating
- `test_hints_unlocked_with_sufficient_attempts`: Unlock logic
- `test_disabled_hints_not_shown`: Disabled hint filtering
- `test_no_progress_shows_zero_attempts`: No progress handling

**Hint Types (TestHintTypes)**
- `test_variable_fade_hint_content`: Variable Fade structure
- `test_subgoal_highlight_hint_content`: Subgoal Highlighting structure
- `test_suggested_trace_hint_content`: Suggested Trace structure
- `test_locked_hint_access_denied`: Access control
- `test_invalid_hint_type`: Error handling

**Course Context (TestHintCourseContext)**
- `test_hint_availability_with_course_context`: Course-specific hints
- `test_hint_access_requires_course_enrollment`: Enrollment requirements
- `test_hint_without_course_context`: Non-course hints

#### Progress Tracking (`tests/unit/test_progress_tracking.py`)
**Creation and Updates (TestUserProgressCreation)**
- `test_progress_created_on_first_submission`: Automatic creation
- `test_progress_updated_on_subsequent_submissions`: Update logic
- `test_progress_completion_status`: Completion tracking
- `test_time_tracking`: Time spent tracking

**Best Score Logic (TestBestScoreTracking)**
- `test_best_score_never_decreases`: Score never decreases
- `test_best_score_updates_on_improvement`: Improvement tracking
- `test_zero_score_handling`: Zero score edge cases

**Course Isolation (TestCourseIsolation)**
- `test_separate_progress_per_course`: Course isolation
- `test_progress_without_course_context`: Non-course progress
- `test_course_progress_aggregation`: Aggregation logic

#### Integration Workflows (`tests/integration/test_full_workflow.py`)
**Complete Workflows (TestCompleteSubmissionFlow)**
- `test_first_submission_workflow`: End-to-end first submission
- `test_multiple_submission_workflow`: Multi-submission flow

**EiPL Workflow (TestEiPLWorkflow)**
- `test_eipl_submission_to_progress`: EiPL to progress integration

**Cross-Course (TestCrossCourseWorkflow)**
- `test_independent_progress_per_course`: Course isolation

**Error Scenarios (TestErrorScenarios)**
- `test_invalid_problem_workflow`: Invalid problem handling
- `test_execution_failure_workflow`: Execution failures
- `test_unauthorized_course_access`: Authorization failures

## Running Tests

### Environment Setup Required
```bash
# ALWAYS required before running tests
source env/bin/activate
export DJANGO_SETTINGS_MODULE=purplex.settings
```

### Test Commands

#### Working Commands
```bash
# Run basic infrastructure tests (✅ All pass)
pytest tests/test_setup.py

# Run progress tracking tests (⚠️ Partial - 9/13 pass)  
pytest tests/unit/test_progress_tracking.py

# Run service layer validation tests (⚠️ Partial - 2/6 pass)
pytest tests/unit/test_validation.py
```

#### Currently Failing Commands (Authentication Issues)
```bash
# These fail with 403 errors due to missing auth mocking:
pytest -m unit                     # 12/32 passing
pytest -m integration              # 1/27 passing 
pytest tests/unit/test_hint_system.py          # 0/13 passing
pytest tests/integration/test_submission_pipeline.py  # 0/20 passing
pytest tests/integration/test_full_workflow.py         # 1/6 passing
pytest tests/integration/test_rate_limiting.py         # 0/4 passing
```

#### Diagnostic Commands
```bash
# Run with verbose output to see failure details
pytest tests/unit/ -v --tb=short

# Run specific failing test to debug
pytest tests/unit/test_hint_system.py::TestHintAvailability::test_hints_locked_with_insufficient_attempts -v

# Run with coverage (when tests are fixed)
pytest tests/ --cov=purplex --cov-report=html
```

## Key Testing Principles

1. **Isolation**: All external services are mocked
2. **Deterministic**: Fixed test data ensures reproducible results
3. **Comprehensive**: Tests cover happy paths and error cases
4. **Fast**: No actual code execution or AI calls
5. **Maintainable**: Factories and helpers reduce duplication

## Known Issues and Workarounds

### Authentication Issues (Primary Problem)
**Status**: 🚫 BLOCKING - Most tests fail with 403 errors
**Issue**: Tests expect validation errors (400) but get authentication errors (403) first
**Root Cause**: Firebase token authentication required for most endpoints, but tests don't properly mock authentication

**Workaround for Individual Tests**:
```python
# Add to test setup for API tests
@patch('purplex.users_app.services.authentication_service.AuthenticationService.authenticate_token')
def test_with_mocked_auth(self, mock_auth):
    test_user = User.objects.create_user('testuser')
    mock_auth.return_value = (test_user, {'uid': 'test-user-123'})
    # Test code here
```

### Database Constraint Issues
**Status**: ⚠️ WARNING - Some tests fail with IntegrityError
**Issue**: Duplicate key violations for username fields (e.g., 'instructor')
**Cause**: Test isolation problems in factories

### Missing/Outdated References
**Status**: ℹ️ INFO - Documentation and tests reference non-existent modules
**Issue**: Tests and documentation reference outdated imports:
- References to `generate_eipl_variations` function (current tests still use this)
- Documentation referenced files that don't exist:
  - `tests/integration/test_eipl_pipeline.py` (doesn't exist)
  - `tests/unit/test_task_execution.py` (doesn't exist) 
  - `tests/test_eipl_pipeline_integration.py` (doesn't exist)

**Current Status**: Tests use mocked `generate_eipl_variations` but actual implementation may have changed to use the new pipeline architecture in `purplex.problems_app.tasks.pipeline.execute_eipl_pipeline`

## Celery Task Testing with Current Architecture

### Current Pipeline Architecture: `execute_eipl_pipeline`
**Status**: ✅ Available but not properly tested
```python
# Current working task in pipeline.py
from purplex.problems_app.tasks.pipeline import execute_eipl_pipeline

# Example test pattern (needs auth mocking):
@patch('purplex.problems_app.tasks.pipeline.some_dependency')
@patch('purplex.users_app.services.authentication_service.AuthenticationService.authenticate_token')
def test_eipl_pipeline_execution(self, mock_auth, mock_dependency):
    # Mock authentication first
    test_user = User.objects.create_user('testuser')
    mock_auth.return_value = (test_user, {'uid': 'test-user-123'})
    
    result = execute_eipl_pipeline.apply_async(
        args=[prompt, problem_id, user_id],
        kwargs={'request_id': 'test-123'}
    )
    task_result = result.get(timeout=30)
    self.assertTrue(task_result['success'])
```

**Note**: Current tests reference `generate_eipl_variations` which may be outdated. New tests should target the actual pipeline implementation.

## SSE Testing Patterns

### Testing SSE Views
```python
# Test SSE endpoint from sse.py
from purplex.problems_app.views.sse import CleanTaskSSEView

def test_sse_stream_response(self):
    factory = RequestFactory()
    request = factory.get('/api/tasks/test-123/stream/?token=mock-token')
    
    view = CleanTaskSSEView()
    response = view.get(request, task_id='test-123')
    
    self.assertIsInstance(response, StreamingHttpResponse)
```

### Testing Redis Pub/Sub
```python
def test_task_progress_events(self):
    # Test that pipeline publishes progress events
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    pubsub = redis_client.pubsub()
    pubsub.subscribe('task:test-123')
    
    # Trigger task
    execute_eipl_pipeline.apply_async(
        args=[prompt, problem_id, user_id],
        task_id='test-123'
    )
    
    # Check for events
    message = pubsub.get_message(timeout=5)
    self.assertIsNotNone(message)
```

## Firebase Mock Testing

### Using Mock Firebase in Development
```python
from purplex.users_app.authentication import PurplexAuthentication
from purplex.users_app.services.authentication_service import AuthenticationService

def test_mock_firebase_authentication(self):
    # In development, uses mock_firebase.py
    auth = PurplexAuthentication()
    
    # Mock token validation
    with patch.object(AuthenticationService, 'authenticate_token') as mock_auth:
        test_user = User.objects.create_user('testuser')
        mock_auth.return_value = (test_user, {'uid': 'test-user-123'})
        
        result = auth.authenticate(request)
        self.assertEqual(result[0], test_user)
```

## Test Database Configuration

### PostgreSQL Test Database (from pytest.ini)
```ini
[tool:pytest]
DJANGO_SETTINGS_MODULE = purplex.settings
env = 
    DATABASE_URL = postgresql://purplex_user:devpass@localhost:5432/test_purplex
```

## Adding New Tests

### Best Practices
1. **Use Django TestCase**: Inherit from `django.test.TestCase` for database tests
2. **Use pytest markers**: Mark tests appropriately (`@pytest.mark.django_db`, `@pytest.mark.unit`)
3. **Use factories**: Leverage existing factories in `tests/factories.py`
4. **Mock external services**: Use `@patch` for OpenAI, Firebase, Docker execution
5. **Follow naming**: Use descriptive test method names starting with `test_`

### Example New Test
```python
@pytest.mark.django_db
class TestNewFeature(TestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        
    def test_new_functionality(self):
        # Test implementation
        pass
```

## Current Test Status

### ✅ Working Tests (Fully Passing)
- `tests/test_setup.py` - 3/3 passing (basic infrastructure)

### ⚠️ Partially Working Tests 
- `tests/unit/test_progress_tracking.py` - 9/13 passing (progress logic works, course isolation fails)
- `tests/unit/test_validation.py` - 2/6 passing (service layer works, API validation fails with 403)

### 🚫 Failing Tests (Authentication Blocking)
- `tests/unit/test_hint_system.py` - 0/13 passing (all fail with 403 or missing auth context)
- `tests/integration/test_submission_pipeline.py` - 0/20 passing (all fail with 403)
- `tests/integration/test_full_workflow.py` - 1/6 passing (only unauthorized access test passes)
- `tests/integration/test_rate_limiting.py` - 0/4 passing (all fail with 403)

### Root Cause Analysis
**Primary Issue**: Authentication system not properly mocked in test fixtures
- Most API endpoints require Firebase authentication
- Tests written expecting validation errors (400) but get auth errors (403) first  
- Need systematic auth mocking in `conftest.py` or test base classes

### Immediate Fixes Required
1. **Update `tests/conftest.py`**: Add global auth mocking for `authenticated_client` fixture
2. **Fix factory uniqueness**: Ensure test users have unique usernames to prevent IntegrityError
3. **Update test assertions**: Change expected status codes from 400 to 403 where auth fails first
4. **Add auth bypass option**: Create fixtures for testing validation logic without auth

### Test Infrastructure Status
- **Factories**: ✅ Working (in `tests/factories.py`) 
- **Fixtures**: 🚫 BROKEN (missing auth mocking in `tests/conftest.py`)
- **Markers**: ✅ Working (pytest.ini configured correctly)
- **Database**: ✅ Working (PostgreSQL test DB configured)
- **Mocks**: ⚠️ Incomplete (OpenAI mocked, Firebase authentication not mocked)

## Key Testing Patterns

### Service Layer Testing
```python
from purplex.problems_app.services.hint_service import HintService

def test_hint_service_logic(self):
    service = HintService()
    result = service.get_available_hints(user, problem, attempts=5)
    self.assertGreater(len(result), 0)
```

### Async Task Testing
```python
@patch('purplex.problems_app.tasks.pipeline.openai_client')
def test_pipeline_with_mocked_ai(self, mock_openai):
    mock_openai.return_value = {'success': True, 'code': 'def solve(): pass'}
    
    result = execute_eipl_pipeline.apply_async(
        args=['test prompt', 1, 1]
    ).get(timeout=10)
    
    self.assertTrue(result['success'])
```