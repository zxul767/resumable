from resumable.runtime import RuntimeContext
from resumable.ast_programs import build_fib_function, build_range_function
from resumable.resumable import Env, collect_values


def run_range(start: int, end: int) -> list[object]:
    range_fn = build_range_function()
    return collect_values(
        range_fn.new({"start": start, "end": end}),
        Env(name="global"),
        RuntimeContext(),
    )


def run_fib(n: int) -> list[object]:
    fib_fn = build_fib_function()
    return collect_values(
        fib_fn.new({"n": n}),
        Env(name="global"),
        RuntimeContext(),
    )


def test_range_empty_yields_empty_sentinel() -> None:
    assert run_range(0, 0) == ["empty"]


def test_range_returns_expected_interval() -> None:
    assert run_range(5, 10) == [5, 6, 7, 8, 9]


def test_fib_with_upper_bound_zero() -> None:
    assert run_fib(0) == [0]


def test_fib_with_upper_bound_ten() -> None:
    assert run_fib(10) == [0, 1, 1, 2, 3, 5, 8]
