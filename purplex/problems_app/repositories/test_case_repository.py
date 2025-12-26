"""
Repository for TestCase model data access.
"""

from typing import Any

from purplex.problems_app.models import Problem, TestCase

from .base_repository import BaseRepository


class TestCaseRepository(BaseRepository):
    """
    Repository for all TestCase-related database queries.

    This repository handles all data access for test cases,
    including retrieval, creation, and management of problem test cases.
    """

    model_class = TestCase

    @classmethod
    def get_problem_test_cases(
        cls, problem: Problem, include_hidden: bool = True
    ) -> list[TestCase]:
        """
        Get all test cases for a specific problem.

        Args:
            problem: The problem to get test cases for
            include_hidden: Whether to include hidden test cases

        Returns:
            List of test cases ordered by 'order' and 'id'
        """
        queryset = TestCase.objects.filter(problem=problem)

        if not include_hidden:
            queryset = queryset.filter(is_hidden=False)

        return list(queryset.order_by("order", "id"))

    @classmethod
    def get_visible_test_cases(cls, problem: Problem) -> list[TestCase]:
        """
        Get only visible (non-hidden) test cases for a problem.

        Args:
            problem: The problem to get test cases for

        Returns:
            List of visible test cases
        """
        return list(
            TestCase.objects.filter(problem=problem, is_hidden=False).order_by(
                "order", "id"
            )
        )

    @classmethod
    def get_sample_test_cases(cls, problem: Problem) -> list[TestCase]:
        """
        Get only sample test cases for a problem.

        Args:
            problem: The problem to get sample test cases for

        Returns:
            List of sample test cases
        """
        return list(
            TestCase.objects.filter(problem=problem, is_sample=True).order_by(
                "order", "id"
            )
        )

    @classmethod
    def get_test_case_by_id(cls, test_case_id: int) -> TestCase | None:
        """Get a specific test case by ID."""
        return TestCase.objects.filter(id=test_case_id).first()

    @classmethod
    def create_test_case(
        cls, problem: Problem, inputs: list, expected_output: Any, **kwargs
    ) -> TestCase:
        """
        Create a new test case for a problem.

        Args:
            problem: The problem this test case belongs to
            inputs: List of input arguments
            expected_output: Expected output value
            **kwargs: Additional fields (description, is_hidden, is_sample, order)

        Returns:
            Created TestCase instance
        """
        return TestCase.objects.create(
            problem=problem, inputs=inputs, expected_output=expected_output, **kwargs
        )

    @classmethod
    def bulk_create_test_cases(cls, test_cases: list[dict[str, Any]]) -> list[TestCase]:
        """
        Bulk create multiple test cases.

        Args:
            test_cases: List of dicts with test case data

        Returns:
            List of created TestCase instances
        """
        test_case_objects = [
            TestCase(
                problem=tc["problem"],
                inputs=tc["inputs"],
                expected_output=tc["expected_output"],
                description=tc.get("description", ""),
                is_hidden=tc.get("is_hidden", False),
                is_sample=tc.get("is_sample", False),
                order=tc.get("order", 0),
            )
            for tc in test_cases
        ]
        return list(TestCase.objects.bulk_create(test_case_objects))

    @classmethod
    def update_test_case(cls, test_case_id: int, **kwargs) -> bool:
        """
        Update a test case by ID.

        Args:
            test_case_id: The test case ID
            **kwargs: Fields to update

        Returns:
            True if updated, False if not found
        """
        updated = TestCase.objects.filter(id=test_case_id).update(**kwargs)
        return updated > 0

    @classmethod
    def delete_test_case(cls, test_case_id: int) -> bool:
        """
        Delete a test case by ID.

        Args:
            test_case_id: The test case ID

        Returns:
            True if deleted, False if not found
        """
        deleted, _ = TestCase.objects.filter(id=test_case_id).delete()
        return deleted > 0

    @classmethod
    def delete_problem_test_cases(cls, problem: Problem) -> int:
        """
        Delete all test cases for a problem.

        Args:
            problem: The problem whose test cases to delete

        Returns:
            Number of test cases deleted
        """
        deleted, _ = TestCase.objects.filter(problem=problem).delete()
        return deleted

    @classmethod
    def count_problem_test_cases(
        cls, problem: Problem, include_hidden: bool = True
    ) -> int:
        """
        Count test cases for a problem.

        Args:
            problem: The problem to count test cases for
            include_hidden: Whether to include hidden test cases

        Returns:
            Number of test cases
        """
        queryset = TestCase.objects.filter(problem=problem)

        if not include_hidden:
            queryset = queryset.filter(is_hidden=False)

        return queryset.count()

    @classmethod
    def count_problem_test_cases_by_id(
        cls, problem_id: int, include_hidden: bool = True
    ) -> int:
        """
        Count test cases for a problem by ID.

        Args:
            problem_id: The problem ID to count test cases for
            include_hidden: Whether to include hidden test cases

        Returns:
            Number of test cases
        """
        queryset = TestCase.objects.filter(problem_id=problem_id)

        if not include_hidden:
            queryset = queryset.filter(is_hidden=False)

        return queryset.count()

    @classmethod
    def update_test_case_order(cls, test_case_id: int, new_order: int) -> bool:
        """
        Update the order of a test case.

        Args:
            test_case_id: The test case ID
            new_order: The new order value

        Returns:
            True if updated, False if not found
        """
        updated = TestCase.objects.filter(id=test_case_id).update(order=new_order)
        return updated > 0
