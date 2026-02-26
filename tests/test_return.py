import pytest

from resumable.ast_expressions import Equals, Less, Literal, Sum, Var
from resumable.resumable import (
    Assign,
    Define,
    Env,
    Return,
    ResumableBlock,
    ResumableDone,
    ResumableFunction,
    ResumableIf,
    ResumableWhile,
    Yield,
    collect_values,
)
from resumable.runtime import RuntimeContext


def test_return_stops_generator_early() -> None:
    # fun stop_early() {
    #   yield 1
    #   return
    #   yield 2
    # }
    fn = ResumableFunction(
        params=[],
        body=ResumableBlock(
            [Yield(Literal(1)), Return(), Yield(Literal(2))],
            own_environment=False,
            name="function",
        ),
        name="stop_early_fn",
    )

    values = collect_values(fn.new({}), Env(name="global"), RuntimeContext())
    assert values == [1]


def test_return_inside_loop_exits_function() -> None:
    # fun stop_in_loop(limit) {
    #   var i = 0
    #   while (i < limit) {
    #     if (i == 2) return
    #     yield i
    #     i = i + 1
    #   }
    #   yield 99
    # }
    fn = ResumableFunction(
        params=[Var("limit")],
        body=ResumableBlock(
            [
                Define("i", Literal(0)),
                ResumableWhile(
                    Less(Var("i"), Var("limit")),
                    body=ResumableBlock(
                        [
                            ResumableIf(
                                Equals(Var("i"), Literal(2)),
                                then=Return(),
                            ),
                            Yield(Var("i")),
                            Assign(Var("i"), Sum(Var("i"), Literal(1))),
                        ],
                        name="while",
                    ),
                ),
                Yield(Literal(99)),
            ],
            own_environment=False,
            name="function",
        ),
        name="stop_in_loop_fn",
    )

    values = collect_values(fn.new({"limit": 5}), Env(name="global"), RuntimeContext())
    assert values == [0, 1]


def test_return_value_is_exposed_on_completion() -> None:
    # fun returns_value() {
    #   yield 1
    #   return 42
    # }
    fn = ResumableFunction(
        params=[],
        body=ResumableBlock(
            [Yield(Literal(1)), Return(Literal(42))],
            own_environment=False,
            name="function",
        ),
        name="returns_value_fn",
    )
    instance = fn.new({})
    global_env = Env(name="global")

    assert instance.resume(global_env, RuntimeContext()) == 1
    with pytest.raises(ResumableDone) as done:
        instance.resume(global_env, RuntimeContext())
    assert done.value.value == 42


def test_return_without_value_exposes_none() -> None:
    fn = ResumableFunction(
        params=[],
        body=ResumableBlock([Return()], own_environment=False, name="function"),
        name="returns_none_fn",
    )
    with pytest.raises(ResumableDone) as done:
        fn.new({}).resume(Env(name="global"), RuntimeContext())
    assert done.value.value is None


def test_collect_values_includes_return_value_after_yields() -> None:
    # fun yields_then_returns() {
    #   yield 1
    #   yield 2
    #   return 3
    # }
    fn = ResumableFunction(
        params=[],
        body=ResumableBlock(
            [Yield(Literal(1)), Yield(Literal(2)), Return(Literal(3))],
            own_environment=False,
            name="function",
        ),
        name="yields_then_returns_fn",
    )
    values = collect_values(fn.new({}), Env(name="global"), RuntimeContext())
    assert values == [1, 2, 3]
