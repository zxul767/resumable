import pytest

from resumable.runtime import RuntimeContext
from resumable.ast_expressions import Less, Literal, Sum, Var
from resumable.ast_programs import build_range_function
from resumable.resumable import (
    Assign,
    Define,
    Env,
    InvalidOperation,
    ResumableBlock,
    ResumableFunction,
    ResumableIf,
    ResumableWhile,
    Yield,
    collect_values,
)


def test_new_requires_mapping() -> None:
    range_fn = build_range_function()
    with pytest.raises(ValueError):
        range_fn.new(None)


def test_extra_arguments_are_rejected() -> None:
    range_fn = build_range_function()
    with pytest.raises(ValueError):
        range_fn.new({"start": 0, "end": 2, "unused": 123})


def test_duplicate_parameter_names_are_rejected() -> None:
    fn = ResumableFunction(
        params=[Var("x"), Var("x")],
        body=ResumableBlock([Yield(Var("x"))], own_environment=False, name="function"),
        name="dup_param_fn",
    )
    with pytest.raises(ValueError):
        fn.new({"x": 1})


def test_resume_after_done_raises_invalid_operation() -> None:
    globals_env = Env(name="global")
    range_gen = build_range_function().new({"start": 0, "end": 1})
    assert collect_values(range_gen, globals_env, RuntimeContext()) == [0]

    with pytest.raises(InvalidOperation):
        range_gen.resume(globals_env, RuntimeContext())


def test_if_else_executes_both_branches() -> None:
    # fun choose(flag) {
    #   if (flag) yield "then"
    #   else yield "else"
    # }
    chooser = ResumableFunction(
        params=[Var("flag")],
        body=ResumableBlock(
            [
                ResumableIf(
                    Var("flag"),
                    then=Yield(Literal("then")),
                    else_=Yield(Literal("else")),
                )
            ],
            own_environment=False,
            name="function",
        ),
        name="choose_fn",
    )
    globals_env = Env(name="global")

    assert collect_values(chooser.new({"flag": True}), globals_env, RuntimeContext()) == ["then"]
    assert collect_values(chooser.new({"flag": False}), globals_env, RuntimeContext()) == ["else"]


def test_while_can_execute_zero_iterations() -> None:
    # fun only_done(n) {
    #   while (n < 0) { yield n }
    #   yield "done"
    # }
    fn = ResumableFunction(
        params=[Var("n")],
        body=ResumableBlock(
            [
                ResumableWhile(
                    Less(Var("n"), Literal(0)),
                    body=ResumableBlock([Yield(Var("n"))], name="while"),
                ),
                Yield(Literal("done")),
            ],
            own_environment=False,
            name="function",
        ),
        name="only_done_fn",
    )
    values = collect_values(fn.new({"n": 0}), Env(name="global"), RuntimeContext())
    assert values == ["done"]


def test_inner_scope_shadowing_does_not_mutate_outer_binding() -> None:
    # fun scope_isolation() {
    #   var x = 1
    #   {
    #     var x = 2
    #     yield x
    #     x = x + 1
    #   }
    #   x = x + 2
    #   yield x
    # }
    fn = ResumableFunction(
        params=[],
        body=ResumableBlock(
            [
                Define("x", Literal(1)),
                ResumableBlock(
                    [
                        Define("x", Literal(2)),
                        Yield(Var("x")),
                        Assign(Var("x"), Sum(Var("x"), Literal(1))),
                    ],
                    own_environment=True,
                    name="inner",
                ),
                Assign(Var("x"), Sum(Var("x"), Literal(2))),
                Yield(Var("x")),
            ],
            own_environment=False,
            name="function",
        ),
        name="scope_isolation_fn",
    )
    values = collect_values(fn.new({}), Env(name="global"), RuntimeContext())
    assert values == [2, 3]


def test_assignment_in_inner_scope_updates_parent_binding_when_not_shadowed() -> None:
    # fun parent_assignment() {
    #   var x = 1
    #   {
    #     x = x + 1
    #   }
    #   yield x
    # }
    fn = ResumableFunction(
        params=[],
        body=ResumableBlock(
            [
                Define("x", Literal(1)),
                ResumableBlock(
                    [Assign(Var("x"), Sum(Var("x"), Literal(1)))],
                    own_environment=True,
                    name="inner",
                ),
                Yield(Var("x")),
            ],
            own_environment=False,
            name="function",
        ),
        name="parent_assignment_fn",
    )
    values = collect_values(fn.new({}), Env(name="global"), RuntimeContext())
    assert values == [2]


def test_three_generators_keep_independent_state() -> None:
    range_fn = build_range_function()
    globals_env = Env(name="global")

    a = range_fn.new({"start": 0, "end": 3}, name="a")
    b = range_fn.new({"start": 10, "end": 12}, name="b")
    c = range_fn.new({"start": 100, "end": 102}, name="c")

    assert a.resume(globals_env, RuntimeContext()) == 0
    assert b.resume(globals_env, RuntimeContext()) == 10
    assert c.resume(globals_env, RuntimeContext()) == 100
    assert a.resume(globals_env, RuntimeContext()) == 1
    assert b.resume(globals_env, RuntimeContext()) == 11
    assert c.resume(globals_env, RuntimeContext()) == 101
    assert a.resume(globals_env, RuntimeContext()) == 2
