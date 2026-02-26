from resumable.ast_expressions import Less, Literal, Var
from resumable.resumable import Env, ResumableBlock, ResumableFunction, ResumableWhile, Yield, collect_values
from resumable.runtime import RuntimeContext


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
