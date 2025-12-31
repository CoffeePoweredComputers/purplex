# Activity Type Handler Implementation Details

This document explains the handler-based activity type system in Purplex.

## Overview

The activity type system uses a **handler pattern** to support different problem types. Each handler encapsulates type-specific logic for validation, processing, grading, and configuration.

## Handler Architecture

### Core Components

```
problems_app/handlers/
├── __init__.py          # Registry exports (get_handler, is_registered, etc.)
├── base.py              # ActivityHandler ABC + dataclasses
├── debug_fix/
│   ├── __init__.py
│   └── handler.py       # DebugFixHandler
├── eipl/
│   ├── __init__.py
│   └── handler.py       # EiPLHandler
├── mcq/
│   ├── __init__.py
│   └── handler.py       # MCQHandler
├── probeable_code/
│   ├── __init__.py
│   └── handler.py       # ProbeableCodeHandler
├── probeable_spec/
│   ├── __init__.py
│   └── handler.py       # ProbeableSpecHandler
├── prompt/
│   ├── __init__.py
│   └── handler.py       # PromptHandler
└── refute/
    ├── __init__.py
    └── handler.py       # RefuteHandler
```

### Handler Registration

Handlers are registered using the `@register_handler` decorator:

```python
from purplex.problems_app.handlers import register_handler
from purplex.problems_app.handlers.base import ActivityHandler

@register_handler('my_type')
class MyTypeHandler(ActivityHandler):
    @property
    def type_name(self) -> str:
        return 'my_type'

    # Implement all required abstract methods...
```

### Dataclasses

The handler system uses these dataclasses defined in `base.py`:

```python
@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    error: str | None = None

@dataclass
class ProcessingResult:
    """Result of submission processing."""
    success: bool
    processed_code: str | None = None
    error: str | None = None
    type_specific_data: dict[str, Any] | None = None

@dataclass
class SubmissionOutcome:
    """
    Result of handler.submit() - encapsulates sync vs async execution.

    For synchronous handlers (e.g., MCQ, Refute):
        - complete=True
        - submission contains the finalized result

    For asynchronous handlers (e.g., EiPL, DebugFix):
        - complete=False
        - task_id contains the Celery task ID for polling
    """
    complete: bool
    submission: "Submission"
    task_id: str | None = None
    error: str | None = None
    result_data: dict[str, Any] = field(default_factory=dict)
```

### Required Methods

All handlers must implement these methods from `ActivityHandler`:

```python
class ActivityHandler(ABC):
    @property
    @abstractmethod
    def type_name(self) -> str:
        """Unique identifier for this activity type."""
        pass

    # ─── Input Validation ───────────────────────────────────────

    @abstractmethod
    def validate_input(self, raw_input: str, problem: "Problem") -> ValidationResult:
        """Validate user input before submission processing."""
        pass

    # ─── Submission Processing ──────────────────────────────────

    @abstractmethod
    def process_submission(
        self, submission: "Submission", raw_input: str, problem: "Problem"
    ) -> ProcessingResult:
        """Process the submission. Type-specific logic (may raise NotImplementedError for async types)."""
        pass

    # ─── Grading ────────────────────────────────────────────────

    @abstractmethod
    def calculate_grade(self, submission: "Submission") -> str:
        """Calculate grade. Returns: 'complete', 'partial', or 'incomplete'"""
        pass

    @abstractmethod
    def is_correct(self, submission: "Submission") -> bool:
        """Determine if submission meets correctness criteria."""
        pass

    # ─── Completion Evaluation ──────────────────────────────────

    @abstractmethod
    def evaluate_completion(self, submission: "Submission", problem: "Problem") -> str:
        """Evaluate completion status for progress tracking. Returns: 'complete', 'partial', or 'incomplete'"""
        pass

    # ─── Data Extraction ────────────────────────────────────────

    @abstractmethod
    def extract_variations(self, submission: "Submission") -> list[str]:
        """Extract code variations from a submission."""
        pass

    @abstractmethod
    def extract_test_results(
        self, submission: "Submission", problem: "Problem"
    ) -> list[dict[str, Any]]:
        """Extract test results in frontend-compatible format."""
        pass

    @abstractmethod
    def count_variations(self, submission: "Submission") -> int:
        """Count total variations for a submission."""
        pass

    @abstractmethod
    def count_passing_variations(self, submission: "Submission") -> int:
        """Count variations that pass all tests."""
        pass

    # ─── API Configuration ──────────────────────────────────────

    @abstractmethod
    def get_problem_config(self, problem: "Problem") -> dict[str, Any]:
        """Return configuration for frontend rendering."""
        pass

    @abstractmethod
    def serialize_result(self, submission: "Submission") -> dict[str, Any]:
        """Serialize submission result for API response."""
        pass

    @abstractmethod
    def get_admin_config(self) -> dict[str, Any]:
        """Return configuration for admin UI rendering."""
        pass

    # ─── Submission Execution ────────────────────────────────────

    @abstractmethod
    def submit(
        self,
        submission: "Submission",
        raw_input: str,
        problem: "Problem",
        context: dict[str, Any],
    ) -> SubmissionOutcome:
        """
        Execute the full submission lifecycle for this activity type.

        This method owns the execution model (sync vs async) for the type.
        - Synchronous handlers (MCQ, Refute): process inline, return complete=True
        - Asynchronous handlers (EiPL, DebugFix): queue Celery task, return complete=False
        """
        pass

    # ─── Optional Hooks ─────────────────────────────────────────

    def on_submission_created(self, submission: "Submission") -> None:
        """Hook called after submission is created but before processing."""
        pass

    def on_submission_complete(self, submission: "Submission") -> None:
        """Hook called after submission processing is complete."""
        pass
```

## Configuration Contracts

### Problem Config (Frontend Rendering)

The `get_problem_config()` method returns configuration for the frontend:

```python
{
    'display': {
        'show_reference_code': bool,   # Show reference solution after completion
        'code_read_only': bool,        # Whether code editor is read-only
        'show_function_signature': bool,# Show function signature hint
        'section_label': str,          # Label for the input section
        # Type-specific display options:
        'show_image': bool,            # Prompt: show image instead of code
        'show_buggy_code': bool,       # DebugFix: show buggy code to edit
        'show_claim': bool,            # Refute: show claim to disprove
    },
    'input': {
        'type': str,                   # 'textarea', 'radio', 'checkbox', 'code', 'json', 'probeable_code', 'probeable_spec'
        'label': str,                  # Label for input field
        'placeholder': str,            # Placeholder text (optional)
        'options': list,               # For MCQ: list of options
        'language': str,               # For code types: 'python'
        'min_length': int,             # Minimum input length
        'max_length': int,             # Maximum input length
    },
    'probe': {                         # For probeable types only
        'enabled': bool,
        'mode': str,                   # 'explore', 'limited', 'cooldown'
        'max_probes': int,
        'function_signature': str,
        'function_name': str,
        'parameters': list,            # Parsed parameter info
    },
    'hints': {
        'available': list,             # Available hint types (e.g., ['variable_fade', 'subgoal_highlight', 'suggested_trace'])
        'enabled': bool,               # Whether hints are enabled
    },
    'feedback': {
        'show_variations': bool,       # Show code variations (EiPL, ProbeableSpec)
        'show_segmentation': bool,     # Show segmentation section
        'show_test_results': bool,     # Show test execution results
        'show_correct_answer': bool,   # Show correct answer (MCQ)
        'show_probe_history': bool,    # Show past probe queries (probeable types)
        'show_execution_result': bool, # Show execution result (Refute)
    }
}
```

### Admin Config (Editor)

The `get_admin_config()` method returns configuration for the admin editor:

```python
{
    'hidden_sections': list,           # Sections to hide in editor (e.g., ['code_solution', 'test_cases'])
    'required_fields': list,           # Fields that must be filled
    'optional_fields': list,           # Optional field names
    'type_specific_section': str|None, # Component name for type-specific input (e.g., 'options', 'refute_config')
    'supports': {
        'hints': bool,                 # Whether type supports hints
        'segmentation': bool,          # Whether type supports segmentation
        'test_cases': bool,            # Whether type uses test cases
    }
}
```

## Handler Usage

### Getting a Handler

```python
from purplex.problems_app.handlers import get_handler, is_registered

# Check if a type is registered
if is_registered('mcq'):
    handler = get_handler('mcq')

# Use handler
config = handler.get_problem_config(problem)
result = handler.validate_input(user_input, problem)
```

### Available Functions

```python
from purplex.problems_app.handlers import (
    ActivityHandler,        # Base class for handlers
    ValidationResult,       # Dataclass for validation results
    ProcessingResult,       # Dataclass for processing results
    SubmissionOutcome,      # Dataclass for submit() results
    register_handler,       # Decorator to register a handler
    get_handler,            # Get handler instance by type
    get_registered_types,   # List all registered types
    is_registered,          # Check if type is registered
)
```

## Current Handlers (7 types)

### EiPLHandler (`eipl`)

- Code comprehension with natural language explanations
- Generates code variations from user prompt via LLM
- Executes test cases against variations in Docker
- Supports segmentation analysis for comprehension level
- Supports hints (Variable Fade, Subgoal Highlighting, Suggested Trace)
- **Async processing** via Celery

### MCQHandler (`mcq`)

- Multiple choice questions
- No code execution required
- Binary correctness (correct/incorrect)
- No hint support
- Shows correct answer after submission
- **Sync processing** (no Celery)

### PromptHandler (`prompt`)

- Image-based EiPL variant
- Displays image instead of code
- Reuses EiPL pipeline for processing
- Supports segmentation and hints
- **Async processing** via Celery

### DebugFixHandler (`debug_fix`)

- Students receive buggy code and must fix it
- No LLM involved - student directly edits code
- Runs test cases against student's fixed code
- Supports progressive bug hints
- **Async processing** via Celery (Docker execution)

### ProbeableCodeHandler (`probeable_code`)

- Students discover hidden function behavior via oracle probes
- Probe limit enforced based on `probe_mode`
- Students write code implementing the discovered behavior
- Tests against hidden test cases
- No traditional hints - probing is the discovery mechanism
- **Async processing** via Celery (Docker execution)

### ProbeableSpecHandler (`probeable_spec`)

- Combines probe discovery with NL explanation (like EiPL)
- Students probe oracle to discover behavior, then write NL explanation
- LLM generates code from explanation (reuses EiPL pipeline)
- Supports segmentation for comprehension analysis
- **Async processing** via Celery

### RefuteHandler (`refute`)

- Counterexample problems
- Students find input that disproves a claim about a function
- Executes function with student input to check claim
- Uses `claim_predicate` for evaluation (with legacy pattern matching fallback)
- **Sync processing** (restricted in-process execution)

## Pipeline Integration

Each handler owns its execution model via the `submit()` method. Handlers determine whether processing is synchronous or asynchronous:

**Synchronous handlers** (MCQ, Refute):
- Process inline within the API request
- Return `SubmissionOutcome(complete=True, ...)`
- No polling required

**Asynchronous handlers** (EiPL, Prompt, DebugFix, ProbeableCode, ProbeableSpec):
- Queue a Celery task for background processing
- Return `SubmissionOutcome(complete=False, task_id=..., ...)`
- Frontend polls for completion

```python
# Example: EiPL submit() queues Celery task
def submit(self, submission, raw_input, problem, context) -> SubmissionOutcome:
    task = execute_eipl_pipeline.apply_async(
        args=[problem.id, raw_input, context["user_id"], ...],
        task_id=context["request_id"],
    )
    return SubmissionOutcome(complete=False, submission=submission, task_id=task.id)

# Example: MCQ submit() processes inline
def submit(self, submission, raw_input, problem, context) -> SubmissionOutcome:
    # ... process and grade immediately ...
    return SubmissionOutcome(complete=True, submission=submission, result_data={...})
```

### Celery Pipeline Tasks

- `execute_eipl_pipeline` - Used by EiPL, Prompt, ProbeableSpec
- `execute_debug_fix_pipeline` - Used by DebugFix
- `execute_probeable_code_pipeline` - Used by ProbeableCode

## Adding a New Handler

See [NEW_PROBLEM_TYPE_GUIDE.md](../development/NEW_PROBLEM_TYPE_GUIDE.md) for step-by-step instructions on adding a new activity type.

## Testing

Handler tests are in `tests/unit/test_handlers.py`:

```bash
pytest tests/unit/test_handlers.py -v
```

Registry consistency tests are in `tests/unit/test_registry_consistency.py`:

```bash
pytest tests/unit/test_registry_consistency.py -v
```
