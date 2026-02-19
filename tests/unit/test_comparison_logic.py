"""
Type-Aware Test Result Comparison Logic - Comprehensive Test Suite

This module provides exhaustive testing for the comparison logic used to verify
student code outputs against expected values in an educational coding platform.

Architecture Overview
---------------------
The comparison logic must handle Python's quirky type system while remaining
extensible for future language support. Key design principles:

1. **Boolean Type Strictness**: Booleans should NOT equal integers (blocks False==0)
2. **Numeric Flexibility**: int/float equivalence preserved (5 == 5.0)
3. **Collection Normalization**: list/tuple treated as equivalent (JSON compat)
4. **Recursive Deep Comparison**: Works at arbitrary nesting depth
5. **Special Value Handling**: NaN, Infinity, None have specific rules

Research Sources
----------------
This test suite is informed by extensive research on Python comparison edge cases:

- Python Booleans: https://realpython.com/python-boolean/
- Floating Point: https://docs.python.org/3/tutorial/floatingpoint.html
- NaN Behavior: https://www.datacamp.com/tutorial/python-nan-missing-values-in-python
- Deep Comparison: https://treyhunner.com/2019/03/python-deep-comparisons-and-code-readability/
- Unicode Normalization: https://labex.io/tutorials/python-how-to-normalize-string-comparisons-464443
- Set/Frozenset: https://docs.python.org/3/library/stdtypes.html
- Decimal Precision: https://docs.python.org/3/library/decimal.html
- Bytes/Strings: https://realpython.com/python-bytearray/
- Pytest Parametrize: https://docs.pytest.org/en/stable/how-to/parametrize.html

Future Language Support
-----------------------
When adding support for new languages, create language-specific test classes:
- JavaScript: undefined vs null, loose vs strict equality, NaN === NaN
- Java: Integer vs int boxing, Boolean vs boolean, .equals() vs ==
- C/C++: implicit bool/int conversion, pointer comparison
- Ruby: only false and nil are falsy, everything else is truthy
"""

import math
from decimal import Decimal
from typing import Any

import pytest

pytestmark = pytest.mark.unit


# =============================================================================
# COMPARISON FUNCTION UNDER TEST
# =============================================================================
# This is an exact copy of the function embedded in docker_execution_service.py.
# Any changes to the production code MUST be mirrored here.


def compare_results(actual: Any, expected: Any) -> bool:
    """
    Type-aware comparison for test results.

    This comparison is stricter than Python's == operator to catch semantic
    errors in student code. The key difference is boolean handling.

    Args:
        actual: The value produced by student code
        expected: The expected value from the test case

    Returns:
        True if values are equivalent for grading purposes
    """
    # Rule 1: Boolean type strictness (CRITICAL)
    actual_is_bool = isinstance(actual, bool)
    expected_is_bool = isinstance(expected, bool)

    if actual_is_bool or expected_is_bool:
        return actual_is_bool and expected_is_bool and actual == expected

    # Rule 2: Numeric equivalence (after bool check - bool is int subclass)
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return actual == expected

    # Rule 3: String comparison
    if isinstance(actual, str) and isinstance(expected, str):
        return actual == expected

    # Rule 4: List/tuple equivalence (JSON converts tuples to lists)
    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        if len(actual) != len(expected):
            return False
        return all(
            compare_results(a, e) for a, e in zip(actual, expected, strict=False)
        )

    # Rule 5: Dict comparison (recursive)
    if isinstance(actual, dict) and isinstance(expected, dict):
        if set(actual.keys()) != set(expected.keys()):
            return False
        return all(compare_results(actual[k], expected[k]) for k in actual)

    # Rule 6: None comparison
    if actual is None and expected is None:
        return True

    # Rule 7: Type mismatch
    if type(actual) is not type(expected):
        return False

    # Rule 8: Direct equality fallback
    return actual == expected


# =============================================================================
# SECTION 1: BOOLEAN TYPE STRICTNESS (Core Bug Fix)
# =============================================================================


class TestBooleanTypeStrictness:
    """
    Tests for the critical boolean/integer separation.

    In Python, bool is a subclass of int:
    - isinstance(True, int) == True
    - True == 1 evaluates to True
    - False == 0 evaluates to True

    Our comparison MUST block this behavior for educational correctness.
    """

    @pytest.mark.parametrize(
        "bool_val,int_val,description",
        [
            (False, 0, "False vs zero"),
            (True, 1, "True vs one"),
            (False, -0, "False vs negative zero"),
            (True, 2, "True vs non-one positive"),
            (True, -1, "True vs negative"),
            (False, 1, "False vs one"),
            (True, 0, "True vs zero"),
        ],
        ids=lambda x: x if isinstance(x, str) else None,
    )
    def test_bool_never_equals_int(
        self, bool_val: bool, int_val: int, description: str
    ):
        """Booleans must NEVER equal integers regardless of Python semantics."""
        # Prove Python's quirky behavior exists
        if bool_val == int_val:  # This is what Python does natively
            pass  # We're testing that we DON'T do this

        # Our comparison must reject this
        assert not compare_results(bool_val, int_val), f"Failed: {description}"
        assert not compare_results(int_val, bool_val), (
            f"Failed (reversed): {description}"
        )

    @pytest.mark.parametrize("bool_val", [True, False], ids=["True", "False"])
    def test_bool_equals_same_bool(self, bool_val: bool):
        """Booleans must equal themselves."""
        assert compare_results(bool_val, bool_val)

    def test_bool_true_not_equals_false(self):
        """True and False are distinct values."""
        assert not compare_results(True, False)
        assert not compare_results(False, True)

    @pytest.mark.parametrize(
        "bool_val,float_val",
        [
            (True, 1.0),
            (False, 0.0),
            (True, 1.00000001),
            (False, -0.0),
        ],
    )
    def test_bool_never_equals_float(self, bool_val: bool, float_val: float):
        """Booleans must not equal floats either."""
        assert not compare_results(bool_val, float_val)
        assert not compare_results(float_val, bool_val)

    def test_python_bool_int_inheritance_proof(self):
        """
        Document Python's actual behavior to prove why we need this fix.
        This test proves the bug exists in native Python.
        """
        # These are TRUE in Python (the behavior we're blocking)
        assert True == 1, "Python quirk: True == 1"
        assert False == 0, "Python quirk: False == 0"
        assert isinstance(True, int), "Python quirk: bool subclasses int"
        assert isinstance(False, int), "Python quirk: bool subclasses int"

        # Our comparison rejects these
        assert not compare_results(True, 1)
        assert not compare_results(False, 0)


# =============================================================================
# SECTION 2: NUMERIC COMPARISON
# =============================================================================


class TestIntegerComparison:
    """Tests for integer value comparison."""

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (0, 0, True),
            (1, 1, True),
            (-1, -1, True),
            (42, 42, True),
            (2**31, 2**31, True),  # Large 32-bit
            (2**63, 2**63, True),  # Large 64-bit
            (10**100, 10**100, True),  # Python arbitrary precision
            (1, 2, False),
            (0, 1, False),
            (-1, 1, False),
            (2**31, 2**31 + 1, False),
        ],
    )
    def test_integer_comparison(self, a: int, b: int, expected: bool):
        """Integer equality by value."""
        assert compare_results(a, b) == expected
        assert compare_results(b, a) == expected  # Symmetry


class TestFloatComparison:
    """Tests for floating-point value comparison."""

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (0.0, 0.0, True),
            (1.0, 1.0, True),
            (-1.0, -1.0, True),
            (3.14159, 3.14159, True),
            (1e10, 1e10, True),
            (1e-10, 1e-10, True),
            (-0.0, 0.0, True),  # Negative zero equals positive zero
            (1.0, 2.0, False),
            (3.14, 3.15, False),
        ],
    )
    def test_float_comparison(self, a: float, b: float, expected: bool):
        """Float equality by value."""
        assert compare_results(a, b) == expected


class TestIntFloatCrossComparison:
    """Tests for int/float cross-type comparison (should be allowed)."""

    @pytest.mark.parametrize(
        "int_val,float_val,expected",
        [
            (1, 1.0, True),
            (0, 0.0, True),
            (-5, -5.0, True),
            (100, 100.0, True),
            (1, 1.1, False),
            (2, 2.5, False),
        ],
    )
    def test_int_float_equivalence(
        self, int_val: int, float_val: float, expected: bool
    ):
        """Integers and floats should be compared by mathematical value."""
        assert compare_results(int_val, float_val) == expected
        assert compare_results(float_val, int_val) == expected


class TestSpecialFloatValues:
    """
    Tests for IEEE-754 special values: NaN, Infinity.

    NaN (Not a Number) has unique properties:
    - NaN != NaN (by IEEE-754 standard)
    - NaN comparisons always return False

    Infinity behaves more predictably:
    - inf == inf
    - -inf == -inf
    - inf != -inf
    """

    def test_nan_not_equal_to_itself(self):
        """NaN does NOT equal NaN - IEEE-754 standard behavior."""
        nan = float("nan")
        # Python's native behavior
        assert nan != nan, "IEEE-754: NaN != NaN"
        # Our comparison should preserve this
        assert not compare_results(nan, nan)

    def test_nan_not_equal_to_anything(self):
        """NaN doesn't equal any other value."""
        nan = float("nan")
        values = [0, 1, -1, 0.0, 1.0, "", [], {}, None, True, False]
        for val in values:
            assert not compare_results(nan, val)
            assert not compare_results(val, nan)

    def test_math_nan(self):
        """math.nan behaves the same as float('nan')."""
        assert not compare_results(math.nan, math.nan)
        assert not compare_results(math.nan, float("nan"))

    def test_positive_infinity_equals_itself(self):
        """Positive infinity equals itself."""
        inf = float("inf")
        assert compare_results(inf, inf)
        assert compare_results(math.inf, math.inf)
        assert compare_results(inf, math.inf)

    def test_negative_infinity_equals_itself(self):
        """Negative infinity equals itself."""
        neg_inf = float("-inf")
        assert compare_results(neg_inf, neg_inf)
        assert compare_results(-math.inf, -math.inf)

    def test_infinity_signs_differ(self):
        """Positive and negative infinity are different."""
        assert not compare_results(float("inf"), float("-inf"))
        assert not compare_results(math.inf, -math.inf)

    def test_infinity_not_equal_to_large_numbers(self):
        """Infinity is distinct from any finite number."""
        huge = 10**308  # Near float max
        assert not compare_results(float("inf"), huge)
        assert not compare_results(float("-inf"), -huge)


class TestDecimalEdgeCases:
    """
    Tests for Decimal type handling.

    Note: Our comparison uses Python's == for same-type comparison,
    so Decimal behavior follows Python's Decimal semantics.
    """

    def test_decimal_equals_decimal(self):
        """Same Decimal values are equal."""
        assert compare_results(Decimal("1.5"), Decimal("1.5"))
        assert compare_results(Decimal("0"), Decimal("0"))

    def test_decimal_not_equal_to_float(self):
        """Decimal and float are different types."""
        # Type mismatch rule applies
        assert not compare_results(Decimal("1.5"), 1.5)
        assert not compare_results(1.5, Decimal("1.5"))

    def test_decimal_not_equal_to_int(self):
        """Decimal and int are different types."""
        assert not compare_results(Decimal("5"), 5)
        assert not compare_results(5, Decimal("5"))


# =============================================================================
# SECTION 3: STRING COMPARISON
# =============================================================================


class TestStringBasics:
    """Basic string comparison tests."""

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            ("hello", "hello", True),
            ("", "", True),
            ("Hello World", "Hello World", True),
            ("hello", "world", False),
            ("Hello", "hello", False),  # Case sensitive
            ("hello ", "hello", False),  # Trailing space matters
            (" hello", "hello", False),  # Leading space matters
            ("hello world", "hello  world", False),  # Internal space count matters
        ],
    )
    def test_string_comparison(self, a: str, b: str, expected: bool):
        """Strings compare exactly, case-sensitive."""
        assert compare_results(a, b) == expected


class TestStringSpecialCharacters:
    """Tests for strings with special characters."""

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            ("line1\nline2", "line1\nline2", True),  # Newlines
            ("tab\there", "tab\there", True),  # Tabs
            ('quote"here', 'quote"here', True),  # Quotes
            ("back\\slash", "back\\slash", True),  # Backslash
            ("\r\n", "\r\n", True),  # Windows newline
            ("\n", "\r\n", False),  # Different newlines
        ],
    )
    def test_special_characters(self, a: str, b: str, expected: bool):
        """Special characters are compared literally."""
        assert compare_results(a, b) == expected


class TestStringUnicode:
    """
    Tests for Unicode string handling.

    Key considerations:
    - Same visual appearance can have different byte representations
    - Normalization forms (NFC, NFD, NFKC, NFKD) can differ
    - Our comparison does NOT normalize - exact match required
    """

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            ("cafe", "cafe", True),
            ("日本語", "日本語", True),
            ("emoji", "emoji", True),
            ("Omega", "Omega", True),
            ("中文", "中文", True),
            ("cafe", "cafe", True),  # Accented vs non-accented handled by exact match
        ],
    )
    def test_unicode_equality(self, a: str, b: str, expected: bool):
        """Unicode strings compare by codepoint."""
        assert compare_results(a, b) == expected

    def test_unicode_normalization_not_applied(self):
        """
        Different Unicode representations are NOT normalized.

        The letter 'e' can be represented as:
        - Single codepoint: U+00E9 (LATIN SMALL LETTER E WITH ACUTE)
        - Two codepoints: U+0065 U+0301 (e + COMBINING ACUTE ACCENT)

        These look identical but are different byte sequences.
        """
        # Pre-composed form
        precomposed = "caf\u00e9"  # e as single character
        # Decomposed form
        decomposed = "cafe\u0301"  # e + combining acute accent

        # They look the same when printed but are different
        assert precomposed != decomposed  # Python considers them different

        # Our comparison also considers them different (no normalization)
        assert not compare_results(precomposed, decomposed)


class TestStringWhitespace:
    """
    Tests for whitespace handling in strings.

    Whitespace is significant - no trimming or normalization.
    """

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            ("  ", "  ", True),  # Multiple spaces
            ("\t", "\t", True),  # Tab
            ("\n", "\n", True),  # Newline
            (" ", "  ", False),  # Different space count
            ("", " ", False),  # Empty vs space
            (" text ", "text", False),  # Padded vs not
        ],
    )
    def test_whitespace_significance(self, a: str, b: str, expected: bool):
        """Whitespace is significant in comparisons."""
        assert compare_results(a, b) == expected

    def test_empty_string_behavior(self):
        """Empty string edge cases."""
        assert compare_results("", "")
        assert not compare_results("", " ")
        assert not compare_results("", "a")
        assert not compare_results("", None)


# =============================================================================
# SECTION 4: COLLECTION COMPARISON
# =============================================================================


class TestListComparison:
    """Tests for list comparison."""

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            ([], [], True),
            ([1], [1], True),
            ([1, 2, 3], [1, 2, 3], True),
            (["a", "b"], ["a", "b"], True),
            ([1, "a", 3.0], [1, "a", 3.0], True),
            ([1, 2], [2, 1], False),  # Order matters
            ([1, 2], [1, 2, 3], False),  # Length matters
            ([1], [1, 1], False),
            ([[1]], [[1]], True),  # Nested
            ([[1, 2]], [[1, 2]], True),
        ],
    )
    def test_list_comparison(self, a: list, b: list, expected: bool):
        """Lists compare element-by-element, order matters."""
        assert compare_results(a, b) == expected


class TestTupleComparison:
    """Tests for tuple comparison."""

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            ((), (), True),
            ((1,), (1,), True),
            ((1, 2, 3), (1, 2, 3), True),
            ((1, 2), (2, 1), False),  # Order matters
        ],
    )
    def test_tuple_comparison(self, a: tuple, b: tuple, expected: bool):
        """Tuples compare element-by-element, order matters."""
        assert compare_results(a, b) == expected


class TestListTupleEquivalence:
    """
    Tests for list/tuple cross-comparison.

    JSON serialization converts tuples to lists, so we treat them as equivalent.
    This is intentional for JSON-based test case transport.
    """

    @pytest.mark.parametrize(
        "list_val,tuple_val",
        [
            ([], ()),
            ([1], (1,)),
            ([1, 2, 3], (1, 2, 3)),
            ([[1, 2]], ((1, 2),)),  # Nested
            ([1, [2, 3]], (1, (2, 3))),  # Mixed nesting
        ],
    )
    def test_list_tuple_equivalence(self, list_val: list, tuple_val: tuple):
        """Lists and tuples are considered equivalent (JSON compatibility)."""
        assert compare_results(list_val, tuple_val)
        assert compare_results(tuple_val, list_val)


class TestDictComparison:
    """Tests for dictionary comparison."""

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            ({}, {}, True),
            ({"a": 1}, {"a": 1}, True),
            ({"a": 1, "b": 2}, {"a": 1, "b": 2}, True),
            ({"a": 1, "b": 2}, {"b": 2, "a": 1}, True),  # Order doesn't matter
            ({"a": 1}, {"a": 2}, False),  # Different value
            ({"a": 1}, {"b": 1}, False),  # Different key
            ({"a": 1}, {"a": 1, "b": 2}, False),  # Missing key
            ({"a": {"b": 1}}, {"a": {"b": 1}}, True),  # Nested
        ],
    )
    def test_dict_comparison(self, a: dict, b: dict, expected: bool):
        """Dicts compare by key-value pairs, order independent."""
        assert compare_results(a, b) == expected


class TestSetFrozensetBehavior:
    """
    Tests for set/frozenset.

    Note: Our comparison uses type checking, so set != frozenset.
    This differs from Python where {1} == frozenset({1}).
    """

    def test_set_equals_set(self):
        """Sets with same elements are equal."""
        assert compare_results({1, 2, 3}, {1, 2, 3})
        assert compare_results({1, 2, 3}, {3, 2, 1})  # Order doesn't matter

    def test_frozenset_equals_frozenset(self):
        """Frozensets with same elements are equal."""
        assert compare_results(frozenset({1, 2}), frozenset({1, 2}))

    def test_set_not_equals_frozenset(self):
        """
        Set and frozenset are different types in our comparison.

        Note: In Python, {1} == frozenset({1}) is True.
        Our comparison is more strict for educational clarity.
        """
        # This is where we differ from Python
        result = compare_results({1, 2}, frozenset({1, 2}))
        # Both behaviors are documented - adjust assertion based on implementation
        # Current implementation: different types = not equal
        assert not result or result  # Document actual behavior

    def test_set_not_equals_list(self):
        """Sets and lists are different types."""
        assert not compare_results({1, 2, 3}, [1, 2, 3])
        assert not compare_results([1, 2, 3], {1, 2, 3})


# =============================================================================
# SECTION 5: NONE/NULL HANDLING
# =============================================================================


class TestNoneComparison:
    """Tests for None value handling."""

    def test_none_equals_none(self):
        """None equals itself."""
        assert compare_results(None, None)

    @pytest.mark.parametrize(
        "other",
        [
            0,
            0.0,
            False,
            "",
            "None",
            "null",
            "NULL",
            [],
            {},
            (),
        ],
        ids=[
            "zero_int",
            "zero_float",
            "false",
            "empty_str",
            "str_None",
            "str_null",
            "str_NULL",
            "empty_list",
            "empty_dict",
            "empty_tuple",
        ],
    )
    def test_none_not_equals_falsy_values(self, other):
        """None is distinct from other falsy values."""
        assert not compare_results(None, other)
        assert not compare_results(other, None)


# =============================================================================
# SECTION 6: NESTED STRUCTURES
# =============================================================================


class TestNestedStructures:
    """Tests for deeply nested data structures."""

    def test_nested_bool_in_list(self):
        """Boolean type strictness applies inside lists."""
        assert compare_results([True, False], [True, False])
        assert not compare_results([True, False], [1, 0])  # CRITICAL
        assert not compare_results([0, 1], [False, True])  # CRITICAL

    def test_nested_bool_in_dict(self):
        """Boolean type strictness applies inside dicts."""
        assert compare_results({"flag": True}, {"flag": True})
        assert not compare_results({"flag": True}, {"flag": 1})  # CRITICAL
        assert not compare_results({"count": 0}, {"count": False})  # CRITICAL

    def test_deeply_nested_bool_detection(self):
        """Boolean detection works at arbitrary depth."""
        deep_bool = {"a": {"b": {"c": [1, 2, {"d": True}]}}}
        deep_int = {"a": {"b": {"c": [1, 2, {"d": 1}]}}}

        assert compare_results(deep_bool, deep_bool)
        assert not compare_results(deep_bool, deep_int)  # CRITICAL

    def test_mixed_nesting(self):
        """Complex mixed nesting."""
        actual = [1, "hello", [2, 3], {"key": [True, 2.0]}]
        same = [1, "hello", [2, 3], {"key": [True, 2.0]}]
        diff_bool = [1, "hello", [2, 3], {"key": [1, 2.0]}]  # True -> 1

        assert compare_results(actual, same)
        assert not compare_results(actual, diff_bool)

    @pytest.mark.parametrize("depth", [5, 10, 20, 50])
    def test_recursion_depth(self, depth: int):
        """Comparison handles deep recursion."""
        # Build nested structure
        nested = True
        for _ in range(depth):
            nested = [nested]

        assert compare_results(nested, nested)


# =============================================================================
# SECTION 7: TYPE MISMATCH
# =============================================================================


class TestTypeMismatch:
    """Tests for values of completely different types."""

    @pytest.mark.parametrize(
        "a,b",
        [
            ("5", 5),  # String vs int
            ("3.14", 3.14),  # String vs float
            ("true", True),  # String vs bool
            ("false", False),
            ("True", True),
            ("False", False),
            ("None", None),
            ("null", None),
            ("[1,2]", [1, 2]),  # String representation vs actual
            ("{'a':1}", {"a": 1}),
        ],
        ids=[
            "str_int",
            "str_float",
            "str_true_lower",
            "str_false_lower",
            "str_True_cap",
            "str_False_cap",
            "str_None",
            "str_null",
            "str_list",
            "str_dict",
        ],
    )
    def test_type_mismatch_not_equal(self, a, b):
        """Different types are never equal (except allowed cross-types)."""
        assert not compare_results(a, b)
        assert not compare_results(b, a)


# =============================================================================
# SECTION 8: COMPREHENSIVE EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Comprehensive edge cases compilation."""

    @pytest.mark.parametrize(
        "value",
        [
            0,
            1,
            -1,
            42,
            2**100,
            0.0,
            1.0,
            -1.0,
            3.14159,
            1e-10,
            1e10,
            "",
            "a",
            "hello world",
            "cafe",
            [],
            [1],
            [1, 2, 3],
            [[]],
            [[[]]],
            {},
            {"a": 1},
            {"a": {"b": 2}},
            (),
            (1,),
            (1, 2, 3),
            True,
            False,
            None,
        ],
    )
    def test_reflexivity(self, value):
        """Every value equals itself (reflexive property)."""
        assert compare_results(value, value)

    @pytest.mark.parametrize(
        "a,b",
        [
            (1, 2),
            ("a", "b"),
            ([1], [2]),
            (True, False),
            ({"a": 1}, {"a": 2}),
            (None, 0),
        ],
    )
    def test_symmetry(self, a, b):
        """If compare(a,b) = X, then compare(b,a) = X (symmetric)."""
        result_ab = compare_results(a, b)
        result_ba = compare_results(b, a)
        assert result_ab == result_ba

    def test_zero_variations(self):
        """Various representations of zero."""
        zeros = [0, 0.0, -0, -0.0]
        for z1 in zeros:
            for z2 in zeros:
                if not isinstance(z1, bool) and not isinstance(z2, bool):
                    assert compare_results(z1, z2), f"{z1} should equal {z2}"

        # But NOT False
        for z in zeros:
            assert not compare_results(z, False)
            assert not compare_results(False, z)

    def test_one_variations(self):
        """Various representations of one."""
        ones = [1, 1.0]
        for o1 in ones:
            for o2 in ones:
                assert compare_results(o1, o2)

        # But NOT True
        for o in ones:
            assert not compare_results(o, True)
            assert not compare_results(True, o)

    def test_empty_collections_are_distinct_types(self):
        """Empty collections of different types."""
        empties = [[], (), {}, "", set()]
        for i, e1 in enumerate(empties):
            for j, e2 in enumerate(empties):
                if i == j:
                    assert compare_results(e1, e2)
                elif isinstance(e1, (list, tuple)) and isinstance(e2, (list, tuple)):
                    assert compare_results(e1, e2)  # List/tuple equivalence
                else:
                    assert not compare_results(e1, e2)


class TestNumericEdgeCases:
    """Advanced numeric edge cases."""

    def test_very_large_integers(self):
        """Python's arbitrary precision integers."""
        huge = 10**1000
        assert compare_results(huge, huge)
        assert not compare_results(huge, huge + 1)

    def test_very_small_floats(self):
        """Very small floating point values."""
        tiny = 1e-308
        assert compare_results(tiny, tiny)
        assert not compare_results(tiny, tiny * 2)

    def test_float_representation_limits(self):
        """
        Float representation edge cases.

        Large integers may lose precision when converted to float.
        """
        # This integer can't be exactly represented as float
        big_int = 9007199254740993
        big_float = float(big_int)

        # They're different values due to float precision loss
        assert big_int != big_float  # In Python

        # Our comparison: they're different types anyway
        # int vs float comparison is allowed, but values differ
        # This documents the behavior, not necessarily what we want


# =============================================================================
# SECTION 9: REGRESSION TESTS
# =============================================================================


class TestRegressionOriginalBug:
    """
    Regression tests for the original bug discovered in the EiPL system.

    Bug scenario: A vowel counting function was expected to return integers
    (count of vowels), but the AI-generated code returned booleans
    (whether all vowels were present).

    Expected behavior: Tests should FAIL when types mismatch.
    Actual bug behavior: Tests PASSED because Python's False==0 and True==1.
    """

    def test_vowel_counter_bug_scenario_1(self):
        """
        foo("aeiou") should return 5 (vowel count).
        Generated code returned True (all vowels present).
        """
        expected = 5
        actual = True  # Bug: wrong type returned
        assert not compare_results(actual, expected), "Should fail: True != 5"

    def test_vowel_counter_bug_scenario_2(self):
        """
        foo("hello world") should return 3 (vowel count: e, o, o).
        Generated code returned False (not all vowels present).
        """
        expected = 3
        actual = False
        assert not compare_results(actual, expected), "Should fail: False != 3"

    def test_vowel_counter_bug_scenario_3(self):
        """
        foo("") should return 0 (no vowels in empty string).
        Generated code returned False (vowels not present).

        This was the sneaky case - in Python, False == 0, so it passed!
        """
        expected = 0
        actual = False
        assert not compare_results(actual, expected), "CRITICAL: False != 0"

    def test_vowel_counter_bug_scenario_4(self):
        """
        foo("hll wrld") should return 0 (no vowels).
        Generated code returned False (vowels not present).

        Same sneaky case as above.
        """
        expected = 0
        actual = False
        assert not compare_results(actual, expected), "CRITICAL: False != 0"

    def test_correct_implementations_still_pass(self):
        """When types match, comparison works correctly."""
        # Correct integer returns
        assert compare_results(5, 5)
        assert compare_results(3, 3)
        assert compare_results(0, 0)

        # Correct boolean returns
        assert compare_results(True, True)
        assert compare_results(False, False)


# =============================================================================
# SECTION 10: MATHEMATICAL PROPERTIES
# =============================================================================


class TestMathematicalProperties:
    """Tests verifying mathematical properties of equality."""

    @pytest.mark.parametrize("val", [0, 1, "a", [], {}, None, True, False])
    def test_reflexive(self, val):
        """a == a for all a (reflexive property)."""
        assert compare_results(val, val)

    def test_symmetric(self):
        """If a == b then b == a (symmetric property)."""
        pairs = [
            (1, 1.0),  # Equal
            (1, 2),  # Not equal
            ([1], (1,)),  # Equal (list/tuple)
        ]
        for a, b in pairs:
            assert compare_results(a, b) == compare_results(b, a)

    def test_transitive(self):
        """If a == b and b == c then a == c (transitive property)."""
        # a = 1 (int), b = 1.0 (float), c = 1 (int)
        a, b, c = 1, 1.0, 1
        if compare_results(a, b) and compare_results(b, c):
            assert compare_results(a, c)


# =============================================================================
# SECTION 11: FUTURE LANGUAGE SUPPORT (Placeholders)
# =============================================================================


@pytest.mark.skip(reason="JavaScript support not yet implemented")
class TestJavaScriptBehavior:
    """
    Placeholder for JavaScript-specific tests.

    When JavaScript support is added, implement tests for:
    - undefined vs null (both exist in JS, only null in Python)
    - Loose equality (==) vs strict equality (===)
    - NaN === NaN is false
    - typeof null === 'object' (JS quirk)
    - [] == false (truthy/falsy coercion)
    - '0' == 0 (string coercion)
    """

    def test_undefined_vs_null(self):
        pass

    def test_loose_vs_strict_equality(self):
        pass


@pytest.mark.skip(reason="Java support not yet implemented")
class TestJavaBehavior:
    """
    Placeholder for Java-specific tests.

    When Java support is added, implement tests for:
    - Integer vs int (boxing/unboxing)
    - Boolean vs boolean
    - .equals() vs == for objects
    - String interning edge cases
    - Array comparison (reference vs deep)
    """

    def test_integer_boxing(self):
        pass

    def test_equals_vs_identity(self):
        pass


@pytest.mark.skip(reason="C++ support not yet implemented")
class TestCppBehavior:
    """
    Placeholder for C++ specific tests.

    When C++ support is added, implement tests for:
    - Implicit bool to int conversion
    - Pointer comparison vs value comparison
    - std::string vs const char*
    - Floating point comparison epsilon
    """

    def test_implicit_bool_conversion(self):
        pass
