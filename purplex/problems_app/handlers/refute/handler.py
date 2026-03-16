"""
Refute (Counterexample) Handler.

Handles problems where students must find input that disproves a claim about a function.
Processing is synchronous - no Celery needed since we execute code in-process.
"""

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from .. import register_handler
from ..base import (
    ActivityHandler,
    ProcessingResult,
    SubmissionOutcome,
    ValidationResult,
)

if TYPE_CHECKING:
    from purplex.problems_app.models import RefuteProblem
    from purplex.submissions.models import Submission

logger = logging.getLogger(__name__)


def _ensure_refute_problem(problem: Any) -> "RefuteProblem":
    """
    Ensure we have a RefuteProblem instance.

    This handles the case where we might receive a base Problem
    that needs to be cast to RefuteProblem.
    """
    from purplex.problems_app.models import RefuteProblem

    if isinstance(problem, RefuteProblem):
        return problem

    # If it's a base Problem, try to get the RefuteProblem
    if hasattr(problem, "refuteproblem"):
        return problem.refuteproblem

    raise TypeError(
        f"Expected RefuteProblem, got {type(problem).__name__}. "
        f"Problem slug: {getattr(problem, 'slug', 'unknown')}"
    )


def _parse_function_args(signature: str) -> list[dict[str, str]]:
    """
    Parse function signature to extract parameter names and types.

    Args:
        signature: Function signature like "f(x: int, y: str) -> bool"

    Returns:
        List of dicts with 'name' and 'type' keys
    """
    # Extract the part between parentheses
    match = re.search(r"\(([^)]*)\)", signature)
    if not match:
        return []

    params_str = match.group(1).strip()
    if not params_str:
        return []

    params = []
    for param in params_str.split(","):
        param = param.strip()
        if ":" in param:
            name, type_hint = param.split(":", 1)
            params.append({"name": name.strip(), "type": type_hint.strip()})
        else:
            params.append({"name": param, "type": "Any"})

    return params


def _safe_execute(
    code: str, function_name: str, args: dict[str, Any]
) -> dict[str, Any]:
    """
    Execute function code safely with provided arguments.

    Uses a restricted environment to prevent dangerous operations.

    Args:
        code: The function code to execute
        function_name: Name of the function to call
        args: Arguments to pass to the function

    Returns:
        Dict with 'success', 'result', 'error' keys
    """
    # Restricted builtins - only safe operations
    safe_builtins = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "chr": chr,
        "dict": dict,
        "divmod": divmod,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "frozenset": frozenset,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "ord": ord,
        "pow": pow,
        "range": range,
        "reversed": reversed,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
        "True": True,
        "False": False,
        "None": None,
    }

    # Create restricted globals
    restricted_globals = {
        "__builtins__": safe_builtins,
    }

    try:
        # Execute the function definition
        # nosec B102: exec used with restricted_globals (safe_builtins only, no file/network access)
        exec(code, restricted_globals)  # nosec B102

        # Check if function was defined
        if function_name not in restricted_globals:
            return {
                "success": False,
                "result": None,
                "error": f"Function '{function_name}' not defined in code",
            }

        # Get the function
        func = restricted_globals[function_name]

        # Call the function with provided args
        result = func(**args)

        return {"success": True, "result": result, "error": None}

    except Exception as e:
        return {"success": False, "result": None, "error": str(e)}


def _extract_function_name(signature: str) -> str:
    """
    Extract function name from signature.

    Args:
        signature: Function signature like "f(x: int) -> int"

    Returns:
        Function name (e.g., "f")
    """
    match = re.match(r"(\w+)\s*\(", signature)
    return match.group(1) if match else "f"


@register_handler("refute")
class RefuteHandler(ActivityHandler):
    """Handler for Refute (Counterexample) problems."""

    @property
    def type_name(self) -> str:
        return "refute"

    # --- Input Validation ---

    def validate_input(
        self, raw_input: str, problem: "RefuteProblem"
    ) -> ValidationResult:
        """
        Validate student's counterexample input.

        Input should be valid JSON representing function arguments.
        Example: {"x": -5} or {"x": 0, "y": "test"}
        """
        refute = _ensure_refute_problem(problem)
        text = raw_input.strip()

        if not text:
            return ValidationResult(
                is_valid=False, error="Please provide input values for the function"
            )

        # Parse as JSON
        try:
            args = json.loads(text)
        except json.JSONDecodeError as e:
            return ValidationResult(is_valid=False, error=f"Invalid JSON format: {e}")

        if not isinstance(args, dict):
            return ValidationResult(
                is_valid=False, error='Input must be a JSON object (e.g., {"x": -5})'
            )

        # Get expected parameter names
        params = _parse_function_args(refute.function_signature)
        expected_names = {p["name"] for p in params}

        # Check if all required parameters are provided
        provided_names = set(args.keys())
        missing = expected_names - provided_names
        if missing:
            return ValidationResult(
                is_valid=False,
                error=f"Missing parameter(s): {', '.join(sorted(missing))}",
            )

        # Note: JSON already restricts to safe types (str, int, float, bool, None, list, dict)
        # No additional validation needed

        return ValidationResult(is_valid=True)

    # --- Submission Processing ---

    def process_submission(
        self, submission: "Submission", raw_input: str, problem: "RefuteProblem"
    ) -> ProcessingResult:
        """
        Process refute submission.

        Execute the reference code with student's input and check if claim fails.
        """
        refute = _ensure_refute_problem(problem)

        # Parse input
        args = json.loads(raw_input.strip())

        # Get function name from signature
        func_name = _extract_function_name(refute.function_signature)

        # Execute the function
        exec_result = _safe_execute(refute.reference_solution, func_name, args)

        # Check if execution failed
        if not exec_result["success"]:
            return ProcessingResult(
                success=True,  # Submission processed, but execution failed
                processed_code=raw_input,
                type_specific_data={
                    "input_args": args,
                    "execution_success": False,
                    "execution_error": exec_result["error"],
                    "claim_disproven": False,
                    "result_value": None,
                },
            )

        result_value = exec_result["result"]

        # Determine if the claim is disproven using predicate or legacy pattern matching
        claim_disproven = self._evaluate_claim(
            claim_predicate=getattr(refute, "claim_predicate", ""),
            claim_text=refute.claim_text,
            result=result_value,
            input_args=args,
        )

        return ProcessingResult(
            success=True,
            processed_code=raw_input,
            type_specific_data={
                "input_args": args,
                "execution_success": True,
                "execution_error": None,
                "claim_disproven": claim_disproven,
                "result_value": self._serialize_result(result_value),
            },
        )

    def _evaluate_claim(
        self, claim_predicate: str, claim_text: str, result: Any, input_args: dict
    ) -> bool:
        """
        Evaluate if the result disproves the claim using the predicate.

        Args:
            claim_predicate: Python expression that's True when claim holds (e.g., 'result > 0')
            claim_text: Human-readable claim text (fallback for legacy pattern matching)
            result: The actual result from executing the function
            input_args: The input arguments provided by the student

        Returns:
            True if the claim is disproven (student found a valid counterexample)
        """
        # If a predicate is provided, use it
        if claim_predicate and claim_predicate.strip():
            try:
                # Build evaluation context with result and input arguments
                context = {"result": result, **input_args}

                # Restricted builtins for predicate evaluation
                safe_builtins = {
                    "abs": abs,
                    "all": all,
                    "any": any,
                    "bool": bool,
                    "len": len,
                    "max": max,
                    "min": min,
                    "sum": sum,
                    "isinstance": isinstance,
                    "int": int,
                    "float": float,
                    "str": str,
                    "list": list,
                    "dict": dict,
                    "set": set,
                    "tuple": tuple,
                    "True": True,
                    "False": False,
                    "None": None,
                }

                # Evaluate predicate - True means claim holds, False means disproven
                # nosec B307: eval used with restricted builtins (no file/network access)
                claim_holds = eval(
                    claim_predicate, {"__builtins__": safe_builtins}, context
                )  # nosec B307
                return not claim_holds  # Return True if claim is disproven

            except Exception:
                logger.exception(
                    "Predicate evaluation failed for '%s'. "
                    "Falling back to legacy pattern matching.",
                    claim_predicate,
                )
                return self._legacy_evaluate_claim(claim_text, result)

        # No predicate set — fall back to legacy pattern matching
        logger.info(
            "No claim_predicate set for claim '%s'; using legacy pattern matching. "
            "Set claim_predicate on the RefuteProblem for reliable evaluation.",
            claim_text,
        )
        return self._legacy_evaluate_claim(claim_text, result)

    def _legacy_evaluate_claim(self, claim_text: str, result: Any) -> bool:
        """
        Legacy evaluation using pattern matching on claim text.

        This is a simplified implementation that checks for common claim patterns.
        Deprecated: Use claim_predicate field instead.
        """
        claim_lower = claim_text.lower()

        # Check for "always returns positive" claims
        if "positive" in claim_lower and "always" in claim_lower:
            if isinstance(result, (int, float)):
                return result <= 0  # Disproven if non-positive
            logger.warning(
                "Claim '%s' matched 'always positive' but result is %s, not numeric. "
                "Cannot evaluate; returning False.",
                claim_text,
                type(result).__name__,
            )
            return False

        # Check for "always returns negative" claims
        if "negative" in claim_lower and "always" in claim_lower:
            if isinstance(result, (int, float)):
                return result >= 0  # Disproven if non-negative
            logger.warning(
                "Claim '%s' matched 'always negative' but result is %s, not numeric. "
                "Cannot evaluate; returning False.",
                claim_text,
                type(result).__name__,
            )
            return False

        # Check for "always returns True" claims
        if "true" in claim_lower and "always" in claim_lower:
            return result is not True

        # Check for "always returns False" claims
        if "false" in claim_lower and "always" in claim_lower:
            return result is not False

        # Check for "never returns None" claims
        if "never" in claim_lower and "none" in claim_lower:
            return result is None

        # Check for "always greater than" claims
        gt_match = re.search(
            r"always\s+(?:returns?\s+)?(?:a\s+value\s+)?greater\s+than\s+(-?\d+)",
            claim_lower,
        )
        if gt_match:
            threshold = int(gt_match.group(1))
            if isinstance(result, (int, float)):
                return result <= threshold
            logger.warning(
                "Claim '%s' matched 'always greater than %s' but result is %s, not numeric. "
                "Cannot evaluate; returning False.",
                claim_text,
                threshold,
                type(result).__name__,
            )
            return False

        # Check for "always less than" claims
        lt_match = re.search(
            r"always\s+(?:returns?\s+)?(?:a\s+value\s+)?less\s+than\s+(-?\d+)",
            claim_lower,
        )
        if lt_match:
            threshold = int(lt_match.group(1))
            if isinstance(result, (int, float)):
                return result >= threshold
            logger.warning(
                "Claim '%s' matched 'always less than %s' but result is %s, not numeric. "
                "Cannot evaluate; returning False.",
                claim_text,
                threshold,
                type(result).__name__,
            )
            return False

        # Default: can't determine, mark as not disproven
        logger.warning(
            "Unrecognized claim pattern: '%s'. Result was: %r. "
            "Add a claim_predicate to this RefuteProblem for reliable evaluation.",
            claim_text,
            result,
        )
        return False

    def _serialize_result(self, result: Any) -> Any:
        """Serialize result for JSON storage."""
        # Handle common types
        if result is None or isinstance(result, (bool, int, float, str)):
            return result
        if isinstance(result, (list, tuple)):
            return [self._serialize_result(item) for item in result]
        if isinstance(result, dict):
            return {str(k): self._serialize_result(v) for k, v in result.items()}
        # Fallback to string representation
        return str(result)

    # --- Grading ---

    def calculate_grade(self, submission: "Submission") -> str:
        """
        Calculate grade for refute submission.

        Binary grading: complete if counterexample found, incomplete otherwise.
        """
        if submission.passed_all_tests:
            return "complete"
        return "incomplete"

    def is_correct(self, submission: "Submission") -> bool:
        """Check if refute submission found a valid counterexample."""
        return submission.passed_all_tests

    # --- Completion Evaluation ---

    def evaluate_completion(
        self, submission: "Submission", problem: "RefuteProblem"
    ) -> str:
        """
        Evaluate completion status for progress tracking.

        For Refute: Just check if counterexample was found.
        """
        if submission.passed_all_tests:
            return "complete"
        return "incomplete"

    # --- Data Extraction ---

    def extract_variations(self, submission: "Submission") -> list[str]:
        """Extract variations from refute submission (returns single input)."""
        return [submission.raw_input] if submission.raw_input else []

    def extract_test_results(
        self, submission: "Submission", problem: "RefuteProblem"
    ) -> list[dict[str, Any]]:
        """Extract test results for refute (single result)."""
        # Parse type-specific data if available
        try:
            if (
                hasattr(submission, "type_specific_data")
                and submission.type_specific_data
            ):
                data = submission.type_specific_data
            else:
                data = {}
        except (json.JSONDecodeError, AttributeError):
            data = {}

        return [
            {
                "isSuccessful": submission.passed_all_tests,
                "input_args": data.get("input_args", {}),
                "result_value": data.get("result_value"),
                "claim_disproven": data.get("claim_disproven", False),
                "execution_error": data.get("execution_error"),
            }
        ]

    def count_variations(self, submission: "Submission") -> int:
        """Refute has exactly 1 variation (the input provided)."""
        return 1

    def count_passing_variations(self, submission: "Submission") -> int:
        """Refute has 1 passing if counterexample found, 0 otherwise."""
        return 1 if submission.passed_all_tests else 0

    # --- API Configuration ---

    def get_problem_config(self, problem: "RefuteProblem") -> dict[str, Any]:
        """Return configuration for frontend rendering of Refute problems."""
        refute = _ensure_refute_problem(problem)

        # Parse parameters from signature
        params = _parse_function_args(refute.function_signature)

        return {
            "display": {
                "show_reference_code": True,
                "code_read_only": True,
                "show_function_signature": True,
                "show_claim": True,
                "section_label": "Find a counterexample",
                # Include claim and function info for frontend rendering
                "claim_text": refute.claim_text,
                "function_signature": refute.function_signature,
                "function_name": _extract_function_name(refute.function_signature),
            },
            "input": {
                "type": "json",
                "label": "Enter function arguments as JSON",
                "placeholder": self._generate_placeholder(params),
                "parameters": params,
            },
            "hints": {
                "available": [],
                "enabled": bool(refute.expected_counterexample),
            },
            "feedback": {
                "show_variations": False,
                "show_segmentation": False,
                "show_test_results": True,
                "show_execution_result": True,
            },
        }

    def _generate_placeholder(self, params: list[dict[str, str]]) -> str:
        """Generate a placeholder example for the input field."""
        if not params:
            return "{}"

        examples = []
        for param in params:
            name = param["name"]
            type_hint = param["type"].lower()

            if "int" in type_hint:
                examples.append(f'"{name}": 0')
            elif "float" in type_hint:
                examples.append(f'"{name}": 0.0')
            elif "str" in type_hint:
                examples.append(f'"{name}": ""')
            elif "bool" in type_hint:
                examples.append(f'"{name}": true')
            elif "list" in type_hint:
                examples.append(f'"{name}": []')
            elif "dict" in type_hint:
                examples.append(f'"{name}": {{}}')
            else:
                examples.append(f'"{name}": null')

        return "{" + ", ".join(examples) + "}"

    def serialize_result(self, submission: "Submission") -> dict[str, Any]:
        """Serialize refute submission result for API response."""
        refute = _ensure_refute_problem(submission.problem)

        # Parse type-specific data
        try:
            if (
                hasattr(submission, "type_specific_data")
                and submission.type_specific_data
            ):
                data = submission.type_specific_data
            else:
                data = {}
        except (json.JSONDecodeError, AttributeError):
            data = {}

        return {
            "input_args": data.get("input_args", {}),
            "result_value": data.get("result_value"),
            "claim_disproven": data.get("claim_disproven", False),
            "execution_success": data.get("execution_success", False),
            "execution_error": data.get("execution_error"),
            "claim_text": refute.claim_text,
            "function_signature": refute.function_signature,
        }

    def test_counterexample(
        self, problem: "RefuteProblem", input_args: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Test if input values disprove the claim (for interactive frontend).

        This is a lightweight probe-like operation for the student UI.
        Unlike full submission, this doesn't create a Submission record.

        Args:
            problem: The RefuteProblem instance
            input_args: Dictionary of input parameter values

        Returns:
            Dict with result, claim_disproven, and error fields
        """
        refute = _ensure_refute_problem(problem)

        # Get function name from signature
        func_name = _extract_function_name(refute.function_signature)

        # Execute the function
        exec_result = _safe_execute(refute.reference_solution, func_name, input_args)

        if not exec_result["success"]:
            return {
                "success": False,
                "result": None,
                "claim_disproven": False,
                "error": exec_result["error"],
            }

        result_value = exec_result["result"]

        # Evaluate if claim is disproven
        claim_disproven = self._evaluate_claim(
            claim_predicate=getattr(refute, "claim_predicate", ""),
            claim_text=refute.claim_text,
            result=result_value,
            input_args=input_args,
        )

        return {
            "success": True,
            "result": self._serialize_result(result_value),
            "claim_disproven": claim_disproven,
            "error": None,
        }

    def get_admin_config(self) -> dict[str, Any]:
        """Return admin UI configuration for Refute problems."""
        return {
            "hidden_sections": ["mcq_options", "segmentation"],
            "required_fields": [
                "title",
                "question_text",
                "claim_text",
                "claim_predicate",
                "reference_solution",
                "function_signature",
            ],
            "optional_fields": ["tags", "categories", "expected_counterexample"],
            "type_specific_section": "refute_config",
            "supports": {
                "hints": True,
                "segmentation": False,
                "test_cases": False,
            },
        }

    # --- Submission Execution ---

    def submit(
        self,
        submission: "Submission",
        raw_input: str,
        problem: "RefuteProblem",
        context: dict[str, Any],
    ) -> SubmissionOutcome:
        """
        Execute refute submission synchronously.

        No Celery needed - we execute code in-process with restrictions.
        """
        refute = _ensure_refute_problem(problem)

        # Parse input
        try:
            args = json.loads(raw_input.strip())
        except json.JSONDecodeError as e:
            return SubmissionOutcome(
                complete=True, submission=submission, error=f"Invalid JSON input: {e}"
            )

        # Get function name from signature
        func_name = _extract_function_name(refute.function_signature)

        # Execute the function
        exec_result = _safe_execute(refute.reference_solution, func_name, args)

        # Determine if claim is disproven using predicate or legacy pattern matching
        if exec_result["success"]:
            claim_disproven = self._evaluate_claim(
                claim_predicate=getattr(refute, "claim_predicate", ""),
                claim_text=refute.claim_text,
                result=exec_result["result"],
                input_args=args,
            )
            result_value = self._serialize_result(exec_result["result"])
            execution_error = None
        else:
            claim_disproven = False
            result_value = None
            execution_error = exec_result["error"]

        is_correct = claim_disproven
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

        logger.info(
            f"Refute submission {submission.submission_id}: "
            f"args={args}, result={result_value}, disproven={claim_disproven}, score={score}"
        )

        # Build result data
        result_data = {
            "submission_id": str(submission.submission_id),
            "problem_type": "refute",
            "score": score,
            "is_correct": is_correct,
            "completion_status": submission.completion_status,
            "problem_slug": problem.slug,
            "user_input": raw_input,
            "input_args": args,
            "result_value": result_value,
            "claim_disproven": claim_disproven,
            "execution_success": exec_result["success"],
            "execution_error": execution_error,
            "claim_text": refute.claim_text,
            "function_signature": refute.function_signature,
            "result": self.serialize_result(submission),
        }

        return SubmissionOutcome(
            complete=True, submission=submission, result_data=result_data
        )
