"""
Repository for ProblemSetMembership model data access.
"""

from typing import Any, Dict, List, Optional

from django.db.models import Prefetch

from purplex.problems_app.models import Problem, ProblemSet, ProblemSetMembership

from .base_repository import BaseRepository


class ProblemSetMembershipRepository(BaseRepository):
    """
    Repository for all ProblemSetMembership-related database queries.

    This repository handles all data access for problem set memberships,
    managing the many-to-many relationship between problems and problem sets.
    """

    model_class = ProblemSetMembership

    @classmethod
    def create_membership(
        cls, problem_set: ProblemSet, problem: Problem, order: int = 0
    ) -> ProblemSetMembership:
        """
        Create a new membership between a problem and a problem set.

        Args:
            problem_set: The problem set
            problem: The problem to add
            order: Order of the problem in the set

        Returns:
            Created ProblemSetMembership instance
        """
        return ProblemSetMembership.objects.create(
            problem_set=problem_set, problem=problem, order=order
        )

    @classmethod
    def get_problem_memberships(cls, problem: Problem) -> List[ProblemSetMembership]:
        """
        Get all problem set memberships for a specific problem.

        Args:
            problem: The problem to get memberships for

        Returns:
            List of ProblemSetMembership instances
        """
        return list(
            ProblemSetMembership.objects.filter(problem=problem).select_related(
                "problem_set"
            )
        )

    @classmethod
    def get_problem_set_memberships(
        cls, problem_set: ProblemSet
    ) -> List[ProblemSetMembership]:
        """
        Get all memberships for a specific problem set.

        Args:
            problem_set: The problem set to get memberships for

        Returns:
            List of ProblemSetMembership instances ordered by 'order'
        """
        return list(
            ProblemSetMembership.objects.filter(problem_set=problem_set).order_by(
                "order"
            )
        )

    @classmethod
    def get_problem_set_memberships_with_categories(
        cls, problem_set: ProblemSet
    ) -> List[Dict[str, Any]]:
        """
        Get all memberships for a specific problem set with problem categories and test cases.

        Performance: Optimized with prefetch_related to avoid N+1 queries.
        Fetches problems, categories, and test cases in a single query.

        Args:
            problem_set: The problem set to get memberships for

        Returns:
            List of dicts with membership and problem data including categories and test cases
        """
        # Use Prefetch with Problem.objects.all() for proper polymorphic resolution
        # This ensures we get correct subclass instances (EiplProblem, McqProblem, etc.)
        memberships = (
            ProblemSetMembership.objects.filter(problem_set=problem_set)
            .prefetch_related(
                Prefetch("problem", queryset=Problem.objects.all()),
                "problem__categories",
                "problem__test_cases",
            )
            .order_by("order")
        )

        result = []
        for membership in memberships:
            problem = membership.problem

            # Serialize all test cases from prefetched data
            all_test_cases = problem.test_cases.all()
            test_cases_data = [
                {
                    "id": tc.id,
                    "inputs": tc.inputs,
                    "expected_output": tc.expected_output,
                    "description": tc.description,
                    "is_hidden": tc.is_hidden,
                    "is_sample": tc.is_sample,
                    "order": tc.order,
                }
                for tc in all_test_cases
            ]

            # Filter visible test cases from prefetched data (no extra query)
            visible_test_cases = [tc for tc in test_cases_data if not tc["is_hidden"]]

            # Build problem data with type-specific fields using getattr for safety
            # EiPL/Prompt have: function_name, function_signature, reference_solution, segmentation_*
            # MCQ has: question_text, options, allow_multiple
            problem_data = {
                "id": problem.id,
                "slug": problem.slug,
                "title": problem.title,
                "difficulty": problem.difficulty,
                "problem_type": problem.problem_type,
                "is_active": problem.is_active,
                "categories": [cat.name for cat in problem.categories.all()],
                "test_cases": visible_test_cases,
                "test_case_count": len(all_test_cases),
                "visible_test_case_count": len(visible_test_cases),
            }

            # Add SpecProblem fields (EiPL, Prompt) - these may not exist on MCQ
            problem_data["function_name"] = getattr(problem, "function_name", None)
            problem_data["function_signature"] = getattr(
                problem, "function_signature", None
            )
            problem_data["reference_solution"] = getattr(
                problem, "reference_solution", None
            )
            problem_data["segmentation_enabled"] = getattr(
                problem, "segmentation_enabled", False
            )
            problem_data["segmentation_config"] = getattr(
                problem, "segmentation_config", {}
            )

            # Add MCQ fields - may not exist on EiPL/Prompt
            problem_data["question_text"] = getattr(problem, "question_text", None)
            problem_data["options"] = getattr(problem, "options", None)
            problem_data["allow_multiple"] = getattr(problem, "allow_multiple", None)

            # Add Prompt-specific fields (image_url, image_alt_text)
            problem_data["image_url"] = getattr(problem, "image_url", None)
            problem_data["image_alt_text"] = getattr(problem, "image_alt_text", None)

            result.append(
                {
                    "order": membership.order,
                    "problem_obj": problem,  # Include Problem model for handler config calls
                    "problem": problem_data,
                }
            )

        return result

    @classmethod
    def count_problem_set_memberships(cls, problem_set: ProblemSet) -> int:
        """
        Count the number of memberships in a problem set.

        Args:
            problem_set: The problem set to count memberships for

        Returns:
            Number of memberships
        """
        return ProblemSetMembership.objects.filter(problem_set=problem_set).count()

    @classmethod
    def delete_problem_memberships(cls, problem: Problem) -> int:
        """
        Delete all problem set memberships for a problem.

        Args:
            problem: The problem whose memberships to delete

        Returns:
            Number of memberships deleted
        """
        deleted, _ = ProblemSetMembership.objects.filter(problem=problem).delete()
        return deleted

    @classmethod
    def delete_problem_set_memberships(cls, problem_set: ProblemSet) -> int:
        """
        Delete all memberships for a problem set.

        Args:
            problem_set: The problem set whose memberships to delete

        Returns:
            Number of memberships deleted
        """
        deleted, _ = ProblemSetMembership.objects.filter(
            problem_set=problem_set
        ).delete()
        return deleted

    @classmethod
    def membership_exists(cls, problem_set: ProblemSet, problem: Problem) -> bool:
        """
        Check if a membership exists between a problem and problem set.

        Args:
            problem_set: The problem set
            problem: The problem

        Returns:
            True if membership exists, False otherwise
        """
        return ProblemSetMembership.objects.filter(
            problem_set=problem_set, problem=problem
        ).exists()

    @classmethod
    def get_membership(
        cls, problem_set: ProblemSet, problem: Problem
    ) -> Optional[ProblemSetMembership]:
        """
        Get a specific membership between a problem and problem set.

        Args:
            problem_set: The problem set
            problem: The problem

        Returns:
            ProblemSetMembership instance or None
        """
        return ProblemSetMembership.objects.filter(
            problem_set=problem_set, problem=problem
        ).first()

    @classmethod
    def update_membership_order(
        cls, problem_set: ProblemSet, problem: Problem, new_order: int
    ) -> bool:
        """
        Update the order of a problem in a problem set.

        Args:
            problem_set: The problem set
            problem: The problem
            new_order: The new order value

        Returns:
            True if updated, False if not found
        """
        updated = ProblemSetMembership.objects.filter(
            problem_set=problem_set, problem=problem
        ).update(order=new_order)
        return updated > 0

    @classmethod
    def bulk_create_memberships(
        cls, memberships: List[Dict[str, Any]]
    ) -> List[ProblemSetMembership]:
        """
        Bulk create multiple memberships.

        Args:
            memberships: List of dicts with problem_set, problem, and order

        Returns:
            List of created ProblemSetMembership instances
        """
        membership_objects = [
            ProblemSetMembership(
                problem_set=m["problem_set"],
                problem=m["problem"],
                order=m.get("order", 0),
            )
            for m in memberships
        ]
        return list(
            ProblemSetMembership.objects.bulk_create(
                membership_objects, ignore_conflicts=True
            )
        )
