# Comprehensive Testing Framework for Purplex

## Overview
This testing framework provides comprehensive coverage for the submission pipeline, hint system, and progress tracking functionality. It focuses on capturing the complete dataflow from user input through validation, execution, scoring, and progress updates.

## Test Structure

### 1. Mock Services (`tests/mocks.py`)
- **MockCodeExecutionService**: Simulates code execution without Docker
  - Configurable behaviors: success, partial_success, timeout, syntax_error
  - Tracks calls for verification
- **MockAsyncAIService**: Simulates AI operations
  - Mocks EiPL code generation and testing
  - Configurable timeout behavior
- **MockOpenAIClient**: Mocks OpenAI API calls
- **MockFirebaseAuth**: Mocks Firebase authentication

### 2. Test Factories (`tests/factories.py`)
- **ProblemFactory**: Creates problems with test cases
- **ProblemSetFactory**: Creates problem sets
- **CourseFactory**: Creates courses with enrollments
- **UserFactory**: Creates test users
- **UserProgressFactory**: Creates progress records
- **SubmissionFactory**: Creates submissions
- **HintFactory**: Creates all hint types
- **CourseEnrollmentFactory**: Enrolls users in courses

### 3. Assertion Helpers (`tests/helpers.py`)
- **SubmissionAssertions**: Validates submission response formats
- **ProgressAssertions**: Validates progress updates
- **HintAssertions**: Validates hint availability and content
- **TestDataHelpers**: Creates consistent test payloads

## Test Coverage

### Submission Pipeline Tests (`tests/integration/test_submission_pipeline.py`)
#### Input Validation
- Code size limits (50KB)
- Prompt length validation (10-2000 chars)
- Script injection prevention
- Missing required fields

#### Authorization
- Course enrollment validation
- Problem set membership
- Course-problem set association

#### Code Execution
- Successful execution flow
- Partial test success
- Timeout handling
- Syntax error handling

#### Scoring and Results
- Score calculation (passed/total * 100)
- Hidden test case filtering
- Progress update verification

#### EiPL Submissions
- AI generation mocking
- Variation testing
- Timeout handling

### Hint System Tests (`tests/unit/test_hint_system.py`)
#### Availability
- Attempt-based unlocking
- Disabled hints filtering
- No progress handling

#### Hint Types
- Variable Fade content structure
- Subgoal Highlighting content structure
- Suggested Trace content structure
- Locked hint access prevention

#### Course Context
- Course-specific hint availability
- Enrollment requirements
- Hints without course context

### Progress Tracking Tests (`tests/unit/test_progress_tracking.py`)
#### Creation and Updates
- Automatic creation on first submission
- Subsequent submission updates
- Completion status tracking
- Time tracking

#### Best Score Logic
- Score never decreases
- Updates on improvement
- Zero score handling

#### Course Isolation
- Separate progress per course
- Progress without course context
- Course progress aggregation

#### Edge Cases
- Concurrent submission handling
- Deletion protection
- Problem set changes

### Integration Tests (`tests/integration/test_full_workflow.py`)
#### Complete Workflows
- First submission flow
- Multiple submissions to hint unlock
- EiPL submission flow
- Cross-course workflows

#### Error Scenarios
- Invalid problem handling
- Execution failure workflow
- Unauthorized access

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test module
pytest tests/unit/test_hint_system.py

# Run with coverage
pytest tests/ --cov=purplex --cov-report=html

# Run integration tests only
pytest tests/integration/

# Run with verbose output
pytest tests/ -v
```

## Key Testing Principles

1. **Isolation**: All external services are mocked
2. **Deterministic**: Fixed test data ensures reproducible results
3. **Comprehensive**: Tests cover happy paths and error cases
4. **Fast**: No actual code execution or AI calls
5. **Maintainable**: Factories and helpers reduce duplication

## Dataflow Testing

The framework captures the complete dataflow:

```
User Input
    ↓
Input Validation (size, content, sanitization)
    ↓
Authorization (course enrollment, problem access)
    ↓
Code Execution (mocked Docker container)
    ↓
Test Case Evaluation (visible vs hidden)
    ↓
Score Calculation
    ↓
Progress Update (attempts, best score, completion)
    ↓
Response Formatting
    ↓
Hint Availability Update
```

## Adding New Tests

1. Use existing factories for test data
2. Mock external services appropriately
3. Use assertion helpers for validation
4. Follow the pattern of existing tests
5. Group related tests in classes

## Future Enhancements

1. **Performance Tests**: Add tests for N+1 queries and response times
2. **Load Tests**: Test concurrent submissions
3. **Security Tests**: Expand injection prevention tests
4. **E2E Tests**: Add Playwright for frontend testing
5. **Metrics**: Track test execution time and flakiness