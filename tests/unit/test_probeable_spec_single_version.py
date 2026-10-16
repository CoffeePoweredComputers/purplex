"""
Probeable Spec generates one code version and shows the probeable test ladder.

``probeable_spec`` shares ``execute_eipl_pipeline`` with EiPL and Prompt, but the
student is explaining a function they discovered by probing, so the LLM turns
the explanation into a single implementation. That implementation is graded and
shown exactly like a ``probeable_code`` submission: one ordered ladder, rows up
to the first failure visible, the rest locked (#165), score = tests passed.
EiPL and Prompt keep five versions and the variation pass-rate score.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from purplex.problems_app.handlers import get_handler
from purplex.problems_app.services.ai_generation_service import (
    AITestGenerationService,
)
from purplex.problems_app.services.mock_openai import MockOpenAIClient
from tests.factories import (
    CodeVariationFactory,
    EiplProblemFactory,
    ProbeableCodeProblemFactory,
    ProbeableSpecProblemFactory,
    ProblemSetFactory,
    SubmissionFactory,
    TestCaseFactory,
    TestExecutionFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

PIPELINE = "purplex.problems_app.tasks.pipeline"


# ─── 1. Variation count is a handler property ────────────────────────────────


class TestVariationCount:
    @pytest.mark.parametrize(
        "type_name,expected",
        [("probeable_spec", 1), ("eipl", 5), ("prompt", 5)],
    )
    def test_handler_variation_count(self, type_name, expected):
        assert get_handler(type_name).variation_count == expected


def _system_prompt_for(count):
    """Run _generate_eipl_variations with the LLM call captured."""
    problem = MagicMock()
    problem.function_name = "double"
    problem.reference_solution = "def double(x):\n    return x * 2"

    service = AITestGenerationService.__new__(AITestGenerationService)
    service.client = object()
    service.model_name = "test-model"
    reply = "\n".join(
        "```python\ndef double(x):\n    return x * 2\n```" for _ in range(count)
    )
    with (
        override_settings(USE_MOCK_OPENAI=False),
        patch.object(service, "_call_ai", return_value=reply) as call,
    ):
        result = service.generate_eipl_variations(problem, "doubles x", count=count)
    return call.call_args.kwargs["messages"][0]["content"], result


class TestGenerationPrompt:
    def test_count_five_prompt_is_unchanged(self):
        prompt, result = _system_prompt_for(5)
        assert "Create five different implementations" in prompt
        assert "Each implementation MUST be different" in prompt
        assert prompt.count("def double(...)") == 5
        assert result["success"] is True
        assert len(result["variations"]) == 5

    def test_count_one_prompt_asks_for_exactly_one(self):
        prompt, result = _system_prompt_for(1)
        assert "Create exactly one implementation" in prompt
        assert "five" not in prompt
        assert "different implementations" not in prompt
        assert "MUST be different" not in prompt
        assert prompt.count("def double(...)") == 1
        assert result["success"] is True
        assert len(result["variations"]) == 1

    def test_default_count_is_five(self):
        problem = MagicMock()
        problem.function_name = "double"
        service = AITestGenerationService.__new__(AITestGenerationService)
        service.client = object()
        service.model_name = "test-model"
        with (
            override_settings(USE_MOCK_OPENAI=False),
            patch.object(service, "_call_ai", return_value="") as call,
        ):
            service.generate_eipl_variations(problem, "doubles x")
        assert (
            "Create five different" in call.call_args.kwargs["messages"][0]["content"]
        )


class TestMockLlmHonoursCount:
    @pytest.mark.parametrize("count", [1, 5])
    def test_mock_returns_requested_number_of_versions(self, count):
        problem = MagicMock()
        problem.function_name = "double"
        problem.reference_solution = "def double(x):\n    return x * 2"

        service = AITestGenerationService.__new__(AITestGenerationService)
        service.client = MockOpenAIClient()
        service.model_name = "mock-gpt"
        with override_settings(USE_MOCK_OPENAI=True):
            result = service.generate_eipl_variations(problem, "doubles", count=count)

        assert result["success"] is True
        assert len(result["variations"]) == count


# ─── Pipeline harness ────────────────────────────────────────────────────────


def _user():
    user = UserFactory()
    UserProfileFactory(user=user)
    return user


def _docker_result(passes):
    return {
        "testsPassed": sum(passes),
        "totalTests": len(passes),
        "success": all(passes),
        "results": [
            {"pass": p, "inputs": [i], "expected_output": i, "actual_output": i}
            for i, p in enumerate(passes)
        ],
    }


def _run_pipeline(problem, user, variations, docker_by_code):
    """Run execute_eipl_pipeline synchronously; LLM, Docker, Redis mocked.

    Returns (result, ai_service_mock, progress_messages).
    """
    from purplex.problems_app.tasks.pipeline import execute_eipl_pipeline

    problem_set = ProblemSetFactory()
    submission = SubmissionFactory(
        user=user,
        problem=problem,
        problem_set=problem_set,
        submission_type=problem.problem_type,
    )

    with (
        override_settings(PRIVACY_ENABLE_AI_CONSENT_GATE=False),
        patch(f"{PIPELINE}.AITestGenerationService") as mock_ai_cls,
        patch(f"{PIPELINE}.SharedDockerServiceContext") as mock_ctx,
        patch(f"{PIPELINE}.publish_progress") as mock_progress,
        patch(f"{PIPELINE}.publish_completion"),
        patch(f"{PIPELINE}.segment_prompt_helper", return_value=None),
        patch("purplex.submissions.services.ProgressService.process_submission"),
    ):
        mock_ai_cls.return_value.generate_eipl_variations.return_value = {
            "success": True,
            "variations": variations,
            "error": None,
            "model": "test",
        }
        service = MagicMock()
        service.test_solution.side_effect = lambda code, *_a, **_k: docker_by_code[code]
        mock_ctx.return_value.__enter__.return_value = service

        result = execute_eipl_pipeline.apply(
            args=[
                problem.id,
                "Explain the function in words",
                user.id,
                problem_set.id,
                None,
                str(submission.submission_id),
            ]
        ).get()

    messages = [c.args[2] for c in mock_progress.call_args_list]
    return result, mock_ai_cls.return_value, messages


def _with_tests(problem, n):
    for i in range(n):
        TestCaseFactory(problem=problem, inputs=[i], expected_output=i, order=i)
    return problem


class TestPipelineRequestsHandlerCount:
    @pytest.mark.parametrize(
        "factory,expected",
        [(ProbeableSpecProblemFactory, 1), (EiplProblemFactory, 5)],
    )
    def test_pipeline_requests_handler_variation_count(self, factory, expected):
        problem = _with_tests(
            factory(is_active=True, requires_highlevel_comprehension=False), 1
        )
        codes = [f"def f(x):\n    return x  # {i}" for i in range(expected)]
        _, ai, _ = _run_pipeline(
            problem, _user(), codes, {c: _docker_result([True]) for c in codes}
        )
        ai.generate_eipl_variations.assert_called_once()
        assert ai.generate_eipl_variations.call_args.kwargs["count"] == expected


# ─── 3. Scoring policy ───────────────────────────────────────────────────────


class TestPipelineScore:
    def test_spec_scores_tests_passed_ratio(self):
        problem = _with_tests(
            ProbeableSpecProblemFactory(
                is_active=True, requires_highlevel_comprehension=False
            ),
            4,
        )
        code = "def discover(x):\n    return x"
        result, _, messages = _run_pipeline(
            problem,
            _user(),
            [code],
            {code: _docker_result([True, True, True, False])},
        )

        assert result["score"] == 75
        assert "Submission complete! Score: 75%" in messages

    def test_eipl_scores_variation_pass_rate(self):
        problem = _with_tests(
            EiplProblemFactory(is_active=True, requires_highlevel_comprehension=False),
            4,
        )
        codes = [f"def test_func(x):\n    return x  # {i}" for i in range(5)]
        docker = {
            c: _docker_result([True] * 4 if i < 2 else [False] * 4)
            for i, c in enumerate(codes)
        }
        result, _, messages = _run_pipeline(problem, _user(), codes, docker)

        assert "Submission complete! Score: 40%" in messages
        assert result["score"] == 40

    def test_handler_score_policies(self):
        two_of_five = [
            {"success": True, "testsPassed": 4, "totalTests": 4},
            {"success": True, "testsPassed": 4, "totalTests": 4},
            {"success": False, "testsPassed": 3, "totalTests": 4},
            {"success": False, "testsPassed": 3, "totalTests": 4},
            {"success": False, "testsPassed": 3, "totalTests": 4},
        ]
        assert get_handler("eipl").score_generated_code(two_of_five) == 40
        assert get_handler("prompt").score_generated_code(two_of_five) == 40
        assert get_handler("probeable_spec").score_generated_code(two_of_five) == 85
        assert get_handler("probeable_spec").score_generated_code([]) == 0


# ─── 2. Spec payload is the probeable_code ladder ────────────────────────────


def _submission_with_ladder(problem, submission_type, passes, hidden=()):
    """One variation whose tests ran in order with the given pass pattern."""
    code = "def discover(x):\n    return x"
    submission = SubmissionFactory(
        problem=problem,
        submission_type=submission_type,
        raw_input="It returns its argument unchanged.",
        processed_code=code,
    )
    variation = CodeVariationFactory(
        submission=submission,
        variation_index=0,
        generated_code=code,
        tests_passed=sum(passes),
        tests_total=len(passes),
    )
    for order, passed in enumerate(passes):
        test_case = TestCaseFactory(
            problem=problem,
            inputs=[100 + order],
            expected_output=order,
            order=order,
            is_hidden=order in hidden,
        )
        TestExecutionFactory(
            submission=submission,
            code_variation=variation,
            test_case=test_case,
            execution_order=order,
            passed=passed,
            input_values=[100 + order],
            expected_output=order,
            actual_output=order if passed else -1,
        )
    return submission


class TestSpecLadder:
    @pytest.fixture
    def handler(self):
        return get_handler("probeable_spec")

    def test_first_failure_visible_later_tests_locked(self, handler):
        submission = _submission_with_ladder(
            ProbeableSpecProblemFactory(), "probeable_spec", (True, False, False)
        )
        entries = handler.extract_test_results(submission, submission.problem)

        assert len(entries) == 1
        entry = entries[0]
        assert [r["isSuccessful"] for r in entry["test_results"]] == [True, False]
        assert entry["results"] is entry["test_results"]
        assert entry["testsPassed"] == 1
        assert entry["totalTests"] == 3
        assert entry["success"] is False
        assert entry["lockedCount"] == 1
        assert entry["visibleCount"] == 2

    def test_hidden_test_after_first_failure_is_withheld(self, handler):
        submission = _submission_with_ladder(
            ProbeableSpecProblemFactory(),
            "probeable_spec",
            (False, True, False),
            hidden=(2,),
        )
        payload = handler.serialize_result(submission)

        assert "102" not in str(payload["test_results"])
        assert payload["test_results"][0]["lockedCount"] == 2

    def test_all_pass_locks_nothing(self, handler):
        submission = _submission_with_ladder(
            ProbeableSpecProblemFactory(), "probeable_spec", (True, True)
        )
        entry = handler.extract_test_results(submission, submission.problem)[0]

        assert entry["success"] is True
        assert entry["lockedCount"] == 0
        assert entry["visibleCount"] == 2

    def test_ladder_matches_probeable_code(self, handler):
        passes = (True, True, False, True)
        spec = _submission_with_ladder(
            ProbeableSpecProblemFactory(), "probeable_spec", passes
        )
        code = _submission_with_ladder(
            ProbeableCodeProblemFactory(function_name="discover"),
            "probeable_code",
            passes,
        )

        assert handler.extract_test_results(spec, spec.problem) == get_handler(
            "probeable_code"
        ).extract_test_results(code, code.problem)

    def test_serialize_result_has_probeable_code_shape(self, handler):
        submission = _submission_with_ladder(
            ProbeableSpecProblemFactory(), "probeable_spec", (True, False)
        )
        payload = handler.serialize_result(submission)

        assert set(payload) == {
            "student_code",
            "explanation",
            "test_results",
            "segmentation",
        }
        assert payload["student_code"] == "def discover(x):\n    return x"
        assert payload["explanation"] == "It returns its argument unchanged."
        assert payload["segmentation"] is None
        assert len(payload["test_results"]) == 1
        assert payload["test_results"][0]["lockedCount"] == 0

    def test_no_variation_yields_empty_ladder(self, handler):
        submission = SubmissionFactory(
            problem=ProbeableSpecProblemFactory(), submission_type="probeable_spec"
        )
        assert handler.extract_test_results(submission, submission.problem) == []
