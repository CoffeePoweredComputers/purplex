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
    CourseInstructor,
    CourseProblemSet,
    DebugFixProblem,
    EiplProblem,
    McqProblem,
    ProbeableCodeProblem,
    ProbeableSpecProblem,
    ProblemCategory,
    ProblemHint,
    ProblemSet,
    ProblemSetMembership,
    PromptProblem,
    RefuteProblem,
    TestCase,
    UserProgress,
)
from purplex.users_app.models import (
    AgeVerification,
    ConsentMethod,
    ConsentType,
    DataAccessAuditLog,
    DataPrincipalNominee,
    UserConsent,
    UserProfile,
    VerificationMethod,
)

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
    role = "user"  # Default role; can be overridden with "admin" or "instructor"


# =============================================================================
# Privacy & Consent Factories
# =============================================================================


class UserConsentFactory(DjangoModelFactory):
    """Factory for UserConsent model (append-only audit trail)."""

    class Meta:
        model = UserConsent

    user = factory.SubFactory(UserFactory)
    consent_type = ConsentType.PRIVACY_POLICY
    granted = True
    ip_address = "127.0.0.1"
    policy_version = "1.0"
    consent_method = ConsentMethod.REGISTRATION


class AgeVerificationFactory(DjangoModelFactory):
    """Factory for AgeVerification model (COPPA/DPDPA compliance)."""

    class Meta:
        model = AgeVerification

    user = factory.SubFactory(UserFactory)
    is_minor = False
    is_child = False
    verification_method = VerificationMethod.SELF_DECLARED
    parental_consent_given = False


class DataAccessAuditLogFactory(DjangoModelFactory):
    """Factory for DataAccessAuditLog model (FERPA/GDPR audit trail)."""

    class Meta:
        model = DataAccessAuditLog

    accessor = factory.SubFactory(UserFactory)
    action = "view_user_list"
    ip_address = "127.0.0.1"


class DataPrincipalNomineeFactory(DjangoModelFactory):
    """Factory for DataPrincipalNominee model (DPDPA Sec. 8(7))."""

    class Meta:
        model = DataPrincipalNominee

    user = factory.SubFactory(UserFactory)
    nominee_name = factory.Sequence(lambda n: f"Nominee {n}")
    nominee_email = factory.LazyAttribute(
        lambda o: f"{o.nominee_name.lower().replace(' ', '.')}@example.com"
    )
    nominee_relationship = "parent"


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


class DebugFixProblemFactory(DjangoModelFactory):
    """Factory for Debug Fix problems."""

    class Meta:
        model = DebugFixProblem

    title = factory.Sequence(lambda n: f"Debug Fix Problem {n}")
    slug = factory.LazyAttribute(lambda o: o.title.lower().replace(" ", "-"))
    reference_solution = "def add(a, b):\n    return a + b"
    function_signature = "def add(a: int, b: int) -> int"
    function_name = "add"
    buggy_code = (
        "def add(a, b):\n    return a - b  # Bug: subtraction instead of addition"
    )
    bug_hints = factory.LazyFunction(
        lambda: [
            {"level": 1, "text": "Check the operator"},
            {"level": 2, "text": "The function should add, not subtract"},
        ]
    )
    allow_complete_rewrite = True


class ProbeableCodeProblemFactory(DjangoModelFactory):
    """Factory for Probeable Code problems."""

    class Meta:
        model = ProbeableCodeProblem

    title = factory.Sequence(lambda n: f"Probeable Code Problem {n}")
    slug = factory.LazyAttribute(lambda o: o.title.lower().replace(" ", "-"))
    reference_solution = "def mystery(x):\n    return x * 2"
    function_signature = "def mystery(x: int) -> int"
    function_name = "mystery"
    show_function_signature = True
    probe_mode = "explore"
    max_probes = 10
    cooldown_attempts = 3
    cooldown_refill = 5


class ProbeableSpecProblemFactory(DjangoModelFactory):
    """Factory for Probeable Spec problems."""

    class Meta:
        model = ProbeableSpecProblem

    title = factory.Sequence(lambda n: f"Probeable Spec Problem {n}")
    slug = factory.LazyAttribute(lambda o: o.title.lower().replace(" ", "-"))
    reference_solution = "def discover(x):\n    return x ** 2"
    function_signature = "def discover(x: int) -> int"
    function_name = "discover"
    show_function_signature = True
    probe_mode = "cooldown"
    max_probes = 10
    cooldown_attempts = 3
    cooldown_refill = 5


class RefuteProblemFactory(DjangoModelFactory):
    """Factory for Refute (Counterexample) problems."""

    class Meta:
        model = RefuteProblem

    title = factory.Sequence(lambda n: f"Refute Problem {n}")
    slug = factory.LazyAttribute(lambda o: o.title.lower().replace(" ", "-"))
    question_text = "Find a counterexample to the claim."
    grading_mode = "deterministic"
    claim_text = "The function always returns a positive number"
    claim_predicate = "result > 0"
    reference_solution = "def f(x):\n    return x * 2"
    function_signature = "def f(x: int) -> int"
    expected_counterexample = factory.LazyFunction(lambda: {"x": -5})


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


class CourseInstructorFactory(DjangoModelFactory):
    """Factory for CourseInstructor through-table."""

    class Meta:
        model = CourseInstructor

    course = factory.SubFactory(CourseFactory)
    user = factory.SubFactory(UserFactory)
    role = "primary"
    added_by = None


class CourseEnrollmentFactory(DjangoModelFactory):
    """Factory for CourseEnrollment model."""

    class Meta:
        model = CourseEnrollment

    user = factory.SubFactory(UserFactory)
    course = factory.SubFactory(CourseFactory)


class CourseProblemSetFactory(DjangoModelFactory):
    """Factory for CourseProblemSet through model."""

    class Meta:
        model = CourseProblemSet

    course = factory.SubFactory(CourseFactory)
    problem_set = factory.SubFactory(ProblemSetFactory)
    order = factory.Sequence(lambda n: n)
    is_required = True
    due_date = None
    deadline_type = "none"
    problem_set_version = 1


class TestCaseFactory(DjangoModelFactory):
    """Factory for TestCase model."""

    class Meta:
        model = TestCase

    problem = factory.SubFactory(EiplProblemFactory)
    inputs = factory.LazyFunction(lambda: [1, 2])
    expected_output = factory.LazyFunction(lambda: 2)
    description = factory.Sequence(lambda n: f"Test case {n}")
    is_hidden = False
    is_sample = False
    order = factory.Sequence(lambda n: n)


# =============================================================================
# Hint & Progress Factories
# =============================================================================


class ProblemCategoryFactory(DjangoModelFactory):
    """Factory for ProblemCategory model."""

    class Meta:
        model = ProblemCategory

    name = factory.Sequence(lambda n: f"Category {n}")
    description = factory.LazyAttribute(lambda o: f"Description for {o.name}")


class ProblemHintFactory(DjangoModelFactory):
    """Factory for ProblemHint model."""

    class Meta:
        model = ProblemHint

    problem = factory.SubFactory(EiplProblemFactory)
    hint_type = "variable_fade"
    is_enabled = True
    min_attempts = 2
    content = factory.LazyFunction(lambda: {"mappings": []})


class UserProgressFactory(DjangoModelFactory):
    """Factory for UserProgress model."""

    class Meta:
        model = UserProgress

    user = factory.SubFactory(UserFactory)
    problem = factory.SubFactory(EiplProblemFactory)
    problem_set = factory.SubFactory(ProblemSetFactory)
    attempts = 0
    is_completed = False
