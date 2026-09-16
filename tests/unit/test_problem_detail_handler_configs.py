"""
Tests for handler-provided render configs on the single-problem endpoint.

`/api/problems/<slug>/` is what a client fetching one problem outside a problem
set uses — today that is the LMS embed. It previously returned only the model
fields, so the client had no display_config and could not render the problem's
stimulus (a prompt problem's function-call table, terminal transcript or image)
and no feedback_config to decide whether to show segmentation.

These lock in that the endpoint carries the same handler configs the
problem-set payload does.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from purplex.problems_app.services.student_service import StudentService
from tests.factories import (
    EiplProblemFactory,
    ProbeableCodeProblemFactory,
    PromptProblemFactory,
    UserFactory,
)

CONFIG_KEYS = [
    "display_config",
    "input_config",
    "hints_config",
    "feedback_config",
    "probe_config",
]


@pytest.mark.django_db
class TestGetProblemHandlerConfigs:
    """Service-level behaviour."""

    def test_returns_every_config_key_for_a_registered_type(self):
        problem = EiplProblemFactory()

        configs = StudentService.get_problem_handler_configs(problem)

        assert sorted(configs) == sorted(CONFIG_KEYS)

    def test_prompt_function_table_mode_exposes_the_table(self):
        problem = PromptProblemFactory(function_table_mode=True)

        display = StudentService.get_problem_handler_configs(problem)["display_config"]

        # The embed branches on the show_* flag, so a display_mode alone is not
        # enough — both have to be present for the table to render.
        assert display["display_mode"] == "function_table"
        assert display["show_function_table"] is True
        assert display["show_image"] is False
        assert display["display_data"]["calls"]

    def test_eipl_marks_the_reference_code_as_the_stimulus(self):
        problem = EiplProblemFactory()

        display = StudentService.get_problem_handler_configs(problem)["display_config"]

        assert display["show_reference_code"] is True

    def test_probeable_code_hides_the_reference_code(self):
        problem = ProbeableCodeProblemFactory()

        configs = StudentService.get_problem_handler_configs(problem)

        # The function is the thing the learner probes for; showing it would
        # hand over the answer.
        assert configs["display_config"]["show_reference_code"] is False
        assert configs["probe_config"]["enabled"] is True

    def test_falls_back_to_empty_configs_when_the_handler_raises(self, monkeypatch):
        problem = EiplProblemFactory()

        def boom(_problem):
            raise RuntimeError("handler exploded")

        monkeypatch.setattr(
            "purplex.problems_app.handlers.get_handler",
            lambda _type: type("H", (), {"get_problem_config": staticmethod(boom)})(),
        )

        configs = StudentService.get_problem_handler_configs(problem)

        # A broken handler must not break the problem fetch — the client gets
        # empty configs and renders no stimulus rather than a 500.
        assert configs == {key: {} for key in CONFIG_KEYS}


@pytest.mark.django_db
class TestProblemDetailEndpoint:
    """The configs have to survive the view, not just the service."""

    def _get(self, problem):
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        return client.get(reverse("problem_detail", kwargs={"slug": problem.slug}))

    def test_response_carries_the_handler_configs(self):
        problem = PromptProblemFactory(function_table_mode=True)

        response = self._get(problem)

        assert response.status_code == 200
        for key in CONFIG_KEYS:
            assert key in response.data, f"{key} missing from problem detail payload"

    def test_function_table_problem_returns_a_renderable_table(self):
        problem = PromptProblemFactory(function_table_mode=True)

        response = self._get(problem)

        display = response.data["display_config"]
        assert display["show_function_table"] is True
        assert len(display["display_data"]["calls"]) > 0
