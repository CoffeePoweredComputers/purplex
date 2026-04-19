"""
Integration tests for the AI-consent gate on POST /api/submit/.

The check runs in the view before the Submission row is created. Denial surfaces
as a structured 403 via the custom exception handler so the frontend can route
it to the in-app grant modal instead of an opaque failure.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from purplex.users_app.models import ConsentType
from tests.factories import (
    AgeVerificationFactory,
    CourseEnrollmentFactory,
    CourseFactory,
    CourseProblemSetFactory,
    EiplProblemFactory,
    McqProblemFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    TestCaseFactory,
    UserConsentFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

SUBMIT_URL = reverse("submit_activity")
EIPL_PIPELINE = "purplex.problems_app.tasks.pipeline.execute_eipl_pipeline"


def _enroll(user):
    course = CourseFactory()
    CourseEnrollmentFactory(user=user, course=course)
    problem_set = ProblemSetFactory()
    CourseProblemSetFactory(course=course, problem_set=problem_set)
    return course, problem_set


def _submit(client, problem, problem_set, course, raw_input):
    return client.post(
        SUBMIT_URL,
        {
            "problem_slug": problem.slug,
            "raw_input": raw_input,
            "problem_set_slug": problem_set.slug,
            "course_id": course.course_id,
        },
        format="json",
    )


class TestEiPLSubmissionConsentGate:
    """POST /api/submit/ must reject AI-processing submissions from users who
    haven't granted ai_processing consent, and accept them otherwise."""

    EIPL_INPUT = "This is a valid description of what the code does."

    def test_without_consent_returns_structured_403(
        self, api_client, user_without_ai_consent
    ):
        course, problem_set = _enroll(user_without_ai_consent)
        problem = EiplProblemFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)
        TestCaseFactory(problem=problem, inputs=[1], expected_output=2)

        api_client.force_authenticate(user=user_without_ai_consent)
        response = _submit(api_client, problem, problem_set, course, self.EIPL_INPUT)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == "consent_required"
        assert response.data["purpose"] == "ai_processing"
        assert "error" in response.data

    def test_with_consent_returns_202(self, api_client, user):
        course, problem_set = _enroll(user)
        UserConsentFactory(user=user, consent_type=ConsentType.AI_PROCESSING)

        problem = EiplProblemFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)
        TestCaseFactory(problem=problem, inputs=[1], expected_output=2)

        api_client.force_authenticate(user=user)

        mock_task = MagicMock(id="test-task-id")
        with patch(f"{EIPL_PIPELINE}.apply_async", return_value=mock_task):
            response = _submit(
                api_client, problem, problem_set, course, self.EIPL_INPUT
            )

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["status"] == "processing"

    def test_minor_without_parental_consent_returns_403(self, api_client, user):
        course, problem_set = _enroll(user)
        UserConsentFactory(user=user, consent_type=ConsentType.AI_PROCESSING)
        AgeVerificationFactory(user=user, is_minor=True, parental_consent_given=False)

        problem = EiplProblemFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)
        TestCaseFactory(problem=problem, inputs=[1], expected_output=2)

        api_client.force_authenticate(user=user)
        response = _submit(api_client, problem, problem_set, course, self.EIPL_INPUT)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == "consent_required"
        assert "Parental consent" in response.data["error"]

    def test_mcq_unaffected_by_missing_ai_consent(
        self, api_client, user_without_ai_consent
    ):
        """MCQ does not route through AI processing, so the gate must not fire.
        Regression guard: a bug adding the check to all submission types would
        break non-AI activities."""
        course, problem_set = _enroll(user_without_ai_consent)
        problem = McqProblemFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)

        api_client.force_authenticate(user=user_without_ai_consent)
        response = _submit(api_client, problem, problem_set, course, "b")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "complete"

    @override_settings(PRIVACY_ENABLE_AI_CONSENT_GATE=False)
    def test_gate_disabled_allows_submission(self, api_client, user_without_ai_consent):
        """With the feature flag off, submissions proceed even without consent.
        The flag exists as a kill-switch for emergencies."""
        course, problem_set = _enroll(user_without_ai_consent)
        problem = EiplProblemFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)
        TestCaseFactory(problem=problem, inputs=[1], expected_output=2)

        api_client.force_authenticate(user=user_without_ai_consent)

        mock_task = MagicMock(id="test-task-id")
        with patch(f"{EIPL_PIPELINE}.apply_async", return_value=mock_task):
            response = _submit(
                api_client, problem, problem_set, course, self.EIPL_INPUT
            )

        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_no_orphan_submission_when_consent_denied(
        self, api_client, user_without_ai_consent
    ):
        """Consent check runs BEFORE create_submission, so denial must not leave
        a dangling Submission row."""
        from purplex.submissions.models import Submission

        course, problem_set = _enroll(user_without_ai_consent)
        problem = EiplProblemFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)
        TestCaseFactory(problem=problem, inputs=[1], expected_output=2)

        api_client.force_authenticate(user=user_without_ai_consent)
        response = _submit(api_client, problem, problem_set, course, self.EIPL_INPUT)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Submission.objects.filter(user=user_without_ai_consent).count() == 0
