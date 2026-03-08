"""
Regression tests for unique_together constraints (Change 3, P1).

Each test creates a valid record, then attempts a duplicate inside
transaction.atomic() and expects IntegrityError. These must pass
both before (unique_together) and after (UniqueConstraint) the migration.
"""

import pytest
from django.db import IntegrityError, transaction

from purplex.problems_app.models import (
    CourseEnrollment,
    CourseInstructor,
    CourseProblemSet,
    ProblemHint,
    ProblemSetMembership,
    ProgressSnapshot,
    UserProblemSetProgress,
    UserProgress,
)
from purplex.submissions.models import CodeVariation, HintActivation
from tests.factories import (
    CodeVariationFactory,
    CourseEnrollmentFactory,
    CourseFactory,
    CourseInstructorFactory,
    CourseProblemSetFactory,
    EiplProblemFactory,
    HintActivationFactory,
    ProblemHintFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    UserFactory,
    UserProblemSetProgressFactory,
    UserProgressFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestCourseProblemSetUniqueness:
    def test_duplicate_course_problem_set_raises(self):
        cps = CourseProblemSetFactory()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                CourseProblemSet.objects.create(
                    course=cps.course,
                    problem_set=cps.problem_set,
                    order=99,
                )


class TestCourseEnrollmentUniqueness:
    def test_duplicate_enrollment_raises(self):
        enrollment = CourseEnrollmentFactory()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                CourseEnrollment.objects.create(
                    user=enrollment.user,
                    course=enrollment.course,
                )


class TestCourseInstructorUniqueness:
    def test_duplicate_instructor_raises(self):
        ci = CourseInstructorFactory()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                CourseInstructor.objects.create(
                    course=ci.course,
                    user=ci.user,
                    role="ta",
                )


class TestProblemSetMembershipUniqueness:
    def test_duplicate_membership_raises(self):
        membership = ProblemSetMembershipFactory()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProblemSetMembership.objects.create(
                    problem_set=membership.problem_set,
                    problem=membership.problem,
                    order=99,
                )


class TestProblemHintUniqueness:
    def test_duplicate_problem_hint_type_raises(self):
        hint = ProblemHintFactory()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProblemHint.objects.create(
                    problem=hint.problem,
                    hint_type=hint.hint_type,
                    content={"mappings": []},
                )


class TestUserProgressUniqueness:
    def test_duplicate_progress_raises(self):
        """Use non-null course to avoid PostgreSQL NULL != NULL bypass."""
        course = CourseFactory()
        progress = UserProgressFactory(course=course)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                UserProgress.objects.create(
                    user=progress.user,
                    problem=progress.problem,
                    problem_set=progress.problem_set,
                    course=course,
                )

    def test_null_course_duplicates_allowed(self):
        """PostgreSQL: NULL != NULL in unique_together, so duplicates pass.

        This documents current behavior. If Change 3 migrates to
        UniqueConstraint with condition=Q(course__isnull=False), this
        test should still pass (NULLs remain unrestricted).
        """
        user = UserFactory()
        problem = EiplProblemFactory()
        ps = ProblemSetFactory()
        UserProgress.objects.create(
            user=user,
            problem=problem,
            problem_set=ps,
            course=None,
        )
        # Second record with same fields + NULL course: no error
        UserProgress.objects.create(
            user=user,
            problem=problem,
            problem_set=ps,
            course=None,
        )


class TestUserProblemSetProgressUniqueness:
    def test_duplicate_set_progress_raises(self):
        """Use non-null course to avoid PostgreSQL NULL != NULL bypass."""
        course = CourseFactory()
        psp = UserProblemSetProgressFactory(course=course)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                UserProblemSetProgress.objects.create(
                    user=psp.user,
                    problem_set=psp.problem_set,
                    course=course,
                )

    def test_null_course_duplicates_allowed(self):
        """PostgreSQL NULL != NULL: duplicates with NULL course are allowed."""
        user = UserFactory()
        ps = ProblemSetFactory()
        UserProblemSetProgress.objects.create(
            user=user,
            problem_set=ps,
            course=None,
        )
        UserProblemSetProgress.objects.create(
            user=user,
            problem_set=ps,
            course=None,
        )


class TestProgressSnapshotUniqueness:
    def test_duplicate_snapshot_raises(self):
        """Two snapshots created in the same test share today's date (auto_now_add)."""
        user = UserFactory()
        problem = EiplProblemFactory()
        ps = ProblemSetFactory()
        ProgressSnapshot.objects.create(
            user=user,
            problem=problem,
            problem_set=ps,
            completion_percentage=50,
            problems_completed=2,
            average_score=75.0,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProgressSnapshot.objects.create(
                    user=user,
                    problem=problem,
                    problem_set=ps,
                    completion_percentage=60,
                    problems_completed=3,
                    average_score=80.0,
                )


class TestHintActivationUniqueness:
    def test_duplicate_activation_raises(self):
        ha = HintActivationFactory()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                HintActivation.objects.create(
                    submission=ha.submission,
                    hint=ha.hint,
                    activation_order=99,
                )


class TestCodeVariationUniqueness:
    def test_duplicate_variation_raises(self):
        cv = CodeVariationFactory()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                CodeVariation.objects.create(
                    submission=cv.submission,
                    variation_index=cv.variation_index,
                    generated_code="different code",
                )
