# Problem Types Catalog

This document catalogs all problem/activity types in Purplex, both implemented and planned.

## Architecture Overview

Purplex uses a polymorphic model hierarchy with a handler pattern for extensibility:

```
Problem (PolymorphicModel base)
  |
  +-- StaticProblem (abstract) - No code execution
  |     |
  |     +-- McqProblem (implemented)
  |     +-- RefuteProblem (implemented)
  |     +-- ShortAnswerProblem (planned)
  |
  +-- SpecProblem (abstract) - NL -> LLM -> Code -> Test
        |
        +-- EiplProblem (implemented)
        +-- PromptProblem (implemented)
        +-- DebugFixProblem (implemented)
        +-- ProbeableCodeProblem (implemented)
        +-- ProbeableSpecProblem (implemented)
```

Each problem type has a corresponding handler in `purplex/problems_app/handlers/`.

---

## Implemented Types

### EiPL (Explain in Plain Language)

**Status**: Implemented
**Type Identifier**: `eipl`
**Base Class**: `SpecProblem`
**Processing Model**: Asynchronous (Celery)

**Purpose**: Students describe what code does in natural language. The system generates code variations from the description and tests them.

**Key Fields**:
- `reference_solution` - Reference implementation for test validation
- `function_signature` - Function signature with type hints
- `function_name` - Auto-extracted from reference solution
- `segmentation_config` - Segmentation analysis settings
- `segmentation_threshold` - Max segments for high-level comprehension

**Pipeline**:
1. Student submits natural language description
2. LLM generates multiple code variations (typically 3)
3. Each variation runs against test cases in Docker containers
4. Segmentation analysis evaluates comprehension depth
5. Score based on test pass rate and segmentation quality

**Grading Logic**:
- **Complete**: All tests pass AND segmentation passes (if enabled)
- **Partial**: All tests pass but segmentation fails (too low-level)
- **Incomplete**: Tests fail

**Handler**: `EiPLHandler` in `handlers/eipl/handler.py`

---

### MCQ (Multiple Choice Question)

**Status**: Implemented
**Type Identifier**: `mcq`
**Base Class**: `StaticProblem`
**Processing Model**: Synchronous (inline)

**Purpose**: Students select from predefined answer options. Simple knowledge check with deterministic grading.

**Key Fields**:
- `question_text` - The question shown to students
- `options` - JSON array of `{id, text, is_correct, explanation}`
- `allow_multiple` - Whether multiple selections are allowed
- `shuffle_options` - Randomize option order per attempt

**Pipeline**:
1. Student selects an option
2. Compare to correct answer(s)
3. Score: 100 (correct) or 0 (incorrect)

**Grading Logic**:
- **Complete**: Correct answer selected
- **Incomplete**: Wrong answer selected

**Handler**: `MCQHandler` in `handlers/mcq/handler.py`

---

### Prompt (Image-based EiPL)

**Status**: Implemented
**Type Identifier**: `prompt`
**Base Class**: `SpecProblem`
**Processing Model**: Asynchronous (Celery)

**Purpose**: Students see an image instead of code and describe what it represents. Same pipeline as EiPL otherwise.

**Key Fields**:
- All `SpecProblem` fields (reference_solution, function_signature, etc.)
- `image_url` - URL of the problem image
- `image_alt_text` - Alt text for accessibility
- `SEGMENTATION_DEFAULT_ENABLED = False` - Segmentation off by default

**Pipeline**: Same as EiPL (reuses `execute_eipl_pipeline` task)

**Grading Logic**: Same as EiPL

**Handler**: `PromptHandler` in `handlers/prompt/handler.py`

---

### Refute (Find Counterexamples)

**Status**: Implemented
**Type Identifier**: `refute`
**Base Class**: `StaticProblem`
**Processing Model**: Synchronous (inline with restricted execution)

**Purpose**: Students find counterexamples that disprove a claim about a function. Tests understanding of edge cases and specifications.

**Key Fields**:
- `question_text` - The question shown to students (inherited from StaticProblem)
- `claim_text` - The false claim about the function (e.g., "f(x) always returns positive")
- `claim_predicate` - Python expression that's True when claim holds (e.g., `result > 0`)
- `reference_solution` - The actual function code to execute
- `function_signature` - Function signature for input parsing (e.g., `f(x: int) -> int`)
- `expected_counterexample` - Optional known counterexample for hints

**Pipeline**:
1. Display a function with a claim about its behavior
2. Student provides JSON input (e.g., `{"x": -5}`)
3. System executes function in a restricted sandbox (safe builtins only)
4. Claim predicate evaluated to determine if counterexample is valid

**Grading Logic**:
- **Complete**: Valid counterexample found (claim disproven)
- **Incomplete**: No valid counterexample

**Handler**: `RefuteHandler` in `handlers/refute/handler.py`

---

### Debug Fix (Fix Buggy Code)

**Status**: Implemented
**Type Identifier**: `debug_fix`
**Base Class**: `SpecProblem`
**Processing Model**: Asynchronous (Celery)

**Purpose**: Students fix bugs in given code. Tests debugging and code comprehension skills.

**Key Fields**:
- `reference_solution` - The correct implementation (hidden from student)
- `function_signature` - Function signature with type hints
- `buggy_code` - Code with intentional bug(s) for student to fix
- `bug_hints` - Progressive hints: `[{level: 1, text: "Check line 5"}, ...]`

**Pipeline**:
1. Display buggy code with failing test cases
2. Student modifies the code to fix the bug
3. Fixed code tested against all test cases in Docker

**Grading Logic**:
- **Complete**: All tests pass
- **Incomplete**: Any tests fail

**Handler**: `DebugFixHandler` in `handlers/debug_fix/handler.py`

---

### Probeable Code (Oracle Discovery -> Code)

**Status**: Implemented
**Type Identifier**: `probeable_code`
**Base Class**: `SpecProblem`
**Processing Model**: Asynchronous (Celery)

**Purpose**: Students discover function behavior by querying an oracle, then implement the function.

**Key Fields**:
- `reference_solution` - Hidden oracle implementation
- `function_signature` - Function signature with type hints
- `show_function_signature` - Whether to show signature to student
- `probe_mode` - How probe limits are enforced: `block`, `cooldown`, or `explore`
- `max_probes` - Initial probe budget (ignored for 'explore' mode)
- `cooldown_attempts` - Submission attempts before probe refill (cooldown mode)
- `cooldown_refill` - Probes granted after cooldown (cooldown mode)

**Pipeline**:
1. Hidden reference implementation acts as oracle
2. Students can "probe" with inputs to see outputs (sync API)
3. Probe limit enforced based on probe_mode
4. After discovery, student writes implementation
5. Implementation tested against hidden test cases in Docker

**Grading Logic**:
- **Complete**: Implementation passes all tests
- **Incomplete**: Implementation fails any tests

**Handler**: `ProbeableCodeHandler` in `handlers/probeable_code/handler.py`

---

### Probeable Spec (Oracle Discovery -> NL)

**Status**: Implemented
**Type Identifier**: `probeable_spec`
**Base Class**: `SpecProblem`
**Processing Model**: Asynchronous (Celery)

**Purpose**: Students discover function behavior by querying an oracle, then write a natural language specification.

**Key Fields**:
- `reference_solution` - Hidden oracle implementation
- `function_signature` - Function signature with type hints
- `show_function_signature` - Whether to show signature to student
- `probe_mode` - How probe limits are enforced: `block`, `cooldown`, or `explore`
- `max_probes` - Initial probe budget (ignored for 'explore' mode)
- `cooldown_attempts` - Submission attempts before probe refill (cooldown mode)
- `cooldown_refill` - Probes granted after cooldown (cooldown mode)
- `segmentation_config` - Segmentation analysis settings
- `segmentation_threshold` - Max segments for high-level comprehension

**Pipeline**:
1. Same oracle probing mechanism as Probeable Code (sync API)
2. Probe limit enforced based on probe_mode
3. Instead of writing code, student writes NL description
4. LLM generates code from description (reuses EiPL pipeline)
5. Generated code tested against hidden test cases

**Grading Logic**: Same as EiPL (tests + optional segmentation)
- **Complete**: All tests pass AND segmentation passes (if enabled)
- **Partial**: All tests pass but segmentation fails (too low-level)
- **Incomplete**: Tests fail

**Handler**: `ProbeableSpecHandler` in `handlers/probeable_spec/handler.py`

---

## Planned Types

### Short Answer

**Status**: Planned
**Type Identifier**: `short_answer`
**Base Class**: `StaticProblem`

**Purpose**: Free-text short answer questions with AI-assisted grading.

---

## Handler Interface

All problem types implement the `ActivityHandler` interface:

```python
class ActivityHandler(ABC):
    @property
    @abstractmethod
    def type_name(self) -> str:
        """Unique identifier for this activity type."""

    # ─── Input Validation ───────────────────────────────────────
    @abstractmethod
    def validate_input(self, raw_input: str, problem: 'Problem') -> ValidationResult:
        """Validate user input before submission processing."""

    # ─── Submission Processing ──────────────────────────────────
    @abstractmethod
    def process_submission(
        self, submission: 'Submission', raw_input: str, problem: 'Problem'
    ) -> ProcessingResult:
        """Process the submission. Main type-specific logic."""

    @abstractmethod
    def submit(
        self,
        submission: 'Submission',
        raw_input: str,
        problem: 'Problem',
        context: Dict[str, Any]
    ) -> SubmissionOutcome:
        """Execute full submission lifecycle (sync or async)."""

    # ─── Grading ────────────────────────────────────────────────
    @abstractmethod
    def calculate_grade(self, submission: 'Submission') -> str:
        """Calculate grade: 'complete', 'partial', or 'incomplete'."""

    @abstractmethod
    def is_correct(self, submission: 'Submission') -> bool:
        """Determine if submission meets correctness criteria."""

    @abstractmethod
    def evaluate_completion(self, submission: 'Submission', problem: 'Problem') -> str:
        """Evaluate completion status for progress tracking."""

    # ─── Data Extraction ────────────────────────────────────────
    @abstractmethod
    def extract_variations(self, submission: 'Submission') -> List[str]:
        """Extract code variations from a submission."""

    @abstractmethod
    def extract_test_results(
        self, submission: 'Submission', problem: 'Problem'
    ) -> List[Dict[str, Any]]:
        """Extract test results in frontend-compatible format."""

    @abstractmethod
    def count_variations(self, submission: 'Submission') -> int:
        """Count total variations for a submission."""

    @abstractmethod
    def count_passing_variations(self, submission: 'Submission') -> int:
        """Count variations that pass all tests."""

    # ─── API Configuration ──────────────────────────────────────
    @abstractmethod
    def get_problem_config(self, problem: 'Problem') -> Dict[str, Any]:
        """Return frontend rendering configuration."""

    @abstractmethod
    def serialize_result(self, submission: 'Submission') -> Dict[str, Any]:
        """Serialize submission result for API response."""

    @abstractmethod
    def get_admin_config(self) -> Dict[str, Any]:
        """Return admin UI configuration."""
```

## Adding New Types

See [NEW_PROBLEM_TYPE_GUIDE.md](../development/NEW_PROBLEM_TYPE_GUIDE.md) for step-by-step instructions on implementing new problem types.

## Processing Models

### Synchronous (Inline)

Used by: MCQ, Refute

- Processing completes during HTTP request
- `SubmissionOutcome.complete = True`
- Result returned immediately
- For Refute: Uses restricted sandbox with safe builtins (no file/network access)

### Asynchronous (Celery)

Used by: EiPL, Prompt, Debug Fix, Probeable Code, Probeable Spec

- Processing queued to Celery worker
- `SubmissionOutcome.complete = False`
- `SubmissionOutcome.task_id` returned for polling
- Frontend uses SSE or polling for updates
- Required for: LLM calls, Docker code execution, segmentation analysis
