"""
Regression tests for on_delete behavior across the data model.

These lock down the current PROTECT/SET_NULL/CASCADE strategies so a
refactor can't silently change them and cause data loss in production.

Key invariant: UserProgress uses PROTECT on content FKs to preserve
analytics data. Submission does the same. Both use SET_NULL on user
for GDPR-compliant account deletion.
"""

import pytest
from django.db.models.deletion import ProtectedError

from purplex.problems_app.models import (
    CourseEnrollment,
    CourseInstructor,
    CourseProblemSet,
    ProblemHint,
    ProblemSetMembership,
    TestCase,
    UserProblemSetProgress,
    UserProgress,
)
from purplex.submissions.models import (
    CodeVariation,
    HintActivation,
    SegmentationAnalysis,
    SubmissionFeedback,
    TestExecution,
)
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
    SubmissionFactory,
    TestCaseFactory,
    UserFactory,
    UserProblemSetProgressFactory,
    UserProgressFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


# ─────────────────────────────────────────────────────────────────────────────
# UserProgress — PROTECT on content, SET_NULL on user
# ─────────────────────────────────────────────────────────────────────────────


class TestUserProgressOnDelete:
    """UserProgress must PROTECT content FKs and SET_NULL on user deletion.

    Rationale: progress data is the primary analytics asset. Deleting a
    problem or course must not silently destroy all progress records.
    User deletion (GDPR) should preserve anonymised progress.
    """

    def test_protect_on_problem(self):
        """Deleting a problem with progress records raises ProtectedError."""
        progress = UserProgressFactory()
        problem = progress.problem
        with pytest.raises(ProtectedError):
            problem.delete()

    def test_protect_on_problem_set(self):
        """Deleting a problem_set with progress records raises ProtectedError."""
        ps = ProblemSetFactory()
        UserProgressFactory(problem_set=ps)
        with pytest.raises(ProtectedError):
            ps.delete()

    def test_protect_on_course(self):
        """Deleting a course with progress records raises ProtectedError."""
        course = CourseFactory()
        UserProgressFactory(course=course)
        with pytest.raises(ProtectedError):
            course.delete()

    def test_set_null_on_user(self):
        """Deleting a user nullifies the FK but preserves the progress record."""
        user = UserFactory()
        progress = UserProgressFactory(user=user)
        progress_id = progress.id

        user.delete()

        progress.refresh_from_db()
        assert progress.id == progress_id
        assert progress.user is None


# ─────────────────────────────────────────────────────────────────────────────
# UserProblemSetProgress — CASCADE (inconsistent with UserProgress)
# ─────────────────────────────────────────────────────────────────────────────


class TestUserProblemSetProgressOnDelete:
    """Documents the CASCADE vs PROTECT inconsistency between progress models.

    UserProgress.course       → PROTECT  (blocks course deletion)
    UserProblemSetProgress.course → CASCADE  (silently deleted with course)

    This means a course with UserProgress rows can't be deleted, but if it
    only has UserProblemSetProgress rows, they'll silently vanish.
    """

    def test_cascade_on_course_without_user_progress(self):
        """Deleting a course cascades UserProblemSetProgress when no UserProgress blocks it."""
        course = CourseFactory()
        psp = UserProblemSetProgressFactory(course=course)
        psp_id = psp.id

        course.delete()

        assert not UserProblemSetProgress.objects.filter(id=psp_id).exists()

    def test_course_deletion_blocked_when_user_progress_exists(self):
        """UserProgress PROTECT takes precedence over UserProblemSetProgress CASCADE."""
        course = CourseFactory()
        UserProgressFactory(course=course)
        UserProblemSetProgressFactory(course=course)

        with pytest.raises(ProtectedError):
            course.delete()

    def test_cascade_on_problem_set(self):
        """Deleting a problem_set cascades UserProblemSetProgress."""
        ps = ProblemSetFactory()
        psp = UserProblemSetProgressFactory(problem_set=ps)
        psp_id = psp.id

        # ProblemSet deletion blocked if UserProgress also references it (PROTECT)
        # So test with a problem_set that has no UserProgress
        assert not UserProgress.objects.filter(problem_set=ps).exists()
        ps.delete()
        assert not UserProblemSetProgress.objects.filter(id=psp_id).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Submission — PROTECT on content, SET_NULL on user
# ─────────────────────────────────────────────────────────────────────────────


class TestSubmissionOnDelete:
    """Submission mirrors UserProgress: PROTECT content, SET_NULL user."""

    def test_protect_on_problem(self):
        sub = SubmissionFactory()
        with pytest.raises(ProtectedError):
            sub.problem.delete()

    def test_protect_on_problem_set(self):
        sub = SubmissionFactory()
        with pytest.raises(ProtectedError):
            sub.problem_set.delete()

    def test_protect_on_course(self):
        course = CourseFactory()
        SubmissionFactory(course=course)
        with pytest.raises(ProtectedError):
            course.delete()

    def test_set_null_on_user(self):
        user = UserFactory()
        sub = SubmissionFactory(user=user)
        sub_id = sub.id

        user.delete()

        sub.refresh_from_db()
        assert sub.id == sub_id
        assert sub.user is None


# ─────────────────────────────────────────────────────────────────────────────
# Cascade chains — verify child records are cleaned up
# ─────────────────────────────────────────────────────────────────────────────


class TestSubmissionCascadeChain:
    """Deleting a Submission must cascade to all child records."""

    def test_cascade_deletes_all_children(self):
        sub = SubmissionFactory()
        problem = sub.problem
        tc = TestCaseFactory(problem=problem)

        # Create child records
        TestExecution.objects.create(
            submission=sub,
            test_case=tc,
            execution_order=0,
            passed=True,
            input_values=[1],
            expected_output=2,
        )
        CodeVariationFactory(submission=sub)
        HintActivationFactory(submission=sub)
        SegmentationAnalysis.objects.create(
            submission=sub,
            segment_count=2,
            comprehension_level="relational",
            segments=[{"description": "test"}],
            code_mappings={"1": "a"},
            confidence_score=0.9,
            processing_time_ms=100,
            feedback_message="Good",
        )
        SubmissionFeedback.objects.create(
            submission=sub,
            feedback_type="praise",
            message="Well done",
        )

        sub_id = sub.id
        sub.delete()

        assert not TestExecution.objects.filter(submission_id=sub_id).exists()
        assert not CodeVariation.objects.filter(submission_id=sub_id).exists()
        assert not HintActivation.objects.filter(submission_id=sub_id).exists()
        assert not SegmentationAnalysis.objects.filter(submission_id=sub_id).exists()
        assert not SubmissionFeedback.objects.filter(submission_id=sub_id).exists()


class TestProblemCascadeChain:
    """Deleting a Problem (with no submissions/progress) cascades children."""

    def test_cascade_deletes_test_cases_and_hints(self):
        problem = EiplProblemFactory()
        tc = TestCaseFactory(problem=problem)
        hint = ProblemHintFactory(problem=problem)
        membership = ProblemSetMembershipFactory(problem=problem)

        tc_id, hint_id, membership_id = tc.id, hint.id, membership.id
        problem.delete()

        assert not TestCase.objects.filter(id=tc_id).exists()
        assert not ProblemHint.objects.filter(id=hint_id).exists()
        assert not ProblemSetMembership.objects.filter(id=membership_id).exists()


class TestCourseCascadeChain:
    """Deleting a Course (with no submissions/progress) cascades children."""

    def test_cascade_deletes_enrollments_and_problem_sets(self):
        course = CourseFactory()
        instructor_rel = CourseInstructorFactory(
            course=course, user=UserFactory(), role="primary"
        )
        enrollment = CourseEnrollmentFactory(course=course)
        cps = CourseProblemSetFactory(course=course)

        ci_id, enrollment_id, cps_id = instructor_rel.id, enrollment.id, cps.id
        course.delete()

        assert not CourseInstructor.objects.filter(id=ci_id).exists()
        assert not CourseEnrollment.objects.filter(id=enrollment_id).exists()
        assert not CourseProblemSet.objects.filter(id=cps_id).exists()
