"""Unit tests for probe input type validation (issue #135).

Covers the primitive alias table, the per-kind value rules, hidden-signature
messages, and sanitised oracle errors in ``probe_service``. No database access.
"""

import pytest

from purplex.problems_app.services.probe_service import (
    HIDDEN_ORACLE_ERROR,
    ProbeService,
    normalize_primitive_type,
    validate_probe_input,
)

pytestmark = [pytest.mark.unit]

TYPE_NAMES = ("int", "float", "bool", "str")


def _valid(signature, probe_input, **kwargs):
    return validate_probe_input(signature, probe_input, **kwargs)


class TestHappyPath:
    def test_all_primitive_kinds_accepted(self):
        sig = "def f(a: int, b: float, c: bool, d: str) -> None"
        ok, err = _valid(sig, {"a": 1, "b": 2.5, "c": True, "d": "x"})
        assert ok is True
        assert err is None


class TestIntRule:
    @pytest.mark.parametrize("value", ["5", 1.5])
    def test_int_rejects_non_int(self, value):
        ok, err = _valid("def f(x: int)", {"x": value})
        assert ok is False
        assert err == "Parameter 'x' must be an int"

    def test_int_rejects_bool(self):
        """bool subclasses int in Python; it must still be rejected."""
        ok, err = _valid("def f(x: int)", {"x": True})
        assert ok is False
        assert err == "Parameter 'x' must be an int"

    def test_int_accepts_negative(self):
        assert _valid("def f(x: int)", {"x": -3}) == (True, None)


class TestFloatRule:
    @pytest.mark.parametrize("value", [3, 3.5])
    def test_float_accepts_numbers(self, value):
        assert _valid("def f(x: float)", {"x": value}) == (True, None)

    @pytest.mark.parametrize("value", [False, "3.5"])
    def test_float_rejects_non_numbers(self, value):
        ok, err = _valid("def f(x: float)", {"x": value})
        assert ok is False
        assert err == "Parameter 'x' must be a float"


class TestBoolRule:
    @pytest.mark.parametrize("value", [1, "true"])
    def test_bool_rejects_non_bool(self, value):
        ok, err = _valid("def f(x: bool)", {"x": value})
        assert ok is False
        assert err == "Parameter 'x' must be a bool"

    def test_bool_accepts_false(self):
        assert _valid("def f(x: bool)", {"x": False}) == (True, None)


class TestStrRule:
    @pytest.mark.parametrize("value", [5, None])
    def test_str_rejects_non_str(self, value):
        ok, err = _valid("def f(x: str)", {"x": value})
        assert ok is False
        assert err == "Parameter 'x' must be a str"

    def test_str_accepts_empty_string(self):
        assert _valid("def f(x: str)", {"x": ""}) == (True, None)


class TestAliases:
    @pytest.mark.parametrize(
        ("hint", "expected"),
        [
            ("integer", "int"),
            ("Number", "float"),
            ("BOOLEAN", "bool"),
            ("string", "str"),
            ("int = 3", "int"),
            ("  Str  ", "str"),
        ],
    )
    def test_normalize(self, hint, expected):
        assert normalize_primitive_type(hint) == expected

    @pytest.mark.parametrize(
        ("hint", "bad_value", "message"),
        [
            ("integer", "5", "Parameter 'x' must be an int"),
            ("Number", "5", "Parameter 'x' must be a float"),
            ("BOOLEAN", 1, "Parameter 'x' must be a bool"),
            ("string", 5, "Parameter 'x' must be a str"),
        ],
    )
    def test_aliases_are_checked(self, hint, bad_value, message):
        ok, err = _valid(f"def f(x: {hint})", {"x": bad_value})
        assert ok is False
        assert err == message

    def test_default_value_still_checked(self):
        ok, err = _valid("def f(x: int = 3)", {"x": "abc"})
        assert ok is False
        assert err == "Parameter 'x' must be an int"
        assert _valid("def f(x: int = 3)", {"x": 4}) == (True, None)


class TestUncheckedHints:
    @pytest.mark.parametrize(
        "signature",
        [
            "def f(x)",
            "def f(x: Any)",
            "def f(x: list[int])",
            "def f(x: dict)",
            "def f(x: Optional[int])",
            "def f(x: MyClass)",
        ],
    )
    @pytest.mark.parametrize("value", ["abc", 5, None, [1, 2], {"k": 1}])
    def test_non_primitive_hints_skipped(self, signature, value):
        assert _valid(signature, {"x": value}) == (True, None)

    @pytest.mark.parametrize("hint", [None, "", "Any", "list[int]", "Optional[int]"])
    def test_normalize_returns_none(self, hint):
        assert normalize_primitive_type(hint) is None


class TestHiddenMode:
    @pytest.mark.parametrize(
        ("hint", "bad_value"),
        [("int", "abc"), ("float", "abc"), ("bool", 1), ("str", 5)],
    )
    def test_hidden_message_names_param_not_type(self, hint, bad_value):
        ok, err = _valid(
            f"def f(count: {hint})", {"count": bad_value}, reveal_types=False
        )
        assert ok is False
        assert err == "That value is not valid for parameter 'count'"
        for type_name in TYPE_NAMES:
            assert type_name not in err

    def test_validate_input_reads_problem_flag(self):
        class _Problem:
            function_signature = "def f(x: int)"
            show_function_signature = False

        ok, err = ProbeService.validate_input(_Problem(), {"x": "abc"})
        assert ok is False
        assert err == "That value is not valid for parameter 'x'"

        _Problem.show_function_signature = True
        ok, err = ProbeService.validate_input(_Problem(), {"x": "abc"})
        assert ok is False
        assert err == "Parameter 'x' must be an int"

    def test_validate_input_defaults_to_revealing(self):
        class _Problem:
            function_signature = "def f(x: int)"

        _, err = ProbeService.validate_input(_Problem(), {"x": "abc"})
        assert err == "Parameter 'x' must be an int"


class TestNameChecksFirst:
    def test_missing_param_reported_before_type(self):
        ok, err = _valid("def f(a: int, b: int)", {"a": "bad"})
        assert ok is False
        assert err == "Missing required parameters: b"

    def test_unknown_param_reported_before_type(self):
        ok, err = _valid("def f(a: int)", {"a": "bad", "z": 1})
        assert ok is False
        assert err == "Unknown parameters: z"

    def test_first_mismatch_in_signature_order(self):
        ok, err = _valid("def f(a: int, b: str)", {"b": 5, "a": "x"})
        assert ok is False
        assert err == "Parameter 'a' must be an int"


class TestOracleErrors:
    TYPE_ERROR_CODE = "def g(x):\n    return x + 1"
    VALUE_ERROR_CODE = "def g(x):\n    return int(x)"

    def test_hidden_type_error_sanitised(self):
        result = ProbeService._execute_oracle(
            self.TYPE_ERROR_CODE, "g", {"x": "abc"}, reveal_types=False
        )
        assert result == {
            "success": False,
            "result": None,
            "error": HIDDEN_ORACLE_ERROR,
        }

    def test_hidden_value_error_sanitised(self):
        result = ProbeService._execute_oracle(
            self.VALUE_ERROR_CODE, "g", {"x": "abc"}, reveal_types=False
        )
        assert result["success"] is False
        assert result["error"] == HIDDEN_ORACLE_ERROR

    def test_visible_type_error_keeps_detail(self):
        result = ProbeService._execute_oracle(
            self.TYPE_ERROR_CODE, "g", {"x": "abc"}, reveal_types=True
        )
        assert result["success"] is False
        assert result["error"].startswith("Invalid arguments:")

    def test_visible_value_error_keeps_detail(self):
        result = ProbeService._execute_oracle(self.VALUE_ERROR_CODE, "g", {"x": "abc"})
        assert result["success"] is False
        assert "invalid literal" in result["error"]

    def test_hidden_success_unaffected(self):
        result = ProbeService._execute_oracle(
            self.TYPE_ERROR_CODE, "g", {"x": 1}, reveal_types=False
        )
        assert result == {"success": True, "result": 2, "error": None}
