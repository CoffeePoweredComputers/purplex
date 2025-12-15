"""Service layer for student-related business logic."""

import logging
from typing import TYPE_CHECKING, List

from django.http import Http404

from ..repositories import (
    ProblemCategoryRepository,
    ProblemRepository,
    ProblemSetMembershipRepository,
    TestCaseRepository,
)

# Import models only for type hints
if TYPE_CHECKING:
    from django.db.models import QuerySet

    from ..models import Problem, ProblemSet

logger = logging.getLogger(__name__)


class StudentService:
    """Handle all student-related business logic."""

    @staticmethod
    def get_active_problems(user=None) -> List["Problem"]:
        """
        Get all active problems visible to students.

        Args:
            user: Optional user for filtering (future use)

        Returns:
            List of active problems with optimized queries
        """
        return ProblemRepository.get_active_problems()

    @staticmethod
    def get_problem_detail(slug: str) -> "Problem":
        """
        Get detailed problem information for students.

        Args:
            slug: Problem slug

        Returns:
            Problem instance

        Raises:
            Http404: If problem not found or not active
        """
        problem = ProblemRepository.get_problem_by_slug(slug)
        if not problem or not problem.is_active:
            raise Http404("Problem not found")
        return problem

    @staticmethod
    def get_visible_test_cases(problem: "Problem") -> "QuerySet":
        """
        Get only non-hidden test cases for a problem.

        Args:
            problem: Problem instance

        Returns:
            QuerySet of visible test cases
        """
        return TestCaseRepository.get_visible_test_cases(problem)

    @staticmethod
    def get_public_problem_sets() -> "QuerySet":
        """
        Get all public problem sets with optimized queries.

        Returns:
            QuerySet of public problem sets
        """
        # Get all problem sets and filter for public ones
        all_sets = ProblemRepository.get_all_problem_sets()
        # Filter for public sets only
        public_sets = [ps for ps in all_sets if ps.is_public]
        return public_sets

    @staticmethod
    def get_problem_set_detail(slug: str) -> "ProblemSet":
        """
        Get detailed problem set information.

        Args:
            slug: Problem set slug

        Returns:
            ProblemSet instance with related data

        Raises:
            Http404: If problem set not found or not public
        """
        problem_set = ProblemRepository.get_problem_set_with_problems(slug)
        if not problem_set or not problem_set.is_public:
            raise Http404("Problem set not found")
        return problem_set

    @staticmethod
    def get_problem_set_problems(problem_set: "ProblemSet", user=None) -> List[dict]:
        """
        Get ordered problems for a problem set with test cases and handler configs.

        Performance: Uses prefetched data from repository to avoid N+1 queries.
        Test cases, counts, categories, and handler configs are all included.

        The handler configs (display_config, input_config, hints_config, feedback_config)
        come from each problem type's handler via get_problem_config(). This enables
        the frontend to render type-specific UI without hardcoded type checks.

        Args:
            problem_set: ProblemSet instance
            user: Optional user for progress filtering

        Returns:
            List of problem data with ordering, categories, test cases, and handler configs
        """
        from ..handlers import get_handler, is_registered

        # Get problems through the membership table to preserve order
        # Repository returns structured data with categories AND test cases (optimized)
        memberships_data = (
            ProblemSetMembershipRepository.get_problem_set_memberships_with_categories(
                problem_set
            )
        )

        problems_data = []
        for membership in memberships_data:
            problem = membership["problem"]
            problem_obj = membership[
                "problem_obj"
            ]  # Problem model instance for handler calls

            if problem["is_active"]:
                problem_data = {
                    # Core fields (all problem types)
                    "slug": problem["slug"],
                    "title": problem["title"],
                    "difficulty": problem["difficulty"],
                    "problem_type": problem["problem_type"],
                    "order": membership["order"],
                    "categories": problem["categories"],
                    # Test cases (all types)
                    "test_cases": problem["test_cases"],
                    "test_case_count": problem["test_case_count"],
                    "visible_test_case_count": problem["visible_test_case_count"],
                    # SpecProblem fields (EiPL, Prompt) - None for MCQ
                    "function_name": problem["function_name"],
                    "function_signature": problem["function_signature"],
                    "reference_solution": problem["reference_solution"],
                    "segmentation_enabled": problem["segmentation_enabled"],
                    "segmentation_config": problem["segmentation_config"],
                    # MCQ fields - None for EiPL/Prompt
                    "question_text": problem["question_text"],
                    "options": problem["options"],
                    "allow_multiple": problem["allow_multiple"],
                    # Prompt-specific fields (image_url, image_alt_text)
                    "image_url": problem["image_url"],
                    "image_alt_text": problem["image_alt_text"],
                }

                # Enrich with handler-provided configs
                # These configs tell the frontend how to render this problem type
                problem_type = problem["problem_type"]
                if is_registered(problem_type):
                    try:
                        handler = get_handler(problem_type)
                        config = handler.get_problem_config(problem_obj)
                        problem_data["display_config"] = config.get("display", {})
                        problem_data["input_config"] = config.get("input", {})
                        problem_data["hints_config"] = config.get("hints", {})
                        problem_data["feedback_config"] = config.get("feedback", {})
                        problem_data["probe_config"] = config.get("probe", {})
                    except Exception as e:
                        logger.warning(
                            f"Failed to get handler config for {problem_type}: {e}"
                        )
                        # Provide empty configs as fallback
                        problem_data["display_config"] = {}
                        problem_data["input_config"] = {}
                        problem_data["hints_config"] = {}
                        problem_data["feedback_config"] = {}
                        problem_data["probe_config"] = {}
                else:
                    # Unknown type - provide empty configs
                    problem_data["display_config"] = {}
                    problem_data["input_config"] = {}
                    problem_data["hints_config"] = {}
                    problem_data["feedback_config"] = {}
                    problem_data["probe_config"] = {}

                problems_data.append(problem_data)

        return problems_data

    @staticmethod
    def get_all_categories() -> "QuerySet":
        """
        Get all problem categories ordered by their display order.

        Returns:
            QuerySet of ProblemCategory instances
        """
        return ProblemCategoryRepository.get_all_categories()
