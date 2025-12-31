# New Problem Type Implementation Guide

Step-by-step instructions for implementing new problem types in Purplex. Covers backend handlers, polymorphic models, frontend components, and testing.

---

## Table of Contents

1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [Testing](#testing)
6. [Problem Type Specifications](#problem-type-specifications)
7. [Checklist](#checklist)

---

## Overview

Problem types in Purplex follow a **polymorphic model + handler** architecture:

- **Polymorphic Model**: Django model inheriting from `Problem` base class via django-polymorphic
- **Handler**: Backend class implementing `ActivityHandler` ABC - handles validation, grading, submission execution
- **Input Component**: Vue component for user input
- **Feedback Component**: Vue component for displaying results

### Model Hierarchy

```
Problem (PolymorphicModel base)
├── StaticProblem (abstract) - no code execution
│   ├── McqProblem
│   └── RefuteProblem
├── SpecProblem (abstract) - NL -> LLM -> code -> test
│   ├── EiplProblem
│   ├── PromptProblem
│   ├── DebugFixProblem
│   ├── ProbeableCodeProblem
│   └── ProbeableSpecProblem
└── (Future) CodeProblem (abstract) - student code -> execute
```

### Existing Types

| Type | Description | Handler | Model |
|------|-------------|---------|-------|
| `eipl` | Explain in Plain Language | `EiPLHandler` | `EiplProblem` |
| `mcq` | Multiple Choice Question | `McqHandler` | `McqProblem` |
| `prompt` | Image-based EiPL variant | `PromptHandler` | `PromptProblem` |
| `refute` | Counter-example finding | `RefuteHandler` | `RefuteProblem` |
| `debug_fix` | Fix buggy code | `DebugFixHandler` | `DebugFixProblem` |
| `probeable_code` | Oracle queries + code writing | `ProbeableCodeHandler` | `ProbeableCodeProblem` |
| `probeable_spec` | Oracle queries + spec writing | `ProbeableSpecHandler` | `ProbeableSpecProblem` |

### Planned Types

| Type | Description | Complexity |
|------|-------------|------------|
| `func_redef` | Write spec, LLM generates code | Medium - new LLM pipeline |
| `debug_explain` | Identify and explain bug | Medium - line selection UI |

---

## Directory Structure

```
purplex/
├── problems_app/
│   ├── handlers/
│   │   ├── __init__.py              # Handler registry (MODIFY - add import)
│   │   ├── base.py                  # ActivityHandler ABC (READ-ONLY)
│   │   ├── eipl/
│   │   │   ├── __init__.py
│   │   │   └── handler.py           # Reference implementation (async)
│   │   ├── refute/
│   │   │   ├── __init__.py
│   │   │   └── handler.py           # Reference implementation (sync)
│   │   └── {new_type}/              # CREATE
│   │       ├── __init__.py
│   │       └── handler.py
│   ├── models/                      # Polymorphic model hierarchy
│   │   ├── __init__.py              # Re-exports all models
│   │   ├── base.py                  # Problem base class (PolymorphicModel)
│   │   ├── static.py                # StaticProblem, McqProblem, RefuteProblem
│   │   ├── spec.py                  # SpecProblem, EiplProblem, PromptProblem, etc.
│   │   └── {new_type}.py            # CREATE if needed (or add to existing)
│   ├── tasks/
│   │   └── pipeline.py              # Add pipeline task (for async types only)
│   └── views/
│       └── submission_views.py      # Uses handler.submit() - no changes needed
├── submissions/
│   └── models.py                    # Submission model (usually no changes needed)
└── client/
    └── src/
        └── components/
            └── activities/
                ├── index.ts                 # Component registry (MODIFY)
                ├── types.ts                 # TypeScript types (MAY EXTEND)
                ├── inputs/
                │   ├── EiplInput.vue        # Reference input component
                │   ├── RefuteInput.vue      # Reference input component (JSON input)
                │   ├── {NewType}Input.vue   # CREATE
                │   └── shared/              # Shared composables
                │       └── useProbeState.ts # Probe state management (for probeable types)
                └── feedback/
                    ├── EiplFeedback.vue     # Reference feedback component
                    └── {NewType}Feedback.vue # CREATE or reuse existing
```

---

## Backend Implementation

### Step 1: Create Polymorphic Model Class

Problem types use django-polymorphic for true polymorphic queries. Choose the appropriate abstract base class:

- **StaticProblem**: No code execution (MCQ, Refute)
- **SpecProblem**: NL -> LLM -> code -> test (EiPL, Prompt, DebugFix, Probeable)

**File**: `purplex/problems_app/models/spec.py` (or `static.py` for static types)

```python
"""
{TypeName} problem type.
"""

from django.core.exceptions import ValidationError
from django.db import models

from .base import Problem  # or from .spec import SpecProblem


class {TypeName}Problem(SpecProblem):  # or StaticProblem
    """
    {TypeName} problem type.

    Description of what this problem type does.
    """

    # Set to False if segmentation analysis is not needed
    SEGMENTATION_DEFAULT_ENABLED = False

    # Type-specific fields (not JSONField - use proper Django fields)
    custom_field = models.TextField(
        help_text="Description of this field"
    )
    another_field = models.JSONField(
        default=list,
        blank=True,
        help_text="Configuration options as JSON"
    )

    class Meta:
        app_label = "problems_app"
        verbose_name = "{Type Display Name}"
        verbose_name_plural = "{Type Display Name} Problems"

    @property
    def polymorphic_type(self) -> str:
        """Return type identifier for handler lookup."""
        return "{type_name}"

    def clean(self):
        """Validate type-specific fields."""
        super().clean()
        if not self.custom_field:
            raise ValidationError({"custom_field": "Required for this problem type"})

    def __str__(self):
        return f"[{TypeName}] {self.title}"
```

### Step 2: Export Model in `__init__.py`

**File**: `purplex/problems_app/models/__init__.py`

```python
# Add import
from .spec import {TypeName}Problem  # or from .static import ...

# Add to __all__
__all__ = [
    # ... existing exports ...
    "{TypeName}Problem",
]
```

### Step 3: Create Handler Module

**File**: `purplex/problems_app/handlers/{type_name}/__init__.py`

```python
"""Handler module for {TypeName} problems."""
from .handler import {TypeName}Handler  # noqa: F401
```

**File**: `purplex/problems_app/handlers/{type_name}/handler.py`

```python
"""
Handler for {TypeName} activity type.

{TypeName} problems [description of what this type does].
"""

import logging
from typing import TYPE_CHECKING, Any

from .. import register_handler
from ..base import (
    ActivityHandler,
    ProcessingResult,
    SubmissionOutcome,
    ValidationResult,
)

if TYPE_CHECKING:
    from purplex.problems_app.models import {TypeName}Problem
    from purplex.submissions.models import Submission

logger = logging.getLogger(__name__)


@register_handler("{type_name}")
class {TypeName}Handler(ActivityHandler):
    """Handler for {TypeName} problems."""

    # Validation constants - adjust per type
    MIN_INPUT_LENGTH = 10
    MAX_INPUT_LENGTH = 1000

    @property
    def type_name(self) -> str:
        return "{type_name}"

    # ─── Input Validation ───────────────────────────────────────

    def validate_input(self, raw_input: str, problem: "{TypeName}Problem") -> ValidationResult:
        """Validate {type_name} input."""
        text = raw_input.strip()

        if len(text) < self.MIN_INPUT_LENGTH:
            return ValidationResult(
                is_valid=False,
                error=f"Input must be at least {self.MIN_INPUT_LENGTH} characters",
            )

        if len(text) > self.MAX_INPUT_LENGTH:
            return ValidationResult(
                is_valid=False,
                error=f"Input must be under {self.MAX_INPUT_LENGTH} characters",
            )

        return ValidationResult(is_valid=True)

    # ─── Submission Processing ──────────────────────────────────

    def process_submission(
        self, submission: "Submission", raw_input: str, problem: "{TypeName}Problem"
    ) -> ProcessingResult:
        """
        Process {type_name} submission.

        Note: For async types, this is handled by a Celery pipeline task.
        For sync types, implement the processing logic here.
        """
        raise NotImplementedError(
            "{TypeName} uses submit() for processing. "
            "See EiPLHandler (async) or RefuteHandler (sync) for examples."
        )

    # ─── Grading ────────────────────────────────────────────────

    def calculate_grade(self, submission: "Submission") -> str:
        """
        Calculate grade for {type_name} submission.

        Returns: 'complete', 'partial', or 'incomplete'
        """
        if not submission.passed_all_tests:
            return "incomplete"

        # Add type-specific grading logic here
        return "complete"

    def is_correct(self, submission: "Submission") -> bool:
        """Check if submission is correct."""
        return submission.passed_all_tests

    # ─── Completion Evaluation ──────────────────────────────────

    def evaluate_completion(
        self, submission: "Submission", problem: "{TypeName}Problem"
    ) -> str:
        """
        Evaluate completion status for progress tracking.

        Returns: 'complete', 'partial', or 'incomplete'
        """
        if submission.score < 100:
            return "incomplete"

        return "complete"

    # ─── Data Extraction ────────────────────────────────────────

    def extract_variations(self, submission: "Submission") -> list[str]:
        """Extract code variations from submission."""
        if hasattr(submission, "code_variations") and submission.code_variations.exists():
            return [v.generated_code for v in submission.code_variations.all()]
        return [submission.processed_code] if submission.processed_code else []

    def extract_test_results(
        self, submission: "Submission", problem: "{TypeName}Problem"
    ) -> list[dict[str, Any]]:
        """Extract test results in frontend format."""
        results = []
        for te in submission.test_executions.all().order_by("execution_order"):
            results.append({
                "isSuccessful": te.passed,
                "function_call": self._format_function_call(
                    problem.function_name, te.input_values
                ),
                "expected_output": te.expected_output,
                "actual_output": te.actual_output,
                "error": te.error_message,
            })
        return results

    def count_variations(self, submission: "Submission") -> int:
        """Count total variations."""
        if hasattr(submission, "code_variations"):
            return submission.code_variations.count()
        return 1

    def count_passing_variations(self, submission: "Submission") -> int:
        """Count passing variations."""
        if hasattr(submission, "code_variations"):
            from django.db import models

            return submission.code_variations.filter(
                tests_passed=models.F("tests_total"), tests_total__gt=0
            ).count()
        return 1 if submission.passed_all_tests else 0

    # ─── API Configuration ──────────────────────────────────────

    def get_problem_config(self, problem: "{TypeName}Problem") -> dict[str, Any]:
        """Return configuration for frontend rendering."""
        return {
            "display": {
                "show_reference_code": True,
                "code_read_only": True,
                "show_function_signature": True,
            },
            "input": {
                "type": "textarea",  # or 'code', 'json', 'radio', etc.
                "label": "Your answer",
                "placeholder": "Enter your response...",
                "min_length": self.MIN_INPUT_LENGTH,
                "max_length": self.MAX_INPUT_LENGTH,
            },
            "hints": {
                "available": [],
                "enabled": False,
            },
            "feedback": {
                "show_variations": False,
                "show_segmentation": False,
                "show_test_results": True,
            },
        }

    def serialize_result(self, submission: "Submission") -> dict[str, Any]:
        """Serialize submission result for API response."""
        return {
            "score": submission.score,
            "is_correct": submission.passed_all_tests,
            "test_results": self.extract_test_results(submission, submission.problem),
        }

    def get_admin_config(self) -> dict[str, Any]:
        """Return configuration for admin UI."""
        return {
            "hidden_sections": ["mcq_options"],
            "required_fields": ["title", "description"],
            "optional_fields": ["tags", "categories"],
            "type_specific_section": None,
            "supports": {
                "hints": False,
                "segmentation": False,
                "test_cases": True,
            },
        }

    # ─── Submission Execution ─────────────────────────────────────

    def submit(
        self,
        submission: "Submission",
        raw_input: str,
        problem: "{TypeName}Problem",
        context: dict[str, Any],
    ) -> SubmissionOutcome:
        """
        Execute the full submission lifecycle for this activity type.

        Choose ONE of the following patterns:

        SYNCHRONOUS (like RefuteHandler, McqHandler):
        - Process inline, update submission, return complete=True
        - Good for: simple grading, no LLM/Docker needed

        ASYNCHRONOUS (like EiPLHandler, PromptHandler):
        - Queue a Celery task, return complete=False with task_id
        - Good for: LLM calls, Docker execution, long-running tasks
        """
        # Example: Synchronous execution
        # Process the submission inline
        is_correct = False  # Replace with actual check
        score = 100 if is_correct else 0

        # Update submission
        submission.processed_code = raw_input
        submission.score = score
        submission.passed_all_tests = is_correct
        submission.is_correct = is_correct
        submission.completion_status = "complete" if is_correct else "incomplete"
        submission.execution_status = "completed"
        submission.save()

        # Update progress
        from purplex.problems_app.services.progress_service import ProgressService
        ProgressService.process_submission(submission)

        # Build result data
        result_data = {
            "submission_id": str(submission.submission_id),
            "problem_type": "{type_name}",
            "score": score,
            "is_correct": is_correct,
            "completion_status": submission.completion_status,
            "result": self.serialize_result(submission),
        }

        return SubmissionOutcome(
            complete=True, submission=submission, result_data=result_data
        )

        # Example: Asynchronous execution (uncomment to use)
        # from purplex.problems_app.tasks.pipeline import execute_{type_name}_pipeline
        #
        # task = execute_{type_name}_pipeline.apply_async(
        #     args=[problem.id, raw_input, context["user_id"],
        #           context.get("problem_set_id"), context.get("course_id")],
        #     task_id=context["request_id"],
        # )
        #
        # return SubmissionOutcome(
        #     complete=False, submission=submission, task_id=task.id
        # )
```

### Step 4: Register Handler Import

**File**: `purplex/problems_app/handlers/__init__.py`

Add import at the bottom (in the alphabetically sorted import block):

```python
from . import (  # noqa: E402
    debug_fix,
    eipl,
    mcq,
    probeable_code,
    probeable_spec,
    prompt,
    refute,
    {type_name},  # ADD
)
```

---

## Pipeline Task (Async Types Only)

If your problem type requires asynchronous processing (LLM calls, Docker execution), create a Celery pipeline task.

**File**: `purplex/problems_app/tasks/pipeline.py`

```python
# ─────────────────────────────────────────────────────────────────────────────
# {TypeName} Pipeline (for async types only)
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, name="pipeline.execute_{type_name}")
def execute_{type_name}_pipeline(
    self,
    problem_id: int,
    raw_input: str,
    user_id: int,
    problem_set_id: int | None = None,
    course_id: int | None = None,
) -> dict[str, Any]:
    """
    Execute {TypeName} submission pipeline.

    Called by handler.submit() for async processing.

    Args:
        problem_id: The Problem primary key
        raw_input: User's submission input
        user_id: The User primary key
        problem_set_id: Optional ProblemSet primary key
        course_id: Optional Course primary key
    """
    task_id = self.request.id
    logger.info(
        f"[{type_name.upper()}] Pipeline start: task_id={task_id}, problem_id={problem_id}"
    )

    try:
        # Load entities
        publish_progress(task_id, 10, "Loading problem...")
        problem = Problem.objects.get(pk=problem_id)
        user = User.objects.get(pk=user_id)
        submission = Submission.objects.get(celery_task_id=task_id)

        # Type-specific processing
        publish_progress(task_id, 30, "Processing submission...")

        # TODO: Add type-specific logic here
        # Examples from existing pipelines:
        # - EiPL: generate code variations via LLM, run in Docker
        # - DebugFix: execute student code in Docker against test cases

        is_correct = False  # Replace with actual check
        score = 100 if is_correct else 0

        # Update submission
        publish_progress(task_id, 80, "Saving results...")

        submission.processed_code = raw_input
        submission.score = score
        submission.passed_all_tests = is_correct
        submission.completion_status = "complete" if is_correct else "incomplete"
        submission.execution_status = "completed"
        submission.save()

        # Update progress tracking
        from purplex.problems_app.services.progress_service import ProgressService
        ProgressService.process_submission(submission)

        # Build result for SSE streaming
        publish_progress(task_id, 100, f"Complete! Score: {score}%")

        from purplex.problems_app.handlers import get_handler
        handler = get_handler("{type_name}")

        result = {
            "submission_id": str(submission.submission_id),
            "problem_type": "{type_name}",
            "score": score,
            "is_correct": is_correct,
            "completion_status": submission.completion_status,
            "result": handler.serialize_result(submission),
        }

        publish_completion(task_id, result)
        return result

    except Exception as e:
        logger.error(f"[{type_name.upper()}] Pipeline failed: {e}", exc_info=True)
        publish_error(task_id, str(e))
        raise
```

**Note**: The submission view (`ActivitySubmissionView`) uses `handler.submit()` directly - there is no `PIPELINE_TASKS` registry to update. Your handler's `submit()` method is responsible for calling the Celery task.

---

## Frontend Implementation

### Step 5: Create Input Component

**File**: `purplex/client/src/components/activities/inputs/{TypeName}Input.vue`

```vue
<template>
  <div class="{type-name}-input">
    <!-- Type-specific display area -->
    <div class="problem-display">
      <!-- Example: Code viewer for EiPL-like -->
      <CodeViewer
        v-if="displayConfig?.show_reference_code"
        :code="problem.reference_solution"
        :readonly="true"
      />

      <!-- Example: Image viewer for Prompt -->
      <img
        v-if="displayConfig?.show_image"
        :src="problem.prompt_config?.image_url"
        :alt="problem.prompt_config?.image_alt_text || 'Problem image'"
        class="problem-image"
      />
    </div>

    <!-- Input area -->
    <div class="input-area">
      <!-- Text input (EiPL, Prompt, Debug Explain, Func Redef) -->
      <textarea
        v-if="inputConfig?.type === 'textarea'"
        v-model="localValue"
        :placeholder="inputConfig?.placeholder || 'Enter your response...'"
        :disabled="disabled"
        :maxlength="inputConfig?.max_length"
        @input="handleInput"
        class="explanation-textarea"
      />

      <!-- MCQ radio buttons -->
      <div v-else-if="inputConfig?.type === 'radio'" class="mcq-options">
        <label
          v-for="option in inputConfig?.options"
          :key="option.id"
          class="mcq-option"
        >
          <input
            type="radio"
            :value="option.id"
            v-model="localValue"
            :disabled="disabled"
            @change="handleInput"
          />
          <span>{{ option.text }}</span>
        </label>
      </div>

      <!-- Character count for text inputs -->
      <div v-if="inputConfig?.type === 'textarea'" class="char-count">
        {{ localValue.length }} / {{ inputConfig?.max_length || 1000 }}
      </div>
    </div>

    <!-- Submit button -->
    <button
      class="submit-btn"
      :disabled="!isValid || disabled"
      @click="handleSubmit"
    >
      Submit
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { ActivityInputProps } from '../types'

const props = defineProps<ActivityInputProps>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'submit'): void
}>()

// Local state
const localValue = ref(props.modelValue || '')

// Config shortcuts
const displayConfig = computed(() => props.problem.display_config)
const inputConfig = computed(() => props.problem.input_config)

// Validation
const isValid = computed(() => {
  const minLen = inputConfig.value?.min_length || 0
  const maxLen = inputConfig.value?.max_length || Infinity
  return localValue.value.length >= minLen && localValue.value.length <= maxLen
})

// Handlers
function handleInput() {
  emit('update:modelValue', localValue.value)
}

function handleSubmit() {
  if (isValid.value) {
    emit('submit')
  }
}

// Sync with parent
watch(() => props.modelValue, (newVal) => {
  if (newVal !== localValue.value) {
    localValue.value = newVal
  }
})
</script>

<style scoped>
.{type-name}-input {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.explanation-textarea {
  width: 100%;
  min-height: 150px;
  padding: 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-family: inherit;
  resize: vertical;
}

.char-count {
  text-align: right;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.submit-btn {
  align-self: flex-end;
  padding: 0.5rem 1.5rem;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
```

### Step 6: Create Feedback Component

**Option A: Reuse existing feedback** (for types with similar feedback structure)

```vue
<template>
  <EiplFeedback v-bind="$props" />
</template>

<script setup lang="ts">
import EiplFeedback from './EiplFeedback.vue'
import type { ActivityFeedbackProps } from '../types'

defineProps<ActivityFeedbackProps>()
</script>
```

**Option B: Create custom feedback** - follow `EiplFeedback.vue` patterns.

### Step 7: Register Components

**File**: `purplex/client/src/components/activities/index.ts`

Add to `ACTIVITY_COMPONENTS`:

```typescript
const ACTIVITY_COMPONENTS: ActivityComponentRegistry = {
  eipl: {
    input: () => import('./inputs/EiplInput.vue'),
    feedback: () => import('./feedback/EiplFeedback.vue'),
  },
  mcq: {
    input: () => import('./inputs/McqInput.vue'),
    feedback: () => import('./feedback/McqFeedback.vue'),
  },
  prompt: {
    input: () => import('./inputs/PromptInput.vue'),
    feedback: () => import('./feedback/PromptFeedback.vue'),
  },
  refute: {
    input: () => import('./inputs/RefuteInput.vue'),
    feedback: () => import('./feedback/RefuteFeedback.vue'),
  },
  debug_fix: {
    input: () => import('./inputs/DebugFixInput.vue'),
    feedback: () => import('./feedback/DebugFixFeedback.vue'),
  },
  probeable_code: {
    input: () => import('./inputs/ProbeableCodeInput.vue'),
    feedback: () => import('./feedback/ProbeableCodeFeedback.vue'),
  },
  probeable_spec: {
    input: () => import('./inputs/ProbeableSpecInput.vue'),
    feedback: () => import('./feedback/ProbeableSpecFeedback.vue'),
  },
  // ADD new types
  {type_name}: {
    input: () => import('./inputs/{TypeName}Input.vue'),
    feedback: () => import('./feedback/{TypeName}Feedback.vue'),
  },
}
```

### Step 8: Extend Types (if needed)

**File**: `purplex/client/src/components/activities/types.ts`

The types module already defines common interfaces. Add type-specific interfaces only if needed:

```typescript
// Example: Custom result interface for your type
export interface {TypeName}Result {
  is_correct: boolean
  score: number
  // Add type-specific fields
}
```

Existing interfaces you can reuse:
- `ActivityInputProps` - props for input components
- `ActivityFeedbackProps` - props for feedback components
- `CodeResult` - code variation results
- `TestResultDisplay` - test execution results
- `ProbeConfig`, `ProbeStatus`, `ProbeHistoryEntry` - for probeable types

---

## Testing

### Step 9: Unit Tests for Handler

**File**: `tests/unit/handlers/test_{type_name}_handler.py`

```python
"""Tests for {TypeName} handler."""

import pytest
from unittest.mock import MagicMock

from purplex.problems_app.handlers import get_handler, is_registered
from purplex.problems_app.handlers.{type_name}.handler import {TypeName}Handler


class TestHandlerRegistration:
    """Test handler is properly registered."""

    def test_handler_is_registered(self):
        assert is_registered('{type_name}')

    def test_get_handler_returns_instance(self):
        handler = get_handler('{type_name}')
        assert isinstance(handler, {TypeName}Handler)

    def test_type_name_property(self):
        handler = get_handler('{type_name}')
        assert handler.type_name == '{type_name}'


class TestInputValidation:
    """Test input validation logic."""

    @pytest.fixture
    def handler(self):
        return {TypeName}Handler()

    @pytest.fixture
    def mock_problem(self):
        problem = MagicMock()
        problem.slug = 'test-problem'
        return problem

    def test_valid_input(self, handler, mock_problem):
        result = handler.validate_input('A' * 50, mock_problem)
        assert result.is_valid is True
        assert result.error is None

    def test_input_too_short(self, handler, mock_problem):
        result = handler.validate_input('short', mock_problem)
        assert result.is_valid is False
        assert 'at least' in result.error.lower()

    def test_input_too_long(self, handler, mock_problem):
        result = handler.validate_input('A' * 2000, mock_problem)
        assert result.is_valid is False
        assert 'under' in result.error.lower()

    def test_whitespace_only_fails(self, handler, mock_problem):
        result = handler.validate_input('   \n\t   ', mock_problem)
        assert result.is_valid is False


class TestGrading:
    """Test grading logic."""

    @pytest.fixture
    def handler(self):
        return {TypeName}Handler()

    def test_correct_submission_complete(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = True
        submission.score = 100

        grade = handler.calculate_grade(submission)
        assert grade == 'complete'

    def test_incorrect_submission_incomplete(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = False
        submission.score = 50

        grade = handler.calculate_grade(submission)
        assert grade == 'incomplete'


class TestProblemConfig:
    """Test problem configuration generation."""

    @pytest.fixture
    def handler(self):
        return {TypeName}Handler()

    @pytest.fixture
    def mock_problem(self):
        return MagicMock()

    def test_config_structure(self, handler, mock_problem):
        config = handler.get_problem_config(mock_problem)

        assert 'display' in config
        assert 'input' in config
        assert 'feedback' in config

    def test_input_config_has_required_fields(self, handler, mock_problem):
        config = handler.get_problem_config(mock_problem)

        assert 'type' in config['input']
        assert 'min_length' in config['input']
        assert 'max_length' in config['input']
```

### Step 10: Integration Tests (Optional for Async Types)

**File**: `tests/integration/test_{type_name}_pipeline.py`

```python
"""Integration tests for {TypeName} pipeline."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
class TestPipeline:
    """Test full pipeline execution."""

    @pytest.fixture
    def test_user(self):
        from django.contrib.auth.models import User
        return User.objects.create_user('testuser', 'test@test.com', 'password')

    @pytest.fixture
    def test_problem(self):
        from purplex.problems_app.models import Problem, ProblemSet
        problem_set = ProblemSet.objects.create(
            slug='test-set',
            title='Test Set'
        )
        problem = Problem.objects.create(
            slug='test-{type_name}',
            title='Test Problem',
            problem_type='{type_name}',
            function_name='test_func',
            reference_solution='def test_func(): pass'
        )
        problem_set.problems.add(problem)
        return problem, problem_set

    def test_pipeline_creates_submission(self, test_user, test_problem):
        """Test that pipeline creates a submission record."""
        from purplex.problems_app.tasks.pipeline import execute_{type_name}_pipeline

        problem, problem_set = test_problem

        result = execute_{type_name}_pipeline(
            problem_id=problem.id,
            raw_input='Test input ' * 5,
            user_id=test_user.id,
            problem_set_id=problem_set.id
        )

        assert 'submission_id' in result

        from purplex.submissions.models import Submission
        submission = Submission.objects.get(submission_id=result['submission_id'])
        assert submission.user == test_user
        assert submission.problem == problem

    def test_pipeline_idempotency(self, test_user, test_problem):
        """Test that duplicate task IDs don't create duplicate submissions."""
        from purplex.problems_app.tasks.pipeline import execute_{type_name}_pipeline

        problem, problem_set = test_problem

        with patch.object(execute_{type_name}_pipeline, 'request') as mock_request:
            mock_request.id = 'test-task-id-123'
            result1 = execute_{type_name}_pipeline(
                problem_id=problem.id,
                raw_input='Test input ' * 5,
                user_id=test_user.id,
                problem_set_id=problem_set.id
            )

        with patch.object(execute_{type_name}_pipeline, 'request') as mock_request:
            mock_request.id = 'test-task-id-123'
            result2 = execute_{type_name}_pipeline(
                problem_id=problem.id,
                raw_input='Different input ' * 5,
                user_id=test_user.id,
                problem_set_id=problem_set.id
            )

        assert result1['submission_id'] == result2['submission_id']
```

### Step 11: Generate Migration

```bash
python manage.py makemigrations problems_app -n add_{type_name}_type
python manage.py migrate
```

---

## Problem Type Specifications

### Debug Fix

**Purpose**: Student identifies and corrects a bug in provided code.

| Aspect | Specification |
|--------|---------------|
| **Display** | Code editor with buggy code (editable) |
| **Input** | Modified code |
| **Validation** | Code must be syntactically valid |
| **Pipeline** | Async - executes fixed code in Docker against test cases |
| **Grading** | Test pass rate |
| **Feedback** | Test results, expected vs actual output |

**Model**: `DebugFixProblem` (inherits from `SpecProblem`)

**Model fields**:
```python
buggy_code = models.TextField(
    help_text="Code with intentional bug(s) for student to fix"
)
bug_hints = models.JSONField(
    default=list, blank=True,
    help_text="Progressive hints: [{level: 1, text: 'Check line 5'}, ...]"
)
allow_complete_rewrite = models.BooleanField(
    default=True,
    help_text="If False, require minimal diff from buggy_code"
)
```

---

### Debug Explain

**Purpose**: Student identifies buggy line(s) and explains the error.

| Aspect | Specification |
|--------|---------------|
| **Display** | Code viewer with clickable line numbers (read-only) |
| **Input** | `line_select` + `text_explanation` |
| **Validation** | At least one line selected, explanation 20-500 chars |
| **Pipeline** | LLM evaluates line selection accuracy + explanation quality |
| **Grading** | Line accuracy + explanation quality (combined or separate) |
| **Feedback** | Highlight correct lines, show model explanation |

**Config fields** (`debug_config`):
```python
{
    'buggy_code': str,
    'buggy_lines': [int],        # Correct line numbers
    'bug_explanation': str,      # Reference explanation
    'error_message': str,        # Optional shown error
    'acceptable_line_range': int # How close is "close enough" (default: 0)
}
```

---

### Function Redefinition

**Purpose**: Student writes a specification that an LLM uses to generate correct code.

| Aspect | Specification |
|--------|---------------|
| **Display** | Problem description, function signature, example I/O (no code) |
| **Input** | `text_explanation` - detailed spec for LLM |
| **Validation** | Length 30-1500 chars |
| **Pipeline** | LLM generates code from spec, executes against test cases |
| **Grading** | Test pass rate of generated code |
| **Feedback** | Show generated code, test results, suggestions |

**Config fields** (`func_redef_config`):
```python
{
    'example_io': [{'input': '...', 'output': '...'}],
    'llm_prompt_template': str   # Optional custom prompt
}
```

---

### Refute

**Purpose**: Student finds input that disproves a false claim about a function.

| Aspect | Specification |
|--------|---------------|
| **Display** | Code viewer (reference_solution) + claim text |
| **Input** | JSON object with function arguments (e.g., `{"x": -5}`) |
| **Validation** | JSON must include all function parameters |
| **Pipeline** | Synchronous - executes in-process with restricted globals |
| **Grading** | Binary: claim disproven = complete, not disproven = incomplete |
| **Feedback** | Function result, whether claim was disproven |

**Model**: `RefuteProblem` (inherits from `StaticProblem`)

**Model fields**:
```python
claim_text = models.TextField(
    help_text="The false claim about the function"
)
claim_predicate = models.TextField(
    help_text="Python expression that's True when claim holds (e.g., 'result > 0')"
)
reference_solution = models.TextField(
    help_text="The actual function code to execute"
)
function_signature = models.TextField(
    help_text="Function signature for input parsing"
)
expected_counterexample = models.JSONField(
    default=dict, blank=True,
    help_text="Optional known counterexample for hints"
)
```

---

### Probeable Code

**Purpose**: Student discovers function behavior by querying an oracle, then writes code.

| Aspect | Specification |
|--------|---------------|
| **Display** | Function signature (optional), oracle query interface, code editor |
| **Input** | Probe queries (sync) + code submission (async) |
| **Validation** | Code must be syntactically valid |
| **Pipeline** | Async - executes student code in Docker against test cases |
| **Grading** | Test pass rate |
| **Feedback** | Test results, probe history |

**Model**: `ProbeableCodeProblem` (inherits from `SpecProblem`)

**Model fields**:
```python
show_function_signature = models.BooleanField(default=True)
probe_mode = models.CharField(
    choices=[("block", "Block after limit"), ("cooldown", "Cooldown refill"), ("explore", "Unlimited")],
    default="explore"
)
max_probes = models.PositiveIntegerField(default=10)
cooldown_attempts = models.PositiveIntegerField(default=3)
cooldown_refill = models.PositiveIntegerField(default=5)
```

**Probe modes**:
- `block`: N probes total, then disabled permanently
- `cooldown`: N probes -> submit X times -> get M more probes
- `explore`: Unlimited probing

---

### Probeable Spec

**Purpose**: Like Probeable Code, but student writes NL explanation instead of code.

| Aspect | Specification |
|--------|---------------|
| **Display** | Function signature (optional), oracle interface, text area |
| **Input** | Probe queries (sync) + NL explanation submission (async) |
| **Validation** | Explanation length requirements |
| **Pipeline** | Async - LLM generates code from explanation, tests in Docker |
| **Grading** | Test pass rate + comprehension level (like EiPL) |
| **Feedback** | Generated code variations, test results, segmentation |

**Model**: `ProbeableSpecProblem` (inherits from `SpecProblem`)

**Model fields**: Same as ProbeableCodeProblem (probe configuration) plus SpecProblem fields (LLM config, segmentation).

---

### Prompt (Image-based EiPL)

**Purpose**: Like EiPL but student explains behavior from an image instead of code.

| Aspect | Specification |
|--------|---------------|
| **Display** | Image viewer instead of code viewer |
| **Input** | Text explanation (same as EiPL) |
| **Validation** | Same as EiPL |
| **Pipeline** | Async - reuses EiPL pipeline |
| **Grading** | Same as EiPL (segmentation threshold) |
| **Feedback** | Same as EiPL (variations panel) |

**Model**: `PromptProblem` (inherits from `SpecProblem`)

**Model fields**:
```python
image_url = models.URLField(help_text="URL of the problem image")
image_alt_text = models.CharField(max_length=500, blank=True)
```

---

## Checklist

Use this when implementing a new problem type:

### Backend - Model
- [ ] Create polymorphic model class in `models/spec.py` or `models/static.py`
- [ ] Implement `polymorphic_type` property returning type identifier
- [ ] Add type-specific fields (use proper Django fields, not JSONField for everything)
- [ ] Implement `clean()` for validation
- [ ] Export model in `models/__init__.py`

### Backend - Handler
- [ ] Create handler directory: `handlers/{type_name}/`
- [ ] Create `handlers/{type_name}/__init__.py` with handler export
- [ ] Create `handlers/{type_name}/handler.py` implementing all abstract methods:
  - `type_name` property
  - `validate_input()`
  - `process_submission()` (or raise NotImplementedError if using submit())
  - `calculate_grade()`
  - `is_correct()`
  - `evaluate_completion()`
  - `extract_variations()`
  - `extract_test_results()`
  - `count_variations()`
  - `count_passing_variations()`
  - `get_problem_config()`
  - `serialize_result()`
  - `get_admin_config()`
  - `submit()` - choose sync or async pattern
- [ ] Add handler import to `handlers/__init__.py`
- [ ] (Async only) Create pipeline task in `tasks/pipeline.py`
- [ ] Generate and run migrations

### Frontend
- [ ] Create input component in `purplex/client/src/components/activities/inputs/`
- [ ] Create feedback component in `purplex/client/src/components/activities/feedback/` (or reuse existing)
- [ ] Register components in `purplex/client/src/components/activities/index.ts`
- [ ] Add type-specific interfaces to `types.ts` if needed

### Testing
- [ ] Write handler unit tests in `tests/unit/handlers/`
- [ ] (Async only) Write pipeline integration tests in `tests/integration/`
- [ ] Manual test: create problem via admin
- [ ] Manual test: load problem in frontend
- [ ] Manual test: submit and verify feedback

---

## Capability Matrix

Quick reference for shared capabilities across types:

| Capability | EiPL | MCQ | Prompt | Debug Fix | Refute | Probeable Code | Probeable Spec |
|------------|------|-----|--------|-----------|--------|----------------|----------------|
| Code viewer | Yes | Yes | No | Editable | Yes | No | No |
| Image viewer | No | No | Yes | No | No | No | No |
| Text input | Yes | No | Yes | No | No | No | Yes |
| Code input | No | No | No | Yes | No | Yes | No |
| JSON input | No | No | No | No | Yes | No | No |
| Radio input | No | Yes | No | No | No | No | No |
| Oracle interface | No | No | No | No | No | Yes | Yes |
| LLM in pipeline | Yes | No | Yes | No | No | No | Yes |
| Docker execution | Yes | No | Yes | Yes | No | Yes | Yes |
| Segmentation | Yes | No | Optional | No | No | No | Yes |
| Sync submission | No | Yes | No | No | Yes | No | No |
| Async submission | Yes | No | Yes | Yes | No | Yes | Yes |
