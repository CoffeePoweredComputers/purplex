"""
Regression tests for probe configuration fields (Change 2, P1).

Verifies that ProbeableCodeProblem and ProbeableSpecProblem share the same
5 probe-config fields with identical names and defaults. These tests must
pass both before and after extracting ProbeConfigMixin.
"""

import pytest
from django.core.exceptions import ValidationError

from tests.factories import ProbeableCodeProblemFactory, ProbeableSpecProblemFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

PROBE_FIELDS = [
    "show_function_signature",
    "probe_mode",
    "max_probes",
    "cooldown_attempts",
    "cooldown_refill",
]

PROBE_DEFAULTS = {
    "show_function_signature": True,
    "probe_mode": "explore",
    "max_probes": 10,
    "cooldown_attempts": 3,
    "cooldown_refill": 5,
}


class TestProbeableCodeProblemFields:
    """Verify probe config fields on ProbeableCodeProblem."""

    def test_probe_config_fields_exist(self):
        problem = ProbeableCodeProblemFactory()
        for field in PROBE_FIELDS:
            assert hasattr(problem, field), f"Missing field: {field}"

    def test_probe_config_defaults(self):
        problem = ProbeableCodeProblemFactory()
        for field, expected in PROBE_DEFAULTS.items():
            assert (
                getattr(problem, field) == expected
            ), f"{field}: expected {expected}, got {getattr(problem, field)}"

    def test_probe_config_custom_values(self):
        problem = ProbeableCodeProblemFactory(
            probe_mode="block",
            max_probes=20,
            cooldown_attempts=5,
            cooldown_refill=10,
            show_function_signature=False,
        )
        problem.refresh_from_db()
        assert problem.probe_mode == "block"
        assert problem.max_probes == 20
        assert problem.cooldown_attempts == 5
        assert problem.cooldown_refill == 10
        assert problem.show_function_signature is False

    def test_probe_mode_choices_valid(self):
        for mode in ("block", "cooldown", "explore"):
            problem = ProbeableCodeProblemFactory(probe_mode=mode)
            problem.refresh_from_db()
            assert problem.probe_mode == mode

    def test_cooldown_validation(self):
        problem = ProbeableCodeProblemFactory(
            probe_mode="cooldown", cooldown_attempts=0
        )
        with pytest.raises(ValidationError):
            problem.full_clean()


class TestProbeableSpecProblemFields:
    """Verify probe config fields on ProbeableSpecProblem."""

    def test_probe_config_fields_exist(self):
        problem = ProbeableSpecProblemFactory()
        for field in PROBE_FIELDS:
            assert hasattr(problem, field), f"Missing field: {field}"

    def test_probe_config_defaults(self):
        from purplex.problems_app.models import ProbeableSpecProblem

        for field, expected in PROBE_DEFAULTS.items():
            model_field = ProbeableSpecProblem._meta.get_field(field)
            assert (
                model_field.default == expected
            ), f"{field}: model default {model_field.default}, expected {expected}"

    def test_probe_config_custom_values(self):
        problem = ProbeableSpecProblemFactory(
            probe_mode="block",
            max_probes=20,
            cooldown_attempts=5,
            cooldown_refill=10,
            show_function_signature=False,
        )
        problem.refresh_from_db()
        assert problem.probe_mode == "block"
        assert problem.max_probes == 20
        assert problem.cooldown_attempts == 5
        assert problem.cooldown_refill == 10
        assert problem.show_function_signature is False

    def test_probe_mode_choices_valid(self):
        for mode in ("block", "cooldown", "explore"):
            problem = ProbeableSpecProblemFactory(probe_mode=mode)
            problem.refresh_from_db()
            assert problem.probe_mode == mode

    def test_cooldown_validation(self):
        problem = ProbeableSpecProblemFactory(
            probe_mode="cooldown", cooldown_attempts=0
        )
        with pytest.raises(ValidationError):
            problem.full_clean()


class TestProbeFieldsParity:
    """Verify both probeable types share exactly the same probe field config."""

    def test_both_types_share_same_field_names(self):
        code_problem = ProbeableCodeProblemFactory()
        spec_problem = ProbeableSpecProblemFactory()
        for field in PROBE_FIELDS:
            assert hasattr(code_problem, field), f"Code missing: {field}"
            assert hasattr(spec_problem, field), f"Spec missing: {field}"

    def test_both_types_have_same_defaults(self):
        from purplex.problems_app.models import (
            ProbeableCodeProblem,
            ProbeableSpecProblem,
        )

        for field in PROBE_FIELDS:
            code_default = ProbeableCodeProblem._meta.get_field(field).default
            spec_default = ProbeableSpecProblem._meta.get_field(field).default
            assert (
                code_default == spec_default
            ), f"{field}: Code default={code_default}, Spec default={spec_default}"
