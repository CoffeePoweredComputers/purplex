"""
Base handler for activity types.

This module defines the abstract base class for all activity type handlers.
Each activity type (EiPL, Direct Code, Multiple Choice, etc.) implements
this interface to handle its specific logic.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from purplex.problems_app.models import Problem
    from purplex.submissions.models import Submission


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    error: Optional[str] = None


@dataclass
class ProcessingResult:
    """Result of submission processing."""
    success: bool
    processed_code: Optional[str] = None
    error: Optional[str] = None
    type_specific_data: Optional[Dict[str, Any]] = None


@dataclass
class SubmissionOutcome:
    """
    Result of handler.submit() - encapsulates sync vs async execution.

    For synchronous handlers (e.g., MCQ):
        - complete=True
        - submission contains the finalized result

    For asynchronous handlers (e.g., EiPL):
        - complete=False
        - task_id contains the Celery task ID for polling
    """
    complete: bool
    submission: 'Submission'
    task_id: Optional[str] = None
    error: Optional[str] = None
    result_data: Dict[str, Any] = field(default_factory=dict)


class ActivityHandler(ABC):
    """
    Base class for activity type handlers.

    Each activity type (EiPL, Direct Code, Multiple Choice, etc.)
    implements this interface to handle its specific logic.
    """

    @property
    @abstractmethod
    def type_name(self) -> str:
        """Unique identifier for this activity type."""
        pass

    # ─── Input Validation ───────────────────────────────────────

    @abstractmethod
    def validate_input(
        self,
        raw_input: str,
        problem: 'Problem'
    ) -> ValidationResult:
        """
        Validate user input before submission processing.
        Called before creating the Submission object.
        """
        pass

    # ─── Submission Processing ──────────────────────────────────

    @abstractmethod
    def process_submission(
        self,
        submission: 'Submission',
        raw_input: str,
        problem: 'Problem'
    ) -> ProcessingResult:
        """
        Process the submission. This is the main type-specific logic.

        For EiPL: Generate code variations, run tests, analyze segmentation
        For Direct Code: Run tests on submitted code
        For MCQ: Check selected answer

        Should update submission fields and create any type-specific records.
        """
        pass

    # ─── Grading ────────────────────────────────────────────────

    @abstractmethod
    def calculate_grade(self, submission: 'Submission') -> str:
        """
        Calculate grade based on submission results.

        Returns: 'complete', 'partial', or 'incomplete'
        """
        pass

    @abstractmethod
    def is_correct(self, submission: 'Submission') -> bool:
        """
        Determine if submission meets correctness criteria.

        For EiPL: All tests pass
        For Direct Code: All tests pass
        For MCQ: Correct answer selected
        """
        pass

    # ─── Completion Evaluation ──────────────────────────────────

    @abstractmethod
    def evaluate_completion(
        self,
        submission: 'Submission',
        problem: 'Problem'
    ) -> str:
        """
        Evaluate completion status for progress tracking.

        For EiPL: Requires correctness + high-level comprehension
        For Direct Code: Just correctness
        For MCQ: Just correctness

        Returns: 'complete', 'partial', or 'incomplete'
        """
        pass

    # ─── Data Extraction ────────────────────────────────────────

    @abstractmethod
    def extract_variations(self, submission: 'Submission') -> List[str]:
        """
        Extract code variations from a submission.

        For EiPL: Returns all generated code variations
        For Direct Code: Returns the single submitted code
        """
        pass

    @abstractmethod
    def extract_test_results(
        self,
        submission: 'Submission',
        problem: 'Problem'
    ) -> List[Dict[str, Any]]:
        """
        Extract test results in frontend-compatible format.
        """
        pass

    @abstractmethod
    def count_variations(self, submission: 'Submission') -> int:
        """
        Count total variations for a submission.
        """
        pass

    @abstractmethod
    def count_passing_variations(self, submission: 'Submission') -> int:
        """
        Count variations that pass all tests.
        """
        pass

    # ─── API Configuration ──────────────────────────────────────

    @abstractmethod
    def get_problem_config(self, problem: 'Problem') -> Dict[str, Any]:
        """
        Return configuration for frontend rendering.

        Returns dict with:
        - display: How to show the problem
        - input: What input component to use
        - hints: Available hint types
        - feedback: What feedback to show
        """
        pass

    @abstractmethod
    def serialize_result(self, submission: 'Submission') -> Dict[str, Any]:
        """
        Serialize submission result for API response.

        Returns type-specific data for the feedback panel.
        """
        pass

    @abstractmethod
    def get_admin_config(self) -> Dict[str, Any]:
        """
        Return configuration for admin UI rendering.

        Returns dict with:
        - hidden_sections: List of section names to hide (e.g., ['code_solution', 'test_cases'])
        - required_fields: List of required field names
        - optional_fields: List of optional field names
        - type_specific_section: Component name for type-specific input (or None)
        - supports: Dict of feature flags (hints, segmentation, test_cases, etc.)
        """
        pass

    # ─── Submission Execution ────────────────────────────────────

    @abstractmethod
    def submit(
        self,
        submission: 'Submission',
        raw_input: str,
        problem: 'Problem',
        context: Dict[str, Any]
    ) -> 'SubmissionOutcome':
        """
        Execute the full submission lifecycle for this activity type.

        This method owns the execution model (sync vs async) for the type.
        - Synchronous handlers (MCQ): process inline, return complete=True
        - Asynchronous handlers (EiPL): queue Celery task, return complete=False

        Args:
            submission: The Submission record (already created, status='pending')
            raw_input: The user's input
            problem: The Problem being submitted to
            context: Additional context (user_id, problem_set_id, course_id, etc.)

        Returns:
            SubmissionOutcome with either complete results or task_id for polling
        """
        pass

    # ─── Optional Hooks ─────────────────────────────────────────

    def on_submission_created(self, submission: 'Submission') -> None:
        """Hook called after submission is created but before processing."""
        pass

    def on_submission_complete(self, submission: 'Submission') -> None:
        """Hook called after submission processing is complete."""
        pass

    # ─── Shared Utilities ─────────────────────────────────────────

    @staticmethod
    def _format_function_call(
        function_name: str,
        input_values: Union[List[Any], Any]
    ) -> str:
        """
        Format a function call string from function name and input values.

        Args:
            function_name: Name of the function
            input_values: Either a list of arguments or a single argument

        Returns:
            Formatted function call string, e.g., "my_func(1, 'hello', [1, 2])"
        """
        if isinstance(input_values, list):
            # Use json.dumps for strings to ensure proper quoting, repr for others
            args = ', '.join(
                json.dumps(v) if isinstance(v, str) else repr(v)
                for v in input_values
            )
        else:
            # Single value case
            args = (
                json.dumps(input_values) if isinstance(input_values, str)
                else repr(input_values)
            )
        return f"{function_name}({args})"
