"""Unit tests for the student-facing first-failure truncation rule."""

import pytest

from purplex.problems_app.handlers.result_visibility import truncate_to_first_failure

pytestmark = pytest.mark.unit


def _rows(*flags):
    return [{"isSuccessful": flag, "i": i} for i, flag in enumerate(flags)]


class TestTruncateToFirstFailure:
    def test_all_pass_nothing_locked(self):
        rows = _rows(True, True, True)
        visible, locked = truncate_to_first_failure(rows, passed_key="isSuccessful")
        assert visible == rows
        assert locked == 0

    def test_first_row_fails_only_it_is_visible(self):
        rows = _rows(False, True, False)
        visible, locked = truncate_to_first_failure(rows, passed_key="isSuccessful")
        assert visible == rows[:1]
        assert locked == 2

    @pytest.mark.parametrize("n,k", [(4, 0), (4, 1), (4, 2), (4, 3), (5, 2)])
    def test_fail_at_index_k(self, n, k):
        flags = [True] * n
        flags[k] = False
        rows = _rows(*flags)
        visible, locked = truncate_to_first_failure(rows, passed_key="isSuccessful")
        assert len(visible) == k + 1
        assert locked == n - k - 1
        assert visible == rows[: k + 1]

    def test_error_row_counts_as_failed(self):
        rows = [
            {"passed": True, "error_message": ""},
            {"passed": False, "error_message": "ZeroDivisionError"},
            {"passed": True, "error_message": ""},
        ]
        visible, locked = truncate_to_first_failure(rows, passed_key="passed")
        assert visible == rows[:2]
        assert locked == 1

    def test_empty_list(self):
        visible, locked = truncate_to_first_failure([], passed_key="passed")
        assert visible == []
        assert locked == 0
