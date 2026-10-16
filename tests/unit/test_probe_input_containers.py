"""Unit tests for container probe input validation and signature parsing.

Covers bracket-aware ``parse_function_signature`` (issue #160) and the
one-level container checks in ``validate_probe_input``: ``list[str]`` used to
accept integers silently. No database access.

Fixed-shape tuples such as ``tuple[int, str]`` are checked as shape only
(must be a JSON array); per-position checks are deliberately not done.
"""

import pytest

from purplex.problems_app.services.probe_service import (
    normalize_container_type,
    parse_function_signature,
    validate_probe_input,
)

pytestmark = [pytest.mark.unit]

HIDDEN = "That value is not valid for parameter '{}'"


class TestSignatureParsing:
    def test_dict_annotation_is_one_parameter(self):
        assert parse_function_signature("def f(m: dict[str, int], k: str)") == [
            {"name": "m", "type": "dict[str, int]"},
            {"name": "k", "type": "str"},
        ]

    def test_tuple_annotation_is_one_parameter(self):
        assert parse_function_signature("def f(p: tuple[int, str]) -> int") == [
            {"name": "p", "type": "tuple[int, str]"}
        ]

    def test_bracketed_defaults(self):
        sig = "def f(items: list[int] = [], pair: tuple = (1, 2), x: int = 5)"
        assert parse_function_signature(sig) == [
            {"name": "items", "type": "list[int] = []"},
            {"name": "pair", "type": "tuple = (1, 2)"},
            {"name": "x", "type": "int = 5"},
        ]

    def test_quoted_comma_in_default(self):
        assert parse_function_signature('def f(sep: str = ",", n: int)') == [
            {"name": "sep", "type": 'str = ","'},
            {"name": "n", "type": "int"},
        ]

    def test_untyped_default_keeps_bare_name(self):
        assert parse_function_signature("def f(x=5, y)") == [
            {"name": "x", "type": "Any"},
            {"name": "y", "type": "Any"},
        ]

    def test_untyped_default_with_colon_keeps_bare_name(self):
        assert parse_function_signature('def f(sep="a:b", n: int)') == [
            {"name": "sep", "type": "Any"},
            {"name": "n", "type": "int"},
        ]

    def test_trailing_comma_and_empty(self):
        assert parse_function_signature("def f(a: int,)") == [
            {"name": "a", "type": "int"}
        ]
        assert parse_function_signature("def f()") == []
        assert parse_function_signature("no parens") == []


class TestNormalizeContainer:
    @pytest.mark.parametrize(
        ("hint", "expected"),
        [
            ("list[int]", {"kind": "list", "item": "int"}),
            ("List[String]", {"kind": "list", "item": "str"}),
            ("set[float]", {"kind": "set", "item": "float"}),
            ("tuple[int]", {"kind": "tuple", "item": "int"}),
            ("tuple[int, ...]", {"kind": "tuple", "item": "int"}),
            ("tuple[int, str]", {"kind": "tuple", "item": None}),
            ("list", {"kind": "list", "item": None}),
            ("list[list[int]]", {"kind": "list", "item": None}),
            ("list[Any]", {"kind": "list", "item": None}),
            ("Dict[str, int]", {"kind": "dict", "key": "str", "value": "int"}),
            ("dict", {"kind": "dict", "key": None, "value": None}),
            ("list[int] = []", {"kind": "list", "item": "int"}),
        ],
    )
    def test_containers(self, hint, expected):
        assert normalize_container_type(hint) == expected

    @pytest.mark.parametrize(
        "hint",
        [
            None,
            "",
            "int",
            "Any",
            "Optional[list[int]]",
            "list[int] | None",
            "list[int] = None",
            "MyClass[int]",
        ],
    )
    def test_not_checked(self, hint):
        assert normalize_container_type(hint) is None


class TestListItems:
    def test_list_int_accepts_ints(self):
        assert validate_probe_input("def f(x: list[int])", {"x": [1, -2, 3]}) == (
            True,
            None,
        )

    def test_empty_list_accepted(self):
        assert validate_probe_input("def f(x: list[str])", {"x": []}) == (True, None)

    def test_list_int_rejects_string_item(self):
        assert validate_probe_input("def f(x: list[int])", {"x": [1, "2"]}) == (
            False,
            "Parameter 'x' must be a list of int",
        )

    def test_list_str_rejects_int_item(self):
        """The maintainer's bug: list[str] silently accepted integers."""
        ok, err = validate_probe_input(
            "def schedule(tasks: list[str])", {"tasks": ["a", 2]}
        )
        assert ok is False
        assert err == "Parameter 'tasks' must be a list of str"

    def test_list_int_rejects_bool_item(self):
        assert validate_probe_input("def f(x: list[int])", {"x": [1, True]}) == (
            False,
            "Parameter 'x' must be a list of int",
        )

    def test_list_float_accepts_ints(self):
        assert validate_probe_input("def f(x: list[float])", {"x": [1, 2.5]}) == (
            True,
            None,
        )

    @pytest.mark.parametrize("value", ["[1, 2]", 5, None, {"a": 1}])
    def test_list_rejects_non_array(self, value):
        assert validate_probe_input("def f(x: list[int])", {"x": value}) == (
            False,
            "Parameter 'x' must be a list of int",
        )

    def test_typing_alias(self):
        assert validate_probe_input("def f(x: List[str])", {"x": [1]}) == (
            False,
            "Parameter 'x' must be a list of str",
        )


class TestTupleAndSet:
    def test_tuple_of_int(self):
        assert validate_probe_input("def f(x: tuple[int, ...])", {"x": [1, 2]}) == (
            True,
            None,
        )
        assert validate_probe_input("def f(x: tuple[int])", {"x": ["a"]}) == (
            False,
            "Parameter 'x' must be a tuple of int",
        )

    def test_set_of_str(self):
        assert validate_probe_input("def f(x: set[str])", {"x": ["a", 1]}) == (
            False,
            "Parameter 'x' must be a set of str",
        )

    def test_fixed_shape_tuple_is_shape_only(self):
        sig = "def f(p: tuple[int, str], n: int)"
        assert validate_probe_input(sig, {"p": [1, "a"], "n": 2}) == (True, None)
        # Positions are not checked, only that the value is an array.
        assert validate_probe_input(sig, {"p": ["a", 1], "n": 2}) == (True, None)
        assert validate_probe_input(sig, {"p": "1,a", "n": 2}) == (
            False,
            "Parameter 'p' must be a tuple",
        )


class TestBareAndNested:
    def test_bare_list_rejects_dict(self):
        assert validate_probe_input("def f(x: list)", {"x": {"a": 1}}) == (
            False,
            "Parameter 'x' must be a list",
        )

    def test_bare_list_accepts_mixed_items(self):
        assert validate_probe_input("def f(x: list)", {"x": [1, "a", None]}) == (
            True,
            None,
        )

    def test_bare_dict_rejects_list(self):
        assert validate_probe_input("def f(x: dict)", {"x": [1]}) == (
            False,
            "Parameter 'x' must be a dict",
        )

    def test_nested_list_checked_for_shape_only(self):
        sig = "def f(x: list[list[int]])"
        assert validate_probe_input(sig, {"x": [["a"], [1]]}) == (True, None)
        assert validate_probe_input(sig, {"x": [1, 2]}) == (True, None)
        assert validate_probe_input(sig, {"x": "nope"}) == (
            False,
            "Parameter 'x' must be a list",
        )


class TestDict:
    SIG = "def f(counts: dict[str, int], label: str)"

    def test_accepts_matching(self):
        assert validate_probe_input(
            self.SIG, {"counts": {"a": 1, "b": 2}, "label": "x"}
        ) == (True, None)

    def test_rejects_bad_value(self):
        assert validate_probe_input(self.SIG, {"counts": {"a": "1"}, "label": "x"}) == (
            False,
            "Parameter 'counts' must be a dict of str to int",
        )

    def test_rejects_non_object(self):
        assert validate_probe_input(self.SIG, {"counts": [], "label": "x"}) == (
            False,
            "Parameter 'counts' must be a dict of str to int",
        )

    def test_non_str_keys_not_checkable_on_the_wire(self):
        """JSON object keys are always strings, so int keys are not checked."""
        sig = "def f(m: dict[int, str])"
        assert validate_probe_input(sig, {"m": {"1": "a"}}) == (True, None)
        assert validate_probe_input(sig, {"m": {"1": 2}}) == (
            False,
            "Parameter 'm' must be a dict of int to str",
        )

    def test_signature_order_first_mismatch(self):
        assert validate_probe_input(
            "def f(a: list[int], b: str)", {"b": 5, "a": ["x"]}
        ) == (False, "Parameter 'a' must be a list of int")


class TestHiddenAndDefaults:
    @pytest.mark.parametrize(
        ("hint", "bad_value"),
        [
            ("list[str]", [1]),
            ("list", {"a": 1}),
            ("dict[str, int]", {"a": "b"}),
            ("tuple[int, str]", "x"),
        ],
    )
    def test_hidden_message_is_generic(self, hint, bad_value):
        ok, err = validate_probe_input(
            f"def f(tasks: {hint})", {"tasks": bad_value}, reveal_types=False
        )
        assert ok is False
        assert err == HIDDEN.format("tasks")
        for word in ("list", "dict", "tuple", "int", "str"):
            assert word not in err

    def test_default_with_brackets_still_checked(self):
        sig = "def f(items: list[int] = [], n: int = 0)"
        assert validate_probe_input(sig, {"items": [1], "n": 2}) == (True, None)
        assert validate_probe_input(sig, {"items": ["a"], "n": 2}) == (
            False,
            "Parameter 'items' must be a list of int",
        )

    def test_none_default_is_unchecked(self):
        sig = "def f(items: list[int] = None)"
        assert validate_probe_input(sig, {"items": None}) == (True, None)
        assert validate_probe_input(sig, {"items": ["a"]}) == (True, None)

    def test_name_checks_still_first(self):
        assert validate_probe_input(
            "def f(m: dict[str, int], k: str)", {"m": "bad"}
        ) == (False, "Missing required parameters: k")
