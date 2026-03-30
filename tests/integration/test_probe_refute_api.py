"""Integration tests for probe and refute (counterexample) API endpoints.

Validates the HTTP contract for probeable code oracle queries,
probe status/history, and refute counterexample testing.
"""

import pytest
from rest_framework import status

from tests.factories import (
    ProbeableCodeProblemFactory,
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
def refute_problem_fixture(db):
    """A refute problem for counterexample testing."""
    return RefuteProblemFactory(
        function_signature="def is_positive(n: int) -> bool:",
        is_active=True,
    )


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
