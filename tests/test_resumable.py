from __future__ import annotations

import pytest

from ast_programs import build_fib_function, build_range_function
from resumable import Env, ResumableDone, collect_values



def test_range_empty_yields_empty_sentinel() -> None:
    range_fn = build_range_function()
    values = collect_values(range_fn.new({"start": 0, "end": 0}), Env(name="global"))
    assert values == ["empty"]


def test_range_returns_expected_interval() -> None:
    range_fn = build_range_function()
    values = collect_values(range_fn.new({"start": 5, "end": 10}), Env(name="global"))
    assert values == [5, 6, 7, 8, 9]


def test_interleaved_generators_keep_independent_state() -> None:
    range_fn = build_range_function()
    globals_env = Env(name="global")

    left = range_fn.new({"start": 5, "end": 10}, name="left")
    right = range_fn.new({"start": 0, "end": 3}, name="right")

    assert left.resume(globals_env) == 5
    assert right.resume(globals_env) == 0
    assert left.resume(globals_env) == 6
    assert right.resume(globals_env) == 1
    assert left.resume(globals_env) == 7
    assert right.resume(globals_env) == 2

    with pytest.raises(ResumableDone):
        right.resume(globals_env)


def test_missing_required_arguments_raise_value_error() -> None:
    range_fn = build_range_function()
    with pytest.raises(ValueError):
        range_fn.new({"start": 1})


def test_fib_with_upper_bound_zero() -> None:
    fib_fn = build_fib_function()
    values = collect_values(fib_fn.new({"n": 0}), Env(name="global"))
    assert values == [0]


def test_fib_with_upper_bound_ten() -> None:
    fib_fn = build_fib_function()
    values = collect_values(fib_fn.new({"n": 10}), Env(name="global"))
    assert values == [0, 1, 1, 2, 3, 5, 8]
