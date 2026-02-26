from resumable.ast_expressions import Literal, Sum, Var
from resumable.resumable import Assign, Define, Env, ResumableBlock, ResumableFunction, Yield, collect_values
from resumable.runtime import RuntimeContext


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
