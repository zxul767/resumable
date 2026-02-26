from .ast_expressions import Equals, Less, LessEquals, Literal, Sum, Var
from .resumable import (
    Assign,
    Define,
    ResumableBlock,
    ResumableFunction,
    ResumableIf,
    ResumableWhile,
    Yield,
)


def build_range_function() -> ResumableFunction:
    # Pseudo-code:
    # fun range(start, end) {
    #   if (start == end) yield "empty"
    #   var i = start
    #   while (i < end) {
    #     yield i
    #     i = i + 1
    #   }
    # }
    return ResumableFunction(
        params=[Var("start"), Var("end")],
        body=ResumableBlock(
            [
                ResumableIf(Equals(Var("start"), Var("end")), Yield(Literal("empty"))),
                Define("i", Var("start")),
                ResumableWhile(
                    Less(Var("i"), Var("end")),
                    body=ResumableBlock(
                        [
                            Yield(Var("i")),
                            Assign(Var("i"), Sum(Var("i"), Literal(1))),
                        ],
                        name="while",
                    ),
                ),
            ],
            own_environment=False,
            name="function",
        ),
        name="range_fn",
    )


def build_fib_function() -> ResumableFunction:
    # Pseudo-code:
    # fun fib(n) {
    #   var previous_a = 0
    #   var a = 0
    #   var b = 1
    #   while (a <= n) {
    #     yield a
    #     previous_a = a
    #     a = b
    #     b = previous_a + b
    #   }
    # }
    return ResumableFunction(
        params=[Var("n")],
        body=ResumableBlock(
            [
                Define("previous_a", Literal(0)),
                Define("a", Literal(0)),
                Define("b", Literal(1)),
                ResumableWhile(
                    LessEquals(Var("a"), Var("n")),
                    body=ResumableBlock(
                        [
                            Yield(Var("a")),
                            Assign(Var("previous_a"), Var("a")),
                            Assign(Var("a"), Var("b")),
                            Assign(Var("b"), Sum(Var("previous_a"), Var("b"))),
                        ],
                        name="while",
                    ),
                ),
            ],
            own_environment=False,
            name="function",
        ),
        name="fib_fn",
    )
