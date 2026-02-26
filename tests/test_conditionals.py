from resumable.ast_expressions import Literal, Var
from resumable.resumable import (
    Env,
    ResumableBlock,
    ResumableFunction,
    ResumableIf,
    Yield,
    collect_values,
)
from resumable.runtime import RuntimeContext


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
    env = Env(name="global")
    context = RuntimeContext()
    assert collect_values(chooser.new({"flag": True}), env, context) == ["then"]
    assert collect_values(chooser.new({"flag": False}), env, context) == ["else"]
