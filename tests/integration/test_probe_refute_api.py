"""Integration tests for probe and refute (counterexample) API endpoints.

Validates the HTTP contract for probeable code oracle queries,
probe status/history, and refute counterexample testing.
"""

from unittest import mock

import pytest
from rest_framework import status

from purplex.problems_app.services.probe_service import ProbeService
from purplex.utils.error_codes import ErrorCode
from tests.factories import (
    EiplProblemFactory,
    ProbeableCodeProblemFactory,
    ProbeableSpecProblemFactory,
    ProblemSetMembershipFactory,
    RefuteProblemFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Field sets — from probe_views.py inline responses and frontend types
# ---------------------------------------------------------------------------

# ProbeOracleView response (probe_views.py:50-58)
PROBE_RESULT_FIELDS = {"success", "result", "error", "code", "probe_status"}

# ProbeStatusView response (probe_views.py:186-194)
PROBE_STATUS_FIELDS = {
    "mode",
    "remaining",
    "used",
    "can_probe",
    "message",
    "function_signature",
    "function_name",
    "parameters",
}

# ProbeHistoryView response (probe_views.py:250-261)
PROBE_HISTORY_FIELDS = {"history", "probe_status"}

# RefuteTestView response (probe_views.py:324-330)
REFUTE_RESULT_FIELDS = {"success", "result", "claim_disproven", "error", "code"}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def probe_url(slug):
    return f"/api/problems/{slug}/probe/"


def probe_status_url(slug):
    return f"/api/problems/{slug}/probe/status/"


def probe_history_url(slug):
    return f"/api/problems/{slug}/probe/history/"


def refute_url(slug):
    return f"/api/problems/{slug}/test-counterexample/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def probeable_problem(db):
    """A probeable code problem with a function signature."""
    return ProbeableCodeProblemFactory(
        function_signature="def add(a: int, b: int) -> int:",
        function_name="add",
        reference_solution="def add(a, b):\n    return a + b",
        is_active=True,
    )


@pytest.fixture
def hidden_signature_problem(db):
    """A probeable code problem whose signature types are hidden from students."""
    return ProbeableCodeProblemFactory(
        function_signature="def add(a: int, b: int) -> int:",
        function_name="add",
        reference_solution="def add(a, b):\n    return a + b",
        show_function_signature=False,
        is_active=True,
    )


@pytest.fixture
def refute_problem_fixture(db):
    """A refute problem for counterexample testing."""
    return RefuteProblemFactory(
        function_signature="def is_positive(n: int) -> bool:",
        is_active=True,
    )


# ===========================================================================
# TestHiddenSignaturePayload
# ===========================================================================
class TestHiddenSignaturePayload:
    """GET /api/problem-sets/{slug}/ must not leak a hidden signature."""

    def _problem_payload(self, client, problem):
        membership = ProblemSetMembershipFactory(problem=problem)
        resp = client.get(f"/api/problem-sets/{membership.problem_set.slug}/")
        assert resp.status_code == status.HTTP_200_OK
        (payload,) = resp.data["problems"]
        return payload

    def test_hidden_signature_is_withheld(
        self, authenticated_client, hidden_signature_problem
    ):
        payload = self._problem_payload(authenticated_client, hidden_signature_problem)
        assert payload["function_signature"] is None
        assert payload["probe_config"]["function_signature"] is None
        assert payload["probe_config"]["parameters"] == [
            {"name": "a", "type": ""},
            {"name": "b", "type": ""},
        ]

    def test_visible_signature_is_sent(self, authenticated_client, probeable_problem):
        payload = self._problem_payload(authenticated_client, probeable_problem)
        signature = "def add(a: int, b: int) -> int:"
        assert payload["function_signature"] == signature
        assert payload["probe_config"]["function_signature"] == signature


class TestReferenceSolutionPayload:
    """GET /api/problem-sets/{slug}/ sends reference code only where shown."""

    def _problem_payload(self, client, problem):
        membership = ProblemSetMembershipFactory(problem=problem)
        resp = client.get(f"/api/problem-sets/{membership.problem_set.slug}/")
        assert resp.status_code == status.HTTP_200_OK
        (payload,) = resp.data["problems"]
        return payload

    def test_probeable_code_oracle_is_withheld(
        self, authenticated_client, probeable_problem
    ):
        payload = self._problem_payload(authenticated_client, probeable_problem)
        assert payload["reference_solution"] is None

    def test_hidden_signature_oracle_is_withheld(
        self, authenticated_client, hidden_signature_problem
    ):
        payload = self._problem_payload(authenticated_client, hidden_signature_problem)
        assert payload["reference_solution"] is None

    def test_probeable_spec_without_segmentation_oracle_is_withheld(
        self, authenticated_client
    ):
        problem = ProbeableSpecProblemFactory(
            segmentation_config={"enabled": False}, is_active=True
        )
        payload = self._problem_payload(authenticated_client, problem)
        assert payload["feedback_config"]["show_segmentation"] is False
        assert payload["reference_solution"] is None

    def test_probeable_spec_with_segmentation_keeps_code_for_mapping(
        self, authenticated_client
    ):
        # Segment analysis maps the student's words onto the reference code.
        problem = ProbeableSpecProblemFactory(
            segmentation_config={"enabled": True}, is_active=True
        )
        payload = self._problem_payload(authenticated_client, problem)
        assert payload["feedback_config"]["show_segmentation"] is True
        assert payload["reference_solution"] == "def discover(x):\n    return x ** 2"

    def test_eipl_code_to_explain_is_sent(self, authenticated_client):
        problem = EiplProblemFactory(is_active=True)
        payload = self._problem_payload(authenticated_client, problem)
        assert payload["reference_solution"] == "def test_func(x):\n    return x * 2"


# ===========================================================================
# TestProbeStatus
# ===========================================================================
class TestProbeStatus:
    """GET /api/problems/{slug}/probe/status/"""

    def test_status_success(self, authenticated_client, probeable_problem):
        resp = authenticated_client.get(probe_status_url(probeable_problem.slug))
        assert resp.status_code == status.HTTP_200_OK

    def test_status_response_shape(self, authenticated_client, probeable_problem):
        resp = authenticated_client.get(probe_status_url(probeable_problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == PROBE_STATUS_FIELDS
        assert resp.data["function_name"] == "add"
        assert isinstance(resp.data["parameters"], list)

    def test_status_non_probeable_400(self, authenticated_client, eipl_problem):
        resp = authenticated_client.get(probe_status_url(eipl_problem.slug))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_status_nonexistent_404(self, authenticated_client):
        resp = authenticated_client.get(probe_status_url("does-not-exist"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_status_unauthenticated(self, api_client, probeable_problem):
        resp = api_client.get(probe_status_url(probeable_problem.slug))
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestProbeHistory
# ===========================================================================
class TestProbeHistory:
    """GET /api/problems/{slug}/probe/history/"""

    def test_history_success(self, authenticated_client, probeable_problem):
        resp = authenticated_client.get(probe_history_url(probeable_problem.slug))
        assert resp.status_code == status.HTTP_200_OK

    def test_history_response_shape(self, authenticated_client, probeable_problem):
        resp = authenticated_client.get(probe_history_url(probeable_problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == PROBE_HISTORY_FIELDS
        assert isinstance(resp.data["history"], list)

    def test_history_non_probeable_400(self, authenticated_client, eipl_problem):
        resp = authenticated_client.get(probe_history_url(eipl_problem.slug))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_history_nonexistent_404(self, authenticated_client):
        resp = authenticated_client.get(probe_history_url("does-not-exist"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_history_unauthenticated(self, api_client, probeable_problem):
        resp = api_client.get(probe_history_url(probeable_problem.slug))
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestProbeOracle
# ===========================================================================
class TestProbeOracle:
    """POST /api/problems/{slug}/probe/"""

    def test_probe_non_probeable_400(self, authenticated_client, eipl_problem):
        resp = authenticated_client.post(
            probe_url(eipl_problem.slug),
            {"input": {"a": 1}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_probe_nonexistent_404(self, authenticated_client):
        resp = authenticated_client.post(
            probe_url("does-not-exist"),
            {"input": {"a": 1}},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_probe_invalid_input_type_400(
        self, authenticated_client, probeable_problem
    ):
        resp = authenticated_client.post(
            probe_url(probeable_problem.slug),
            {"input": "not-a-dict"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_probe_error_response_shape(self, authenticated_client, eipl_problem):
        """Even error responses should have the expected shape."""
        resp = authenticated_client.post(
            probe_url(eipl_problem.slug),
            {"input": {"a": 1}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert set(resp.data.keys()) == PROBE_RESULT_FIELDS

    def test_probe_unauthenticated(self, api_client, probeable_problem):
        resp = api_client.post(
            probe_url(probeable_problem.slug),
            {"input": {"a": 1, "b": 2}},
            format="json",
        )
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_probe_success_round_trip(self, authenticated_client, probeable_problem):
        with mock.patch.object(ProbeService, "_record_probe") as record:
            resp = authenticated_client.post(
                probe_url(probeable_problem.slug),
                {"input": {"a": 2, "b": 3}},
                format="json",
            )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True
        assert resp.data["result"] == 5
        record.assert_called_once()

    def test_probe_type_mismatch_visible_400(
        self, authenticated_client, probeable_problem
    ):
        resp = authenticated_client.post(
            probe_url(probeable_problem.slug),
            {"input": {"a": "2", "b": 3}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert set(resp.data.keys()) == PROBE_RESULT_FIELDS
        assert resp.data["code"] == ErrorCode.INVALID_INPUT
        assert "must be an int" in resp.data["error"]

    def test_probe_type_mismatch_hidden_400(
        self, authenticated_client, hidden_signature_problem
    ):
        resp = authenticated_client.post(
            probe_url(hidden_signature_problem.slug),
            {"input": {"a": "2", "b": 3}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == ErrorCode.INVALID_INPUT
        assert resp.data["error"] == "That value is not valid for parameter 'a'"
        assert "int" not in resp.data["error"]

    def test_probe_type_mismatch_not_recorded(
        self, authenticated_client, probeable_problem
    ):
        """Rejected probes must not consume probe quota."""
        with mock.patch.object(ProbeService, "_record_probe") as record:
            resp = authenticated_client.post(
                probe_url(probeable_problem.slug),
                {"input": {"a": "abc", "b": 3}},
                format="json",
            )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        record.assert_not_called()

    def test_probe_bool_for_int_400(self, authenticated_client, probeable_problem):
        resp = authenticated_client.post(
            probe_url(probeable_problem.slug),
            {"input": {"a": True, "b": 3}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == ErrorCode.INVALID_INPUT
        assert "must be an int" in resp.data["error"]


# ===========================================================================
# TestRefuteTest
# ===========================================================================
class TestRefuteTest:
    """POST /api/problems/{slug}/test-counterexample/"""

    def test_refute_non_refute_problem_400(self, authenticated_client, eipl_problem):
        resp = authenticated_client.post(
            refute_url(eipl_problem.slug),
            {"input": {"n": -1}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_refute_error_response_shape(self, authenticated_client, eipl_problem):
        """Even error responses should have the expected shape."""
        resp = authenticated_client.post(
            refute_url(eipl_problem.slug),
            {"input": {"n": -1}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert set(resp.data.keys()) == REFUTE_RESULT_FIELDS

    def test_refute_nonexistent_404(self, authenticated_client):
        resp = authenticated_client.post(
            refute_url("does-not-exist"),
            {"input": {"n": -1}},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_refute_invalid_input_type_400(
        self, authenticated_client, refute_problem_fixture
    ):
        resp = authenticated_client.post(
            refute_url(refute_problem_fixture.slug),
            {"input": "not-a-dict"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_refute_unauthenticated(self, api_client, refute_problem_fixture):
        resp = api_client.post(
            refute_url(refute_problem_fixture.slug),
            {"input": {"n": -1}},
            format="json",
        )
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_refute_type_mismatch_400(
        self, authenticated_client, refute_problem_fixture
    ):
        resp = authenticated_client.post(
            refute_url(refute_problem_fixture.slug),
            {"input": {"n": "abc"}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert set(resp.data.keys()) == REFUTE_RESULT_FIELDS
        assert resp.data["code"] == ErrorCode.INVALID_INPUT
        assert "must be an int" in resp.data["error"]
