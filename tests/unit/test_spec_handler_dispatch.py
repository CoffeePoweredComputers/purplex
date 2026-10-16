"""
Handler identity for activities graded by the shared EiPL pipeline (issue #161).

``probeable_spec`` submissions run through ``execute_eipl_pipeline`` because the
NL -> code -> test flow is identical. The completion envelope must still be built
by the submission's own handler, so ``problem_type`` and ``result`` come from
``ProbeableSpecHandler`` rather than ``EiPLHandler``. Spec also triggers the same
LLM call, so its handler must declare that it needs AI-processing consent.
"""

from unittest.mock import MagicMock, patch

import pytest

from purplex.problems_app.handlers import get_handler
from purplex.problems_app.handlers.eipl.handler import EiPLHandler
from purplex.problems_app.handlers.probeable_spec.handler import ProbeableSpecHandler
from purplex.submissions.models import Submission
from tests.factories import (
    EiplProblemFactory,
    ProbeableSpecProblemFactory,
    ProblemSetFactory,
    SubmissionFactory,
    TestCaseFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

PIPELINE = "purplex.problems_app.tasks.pipeline"

# (problem factory, expected handler type, handler class whose serializer must run)
PIPELINE_TYPES = [
    pytest.param(ProbeableSpecProblemFactory, "probeable_spec", ProbeableSpecHandler),
    pytest.param(EiplProblemFactory, "eipl", EiPLHandler),
]


def _make_problem(problem_factory):
    problem = problem_factory(
        is_active=True,
        function_name="double",
        requires_highlevel_comprehension=False,
    )
    TestCaseFactory(problem=problem, inputs=[2], expected_output=4)
    return problem


def _make_user():
    user = UserFactory()
    UserProfileFactory(user=user)
    return user


def _run_pipeline(problem, user, problem_set, submission_id=None):
    """Run execute_eipl_pipeline synchronously with LLM and Docker mocked."""
    from purplex.problems_app.tasks.pipeline import execute_eipl_pipeline

    docker_result = {
        "testsPassed": 1,
        "totalTests": 1,
        "success": True,
        "results": [
            {"pass": True, "inputs": [2], "expected_output": 4, "actual_output": 4}
        ],
    }

    with (
        patch(
            f"{PIPELINE}.generate_variations_helper",
            return_value=["def double(x):\n    return x * 2"],
        ),
        patch(f"{PIPELINE}.SharedDockerServiceContext") as mock_ctx,
        patch(f"{PIPELINE}.publish_progress"),
        patch(f"{PIPELINE}.publish_completion") as mock_completion,
        patch("purplex.submissions.services.ProgressService.process_submission"),
    ):
        service = MagicMock()
        service.test_solution.return_value = docker_result
        mock_ctx.return_value.__enter__.return_value = service

        result = execute_eipl_pipeline.apply(
            args=[
                problem.id,
                "Double the input",
                user.id,
                problem_set.id,
                None,
                submission_id,
            ]
        ).get()

    mock_completion.assert_called_once()
    return result, mock_completion.call_args.args[1]


class TestPipelineCompletionEnvelopeHandler:
    """The live pipeline must dispatch on the submission's real type."""

    @pytest.mark.parametrize(
        "problem_factory,expected_type,handler_cls", PIPELINE_TYPES
    )
    def test_envelope_uses_submission_handler(
        self, problem_factory, expected_type, handler_cls
    ):
        user = _make_user()
        problem = _make_problem(problem_factory)
        problem_set = ProblemSetFactory()
        # The view creates the row first and passes its id (handler.submit).
        submission = SubmissionFactory(
            user=user,
            problem=problem,
            problem_set=problem_set,
            submission_type=expected_type,
        )

        with patch.object(
            handler_cls,
            "serialize_result",
            autospec=True,
            side_effect=handler_cls.serialize_result,
        ) as spy:
            result, published = _run_pipeline(
                problem, user, problem_set, submission_id=str(submission.submission_id)
            )

        assert result["problem_type"] == expected_type
        assert published["problem_type"] == expected_type
        assert spy.call_count == 1
        assert {"variations", "test_results", "segmentation"} <= set(
            result["result"].keys()
        )

    def test_spec_without_submission_id_records_spec_type(self):
        """Legacy path (pipeline creates the row) must not label spec as eipl."""
        user = _make_user()
        problem = _make_problem(ProbeableSpecProblemFactory)

        result, _ = _run_pipeline(
            problem, user, ProblemSetFactory(), submission_id=None
        )

        assert result["problem_type"] == "probeable_spec"
        submission = Submission.objects.get(submission_id=result["submission_id"])
        assert submission.submission_type == "probeable_spec"


class TestCachedResultEnvelopeHandler:
    """The idempotent-retry twin must dispatch the same way as the live path."""

    @pytest.mark.parametrize(
        "problem_factory,expected_type,handler_cls", PIPELINE_TYPES
    )
    def test_cached_envelope_uses_submission_handler(
        self, problem_factory, expected_type, handler_cls
    ):
        from purplex.problems_app.tasks.pipeline import _build_cached_eipl_result

        problem = _make_problem(problem_factory)
        problem_set = ProblemSetFactory()
        submission = SubmissionFactory(
            user=_make_user(),
            problem=problem,
            problem_set=problem_set,
            submission_type=expected_type,
        )

        with patch.object(
            handler_cls,
            "serialize_result",
            autospec=True,
            side_effect=handler_cls.serialize_result,
        ) as spy:
            result = _build_cached_eipl_result(submission)

        assert result["problem_type"] == expected_type
        assert spy.call_count == 1
        assert {"variations", "test_results", "segmentation"} <= set(
            result["result"].keys()
        )


class TestRequiresAiConsent:
    """Handlers that route student input through an LLM must declare it."""

    def test_probeable_spec_requires_ai_consent(self):
        assert get_handler("probeable_spec").requires_ai_consent() is True

    def test_eipl_requires_ai_consent(self):
        assert get_handler("eipl").requires_ai_consent() is True

    def test_probeable_code_does_not_require_ai_consent(self):
        """Probeable code runs the student's own code; no LLM call."""
        assert get_handler("probeable_code").requires_ai_consent() is False
