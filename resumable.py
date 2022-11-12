#!/usr/bin/env python3

END = object()

from collections import UserDict

# from goto import with_goto
import operator

DEBUG = False
# DEBUG = True


def debug(message):
    if DEBUG:
        print(message, end="")


def debugln(message):
    if DEBUG:
        print(message)


class Env(UserDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enclosing = None

    def __getitem__(self, key):
        if key in self:
            return super().__getitem__(key)

        if self.enclosing is None:
            raise KeyError(key)

        return self.enclosing[key]


class YieldValue(Exception):
    def __init__(self, value, sender):
        self.value = value
        self.sender = sender


class Yield:
    def __init__(self, expr):
        self.expr = expr

    def resume(self, env):
        raise YieldValue(self.expr.eval(env), sender=self)


class ResumableFunction:
    def __init__(self, body, args=None):
        self.body = body
        # bind arguments to parameters in a fresh environment
        self.env = Env(args) if args else Env()
        self.yield_value = None

    def resume(self, env):
        if self.yield_value is END:
            debug(f"resumable is exhausted!")
            raise StopIteration

        try:
            # make sure that outer environments are reachable
            self.env.enclosing = env
            debugln(f"resuming function...")
            self.body.resume(self.env)

        except YieldValue as _yield:
            self.yield_value = _yield.value
            return self.yield_value

        except StopIteration as stop:
            self.yield_value = END
            raise stop


def try_run_resumable(resumable, env, parent, next_parent_index=None):
    try:
        resumable.resume(env)
        # we should reach this when there are no more yields left to hit
        # in the current context of the descendants of `resumable`
        parent.index = next_parent_index

    except YieldValue as _yield:
        # if the yield originated in an immediate child atomic statement,
        # move on to next statement immediately but there is
        if _yield.sender is resumable:
            parent.index = next_parent_index
        # propagate the yield so ancestor resumables can potentially advance
        # their instruction indexes
        raise _yield

    # composite child statements always raise StopIteration when they're done
    except StopIteration:
        parent.index = next_parent_index


class ResumableBlock:
    def __init__(self, stmts, name=""):
        self.stmts = stmts
        self.name = name
        self.index = 0

    def resume(self, env):
        debugln(f"executing block: {self.name}")
        while self.index < len(self.stmts):
            debugln(f"executing statement {self.index}: ")
            stmt = self.stmts[self.index]
            try_run_resumable(stmt, env, parent=self, next_parent_index=self.index + 1)

        raise StopIteration


def raise_(exception):
    raise exception


class ResumableIf:
    def __init__(self, condition, _then, _else=None):
        assert _then is not None, "_then branch is not optional"

        self.condition = condition
        self.condition_value = None
        self.instructions = {
            0: self.if_branch,
            1: self.else_branch,
            None: (lambda env: raise_(StopIteration())),
        }
        self.index = 0
        self._then = _then
        self._else = _else

    def resume(self, env):
        if self.condition_value is None:
            debugln("evaluating if condition...")
            self.condition_value = self.condition.eval(env)

        self.instructions[self.index](env)
        raise StopIteration

    def if_branch(self, env):
        if not self.condition_value:
            self.else_branch(env)
        else:
            debugln("then branch")
            try_run_resumable(self._then, env, parent=self, next_parent_index=None)

    def else_branch(self, env):
        self.index = 1
        debugln("else branch")
        if self._else:
            try_run_resumable(self._else, env, parent=self, next_parent_index=None)


class Print:
    def __init__(self, expr):
        self.expr = expr

    def resume(self, env):
        print(f"printing {self.expr.eval(env)}")


class Var:
    def __init__(self, name):
        self.name = name

    def eval(self, env):
        return env[self.name]

    def __str__(self):
        return self.name


class Literal:
    def __init__(self, value):
        self.value = value

    def eval(self, env):
        return self.value

    def __str__(self):
        return str(self.value)


op_names = {
    operator.__add__: "+",
    operator.__eq__: "==",
}


class Binary:
    def __init__(self, left, right, op):
        self.left = left
        self.right = right
        self.op = op

    def eval(self, env):
        left_value = self.left.eval(env)
        right_value = self.right.eval(env)

        debug(
            f"({self.left}={left_value}) {op_names[self.op]} ({self.right}={right_value})"
        )
        debugln(f" => {self.op(left_value, right_value)}")

        return self.op(left_value, right_value)


class Equals(Binary):
    def __init__(self, left, right):
        super().__init__(left, right, operator.__eq__)


class Sum(Binary):
    def __init__(self, left, right):
        super().__init__(left, right, operator.__add__)


class Define:
    def __init__(self, name, initializer):
        self.name = name
        self.initializer = initializer

    def resume(self, env):
        env[self.name] = self.initializer.eval(env)
        print(f"defining {self.name} = {env[self.name]}")


env = Env({"globals": "globals"})
#
# for (item : fib(0)) {
#    println(item)
# }
#
# fun fib(n) {
#    var i = 0
#    println(globals)
#    if (n == 0) {
#       yield "> zero"
#       println(n)
#       yield "> one"
#       if (i == 1) {
#          yield ">> one"
#          println(">> deep in the trenches")
#          yield ">> two
#       } else {
#          yield "> two"
#       }
#    }
#    yield i + n
# }
#
fib = ResumableFunction(
    ResumableBlock(
        [
            Define("i", Literal(0)),
            Print(Var("globals")),
            ResumableIf(
                Equals(Var("n"), Literal(0)),
                ResumableBlock(
                    [
                        Yield(Literal("> zero")),
                        Print(Var("n")),
                        Yield(Literal("> one")),
                        ResumableIf(
                            Equals(Var("i"), Literal(1)),
                            ResumableBlock(
                                [
                                    Yield(Literal(">> one")),
                                    Print(Literal(">> deep in the trenches")),
                                    Yield(Literal(">> two")),
                                ]
                            ),
                            Yield(Literal("> two")),
                        ),
                    ],
                    name="then-branch",
                ),
            ),
            Yield(Sum(Var("i"), Var("n"))),
        ],
        name="func body",
    ),
    {"n": 0},
)
try:
    while True:
        print(f"yield --> [{fib.resume(env)}]")
        print()
except StopIteration:
    pass
