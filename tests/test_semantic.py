import pytest

from resumable.frontend.parser import parse_and_validate
from resumable.frontend.semantic import SemanticError


# ===== Top-Level Restrictions =====
def test_top_level_return_is_rejected() -> None:
    with pytest.raises(SemanticError, match=r"(?i)(?=.*return)(?=.*function)"):
        parse_and_validate("return 1;")


def test_top_level_yield_is_rejected() -> None:
    with pytest.raises(SemanticError, match=r"(?i)(?=.*yield)(?=.*generator)"):
        parse_and_validate("yield 1;")


# ===== Yield Placement Rules =====
def test_yield_inside_regular_function_is_rejected() -> None:
    source = "fun f() { yield 1; }"
    with pytest.raises(SemanticError, match=r"(?i)(?=.*yield)(?=.*generator)"):
        parse_and_validate(source)


def test_yield_inside_generator_is_allowed() -> None:
    source = "gen g() { yield 1; return 2; }"
    parse_and_validate(source)


# ===== Function Declaration Rules =====
def test_duplicate_parameter_names_are_rejected_semantically() -> None:
    source = "fun dup(x, x) { return x; }"
    with pytest.raises(SemanticError, match=r"(?i)(?=.*duplicate)(?=.*parameter)"):
        parse_and_validate(source)


# ===== Nested Declaration Rules =====
def test_return_is_allowed_in_nested_function_context() -> None:
    source = "fun outer() { fun inner(x) { return x; } return 1; }"
    parse_and_validate(source)


def test_yield_is_allowed_in_nested_generator_context() -> None:
    source = "fun outer() { gen inner() { yield 1; return 2; } return 0; }"
    parse_and_validate(source)
