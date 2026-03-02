import pytest
from typing import cast

from resumable.runtime.interpreter import ProgramState, run
from resumable.runtime import CallableValue, Value


# ===== Helpers =====
def invoke(state: ProgramState, name: str, args: list[Value]) -> Value | None:
    value = state.global_env[name]
    if not callable(value):
        raise ValueError(f"{name} is not a function")
    callable_value = cast(CallableValue, value)
    return callable_value(args, state.context)


# ===== Function Execution =====
def test_simple_regular_function_call() -> None:
    state = run(
        """
        fun add_one(x) {
          return x + 1;
        }
        """
    )

    assert invoke(state, "add_one", [41]) == 42


def test_recursive_fibonacci_function() -> None:
    state = run(
        """
        fun fib(n) {
          if n <= 1 {
            return n;
          }
          return fib(n - 1) + fib(n - 2);
        }
        """
    )

    assert invoke(state, "fib", [10]) == 55


def test_block_scope_does_not_leak_shadowed_binding() -> None:
    state = run(
        """
        fun f() {
          var x = 1;
          {
            var x = 2;
          }
          return x;
        }
        """
    )

    assert invoke(state, "f", []) == 1


def test_top_level_statements_execute_in_global_env() -> None:
    state = run(
        """
        var x = 1;
        x = x + 2;
        """
    )

    assert state.global_env["x"] == 3


# ===== Function Calls And Arity =====
def test_wrong_arity_raises_value_error() -> None:
    state = run("fun f(x) { return x; }")

    with pytest.raises(ValueError, match=r"(?i)(?=.*arguments)(?=.*expected)(?=.*got)"):
        invoke(state, "f", [])


# ===== Interop With Generators =====
def test_regular_function_can_collect_from_generator_call() -> None:
    state = run(
        """
        gen range3() {
          yield 1;
          yield 2;
          yield 3;
        }

        fun total() {
          var values = collect(range3());
          return values;
        }
        """
    )

    assert invoke(state, "total", []) == [1, 2, 3]


def test_regular_function_can_step_generator_with_next() -> None:
    state = run(
        """
        gen counter() {
          yield 10;
          yield 20;
        }

        fun first() {
          var g = counter();
          return next(g);
        }
        """
    )

    assert invoke(state, "first", []) == 10


def test_next_bubbles_stop_iteration_after_generator_exhaustion() -> None:
    state = run(
        """
        gen one() {
          yield 1;
        }

        fun second() {
          var g = one();
          next(g);
          return next(g);
        }
        """
    )

    with pytest.raises(StopIteration):
        invoke(state, "second", [])


def test_next_bubbles_stop_iteration_return_value() -> None:
    state = run(
        """
        gen one_then_return() {
          yield 1;
          return 99;
        }

        fun second() {
          var g = one_then_return();
          next(g);
          return next(g);
        }
        """
    )

    with pytest.raises(StopIteration) as stop:
        invoke(state, "second", [])
    assert stop.value.value == 99
