"""
Factory Boy factories for test data creation.

These factories provide consistent, reusable test data across the test suite.
Use these instead of manual Model.objects.create() calls.

Usage:
    from tests.factories import UserFactory, EiplProblemFactory

    user = UserFactory()  # Creates user with auto-generated data
    problem = EiplProblemFactory(title='Custom Title')  # Override specific fields
"""

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

from purplex.problems_app.models import (
    Course,
    CourseEnrollment,
    EiplProblem,
    McqProblem,
    ProblemSet,
    ProblemSetMembership,
    PromptProblem,
)
from purplex.users_app.models import UserProfile

User = get_user_model()


# =============================================================================
# User Factories
# =============================================================================


class UserFactory(DjangoModelFactory):
    """Factory for Django User model."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class UserProfileFactory(DjangoModelFactory):
    """Factory for UserProfile model."""

    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    firebase_uid = factory.Sequence(lambda n: f"firebase-uid-{n}")


# =============================================================================
# Problem Factories
# =============================================================================


class EiplProblemFactory(DjangoModelFactory):
    """Factory for EiPL (Explain in Plain Language) problems."""

    class Meta:
        model = EiplProblem

    title = factory.Sequence(lambda n: f"EiPL Problem {n}")
    slug = factory.LazyAttribute(lambda o: o.title.lower().replace(" ", "-"))
    reference_solution = "def test_func(x):\n    return x * 2"
    function_signature = "def test_func(x: int) -> int"
    function_name = "test_func"
    difficulty = "beginner"
    segmentation_threshold = 2


class McqProblemFactory(DjangoModelFactory):
    """Factory for Multiple Choice Question problems."""

    class Meta:
        model = McqProblem

    title = factory.Sequence(lambda n: f"MCQ Problem {n}")
    slug = factory.LazyAttribute(lambda o: o.title.lower().replace(" ", "-"))
    question_text = "What is the correct answer?"
    options = factory.LazyFunction(
        lambda: [
            {"id": "a", "text": "Option A", "is_correct": False},
            {"id": "b", "text": "Option B", "is_correct": True},
            {"id": "c", "text": "Option C", "is_correct": False},
        ]
    )
    allow_multiple = False


class PromptProblemFactory(DjangoModelFactory):
    """Factory for Prompt-based problems (image analysis)."""

    class Meta:
        model = PromptProblem

    title = factory.Sequence(lambda n: f"Prompt Problem {n}")
    slug = factory.LazyAttribute(lambda o: o.title.lower().replace(" ", "-"))
    reference_solution = 'def analyze():\n    return "result"'
    function_signature = "def analyze() -> str"
    function_name = "analyze"
    image_url = factory.Sequence(lambda n: f"https://example.com/img_{n}.png")
    image_alt_text = "A test image"


# =============================================================================
# Problem Set & Course Factories
# =============================================================================


class ProblemSetFactory(DjangoModelFactory):
    """Factory for ProblemSet model."""

    class Meta:
        model = ProblemSet

    title = factory.Sequence(lambda n: f"Problem Set {n}")
    slug = factory.LazyAttribute(lambda o: o.title.lower().replace(" ", "-"))


class ProblemSetMembershipFactory(DjangoModelFactory):
    """Factory for ProblemSetMembership (problem-to-set relationship)."""

    class Meta:
        model = ProblemSetMembership

    problem_set = factory.SubFactory(ProblemSetFactory)
    problem = factory.SubFactory(EiplProblemFactory)
    order = factory.Sequence(lambda n: n)


class CourseFactory(DjangoModelFactory):
    """Factory for Course model."""

    class Meta:
        model = Course

    course_id = factory.Sequence(lambda n: f"COURSE-{n}")
    name = factory.Sequence(lambda n: f"Test Course {n}")
    instructor = factory.SubFactory(UserFactory)


class CourseEnrollmentFactory(DjangoModelFactory):
    """Factory for CourseEnrollment model."""

    class Meta:
        model = CourseEnrollment

    user = factory.SubFactory(UserFactory)
    course = factory.SubFactory(CourseFactory)
