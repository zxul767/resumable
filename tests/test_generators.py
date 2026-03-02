import pytest

from resumable.frontend.ast_expressions import Var
from resumable.frontend.ast_statements import FunctionDeclaration
from resumable.frontend.parser import parse_and_validate
from resumable.runtime import RuntimeContext
from resumable.runtime.generator_compiler import (
    compile_generator_function,
    instantiate_generator,
)
from resumable.runtime.interpreter import run
from resumable.runtime.resumable import (
    Env,
    ResumableBlock,
    Generator,
    collect_values,
    try_run_resumable,
)
from resumable.snippets import range_generator_source


RANGE_SOURCE = range_generator_source(include_empty_sentinel=True)

FIB_SOURCE = """
gen fib(n) {
  var previous_a = 0;
  var a = 0;
  var b = 1;
  while a <= n {
    yield a;
    previous_a = a;
    a = b;
    b = previous_a + b;
  }
}
"""


# ===== Helpers =====
def build_range_function() -> Generator:
    program = parse_and_validate(RANGE_SOURCE)
    declaration = program.declarations[0]
    assert isinstance(declaration, FunctionDeclaration)
    return compile_generator_function(declaration)


def run_range(start: int, end: int) -> list[object]:
    state = run(RANGE_SOURCE)
    generator = instantiate_generator(state, "range", {"start": start, "end": end})
    return collect_values(generator, state.global_env, state.context)


def run_fib(n: int) -> list[object]:
    state = run(FIB_SOURCE)
    generator = instantiate_generator(state, "fib", {"n": n})
    return collect_values(generator, state.global_env, state.context)


# ===== Construction And Validation =====
def test_new_requires_mapping() -> None:
    range_fn = build_range_function()
    with pytest.raises(ValueError, match=r"(?i)(?=.*expected)(?=.*dictionary)"):
        range_fn.new(None)


def test_extra_arguments_are_rejected() -> None:
    range_fn = build_range_function()
    with pytest.raises(ValueError, match=r"(?i)(?=.*unexpected)(?=.*argument)"):
        range_fn.new({"start": 0, "end": 2, "unused": 123})


def test_duplicate_parameter_names_are_rejected() -> None:
    with pytest.raises(ValueError, match=r"(?i)(?=.*duplicate)(?=.*parameter)"):
        Generator(
            params=[Var("x"), Var("x")],
            body=ResumableBlock([]),
        )


def test_missing_required_arguments_raise_value_error() -> None:
    range_fn = build_range_function()
    with pytest.raises(ValueError, match=r"(?i)(?=.*required)(?=.*missing)"):
        range_fn.new({"start": 1})


# ===== Instantiation And Calls =====
def test_instantiate_parsed_generator_and_collect_values() -> None:
    source = range_generator_source(include_return_end=True)
    state = run(source)

    generator = instantiate_generator(state, "range", {"start": 2, "end": 5})
    values = collect_values(generator, state.global_env, state.context)

    assert values == [2, 3, 4, 5]


def test_generator_can_call_regular_function() -> None:
    source = """
    fun add_one(x) {
      return x + 1;
    }

    gen g(n) {
      yield add_one(n);
      return 0;
    }
    """
    state = run(source)

    generator = instantiate_generator(state, "g", {"n": 41})
    values = collect_values(generator, state.global_env, state.context)

    assert values == [42, 0]


def test_generator_can_call_generator_via_collect() -> None:
    source = """
    gen inner() {
      yield 5;
      yield 6;
    }

    gen outer() {
      yield collect(inner());
      return 0;
    }
    """
    state = run(source)

    generator = instantiate_generator(state, "outer", {})
    values = collect_values(generator, state.global_env, state.context)

    assert values == [[5, 6], 0]


def test_instantiate_generator_rejects_regular_function_name() -> None:
    state = run("fun f() { return 1; }")

    with pytest.raises(ValueError, match=r"(?i)generator"):
        instantiate_generator(state, "f", {})


def test_instantiate_generator_rejects_non_function_name() -> None:
    state = run("var x = 1;")

    with pytest.raises(ValueError, match=r"(?i)function"):
        instantiate_generator(state, "x", {})


# ===== Core Generator Behavior =====
def test_range_empty_yields_empty_sentinel() -> None:
    assert run_range(0, 0) == ["empty"]


def test_range_returns_expected_interval() -> None:
    assert run_range(5, 10) == [5, 6, 7, 8, 9]


def test_fib_with_upper_bound_zero() -> None:
    assert run_fib(0) == [0]


def test_fib_with_upper_bound_ten() -> None:
    assert run_fib(10) == [0, 1, 1, 2, 3, 5, 8]


def test_three_generators_keep_independent_state() -> None:
    source = range_generator_source()
    state = run(source)

    a = instantiate_generator(state, "range", {"start": 0, "end": 3})
    b = instantiate_generator(state, "range", {"start": 10, "end": 12})
    c = instantiate_generator(state, "range", {"start": 100, "end": 102})

    assert a.resume(state.global_env, state.context) == 0
    assert b.resume(state.global_env, state.context) == 10
    assert c.resume(state.global_env, state.context) == 100
    assert a.resume(state.global_env, state.context) == 1
    assert b.resume(state.global_env, state.context) == 11
    assert c.resume(state.global_env, state.context) == 101
    assert a.resume(state.global_env, state.context) == 2


# ===== Return Semantics =====
def test_return_stops_generator_early() -> None:
    source = """
    gen stop_early() {
      yield 1;
      return;
      yield 2;
    }
    """
    state = run(source)

    values = collect_values(
        instantiate_generator(state, "stop_early", {}),
        state.global_env,
        state.context,
    )
    assert values == [1]


def test_return_inside_loop_exits_function() -> None:
    source = """
    gen stop_in_loop(limit) {
      var i = 0;
      while i < limit {
        if i == 2 {
          return;
        }
        yield i;
        i = i + 1;
      }
      yield 99;
    }
    """
    state = run(source)

    values = collect_values(
        instantiate_generator(state, "stop_in_loop", {"limit": 5}),
        state.global_env,
        state.context,
    )
    assert values == [0, 1]


def test_return_value_is_exposed_on_completion() -> None:
    source = """
    gen returns_value() {
      yield 1;
      return 0;
    }
    """
    state = run(source)

    instance = instantiate_generator(state, "returns_value", {})
    assert instance.resume(state.global_env, state.context) == 1
    with pytest.raises(StopIteration) as stop:
        instance.resume(state.global_env, state.context)
    assert stop.value.value == 0


def test_return_without_value_exposes_none() -> None:
    state = run("gen returns_none() { return; }")

    with pytest.raises(StopIteration) as stop:
        instantiate_generator(state, "returns_none", {}).resume(
            state.global_env, state.context
        )
    assert stop.value.value is None


def test_collect_values_includes_return_value_after_yields() -> None:
    source = """
    gen yields_then_returns() {
      yield 1;
      yield 2;
      return 3;
    }
    """
    state = run(source)

    values = collect_values(
        instantiate_generator(state, "yields_then_returns", {}),
        state.global_env,
        state.context,
    )
    assert values == [1, 2, 3]


def test_resume_after_done_raises_stop_iteration() -> None:
    state = run("gen one() { yield 0; }")

    instance = instantiate_generator(state, "one", {})
    assert collect_values(instance, state.global_env, state.context) == [0]
    with pytest.raises(StopIteration):
        instance.resume(state.global_env, state.context)


# ===== Statement Semantics In Generators =====
def test_if_else_executes_both_branches() -> None:
    source = """
    gen choose(flag) {
      if flag {
        yield "then";
      } else {
        yield "else";
      }
    }
    """
    state = run(source)

    assert collect_values(
        instantiate_generator(state, "choose", {"flag": True}),
        state.global_env,
        state.context,
    ) == ["then"]
    assert collect_values(
        instantiate_generator(state, "choose", {"flag": False}),
        state.global_env,
        state.context,
    ) == ["else"]


def test_while_can_execute_zero_iterations() -> None:
    source = """
    gen only_done(n) {
      while n < 0 {
        yield n;
      }
      yield "done";
    }
    """
    state = run(source)

    values = collect_values(
        instantiate_generator(state, "only_done", {"n": 0}),
        state.global_env,
        state.context,
    )
    assert values == ["done"]


def test_inner_scope_shadowing_does_not_mutate_outer_binding() -> None:
    source = """
    gen scope_isolation() {
      var x = 1;
      {
        var x = 2;
        yield x;
        x = x + 1;
      }
      x = x + 2;
      yield x;
    }
    """
    state = run(source)

    values = collect_values(
        instantiate_generator(state, "scope_isolation", {}),
        state.global_env,
        state.context,
    )
    assert values == [2, 3]


def test_assignment_in_inner_scope_updates_parent_binding_when_not_shadowed() -> None:
    source = """
    gen parent_assignment() {
      var x = 1;
      {
        x = x + 1;
      }
      yield x;
    }
    """
    state = run(source)

    values = collect_values(
        instantiate_generator(state, "parent_assignment", {}),
        state.global_env,
        state.context,
    )
    assert values == [2]


# ===== Runtime Edges =====
def test_try_run_resumable_respects_next_parent_index_zero() -> None:
    parent = ResumableBlock([])
    child = ResumableBlock([])
    parent.index = 1

    try_run_resumable(
        child,
        Env(),
        RuntimeContext(),
        parent=parent,
        next_parent_index=0,
    )

    assert parent.index == 0


def test_range_semantics_across_small_grid() -> None:
    state = run(RANGE_SOURCE)

    for start in range(-2, 3):
        for end in range(-2, 3):
            values = collect_values(
                instantiate_generator(state, "range", {"start": start, "end": end}),
                state.global_env,
                state.context,
            )
            if start == end:
                assert values == ["empty"]
            elif start < end:
                assert values == list(range(start, end))
            else:
                assert values == []
