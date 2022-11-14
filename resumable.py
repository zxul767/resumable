#!/usr/bin/env python3

END = object()

import operator
from collections import UserDict

DEBUG = False
# DEBUG = True

op_names = {
    operator.__add__: "+",
    operator.__eq__: "==",
    operator.__le__: "<=",
}


def debug(message):
    if DEBUG:
        print(message, end="")


def debugln(message):
    if DEBUG:
        print(message)


def raise_(exception):
    raise exception


class Env(UserDict):
    @staticmethod
    def new(args=None):
        env = Env()
        if args:
            for key, value in args.items():
                env.define(key, value)
        return env

    def __init__(self):
        super().__init__()
        self.enclosing = None

    def __getitem__(self, key):
        if key in self:
            return super().__getitem__(key)

        if self.enclosing:
            return self.enclosing[key]

        raise KeyError(key)

    # `env.define(...)` will *add* the key and value to *this* environment
    def define(self, key, value):
        # we could raise an exception if the variable has
        super().__setitem__(key, value)

    # `env[key]=value` will just update an existing key wherever in the
    # environments' chain it is found (or raise an error if not found)
    def __setitem__(self, key, value):
        if key in self:
            super().__setitem__(key, value)

        elif self.enclosing:
            self.enclosing[key] = value

        else:
            raise KeyError(key)


class Yield:
    def __init__(self, expr):
        self.expr = expr

    def resume(self, env):
        raise YieldValue(self.expr.eval(env), sender=self)


class YieldValue(Exception):
    def __init__(self, value, sender):
        self.value = value
        # we use `sender` to identify when to advance the instruction index in
        # parent statements, since "yield" statements don't throw `StopIteration`
        # (the other way in which parent statements know when to advance their
        # instruction pointer)
        self.sender = sender


def try_run_resumable(resumable, env, parent, next_parent_index=None, on_stop=None):
    try:
        resumable.resume(env)
        # we should reach this when there are no more "yields" left to hit
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
        if on_stop:
            on_stop()


class ResumableFunction:
    def __init__(self, body, args=None):
        self.body = body
        # bind arguments to parameters in a fresh environment
        self.env = Env.new(args)
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


class ResumableBlock:
    def __init__(self, stmts, name=""):
        self.name = name

        # ast
        self.stmts = stmts

        # state machine
        self.index = 0

    def resume(self, env):
        debugln(f"executing block: {self.name}")
        while self.index < len(self.stmts):
            debugln(f"executing statement {self.index}: ")
            stmt = self.stmts[self.index]
            try_run_resumable(stmt, env, parent=self, next_parent_index=self.index + 1)

        raise StopIteration

    def reset(self):
        debugln(f"restarting block execution: {self.name}")
        self.index = 0


class ResumableWhile:
    def __init__(self, condition, body):
        # ast
        self.condition = condition
        self.body = body

        # state machine
        self.index = 0
        self.instructions = {
            0: self._execute_condition,
            1: self._execute_body,
            None: (lambda env: raise_(StopIteration())),
        }

    def resume(self, env):
        while True:
            self.instructions[self.index](env)

    def _execute_condition(self, env):
        debugln("evaluating while condition...")
        if self.condition.eval(env):
            self._execute_body(env)
        else:
            self._exit_loop()

    def _execute_body(self, env):
        self.index = 1
        try_run_resumable(
            self.body, env, parent=self, next_parent_index=0, on_stop=self.body.reset
        )

    def _exit_loop(self):
        debugln("exiting while...")
        self.index = None
        raise StopIteration


class ResumableIf:
    def __init__(self, condition, then, else_=None):
        assert then is not None, "then branch is not optional"

        # ast
        self.condition = condition
        self.then = then
        self.else_ = else_

        # state machine
        self.index = 0
        self.condition_value = None
        self.instructions = {
            0: self._execute_condition,
            1: self._execute_if_branch,
            2: self._execute_else_branch,
            None: (lambda env: raise_(StopIteration())),
        }

    def resume(self, env):
        self.instructions[self.index](env)
        # this flow of control may happen if there is no "else" branch,
        # and the condition turned out to be false
        self.index = None
        raise StopIteration

    def _execute_condition(self, env):
        if self.condition_value is None:
            debugln("evaluating if condition...")
            self.condition_value = self.condition.eval(env)

        if self.condition_value:
            self._execute_if_branch(env)
        elif self.else_:
            self._execute_else_branch(env)

    def _execute_if_branch(self, env):
        self.index = 1
        debugln("then branch")
        try_run_resumable(self.then, env, parent=self, next_parent_index=None)

    def _execute_else_branch(self, env):
        self.index = 2
        debugln("else branch")
        try_run_resumable(self.else_, env, parent=self, next_parent_index=None)


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


class LessEquals(Binary):
    def __init__(self, left, right):
        super().__init__(left, right, operator.__le__)


class Sum(Binary):
    def __init__(self, left, right):
        super().__init__(left, right, operator.__add__)


class Assign:
    def __init__(self, var, expr):
        self.var = var
        self.expr = expr

    def resume(self, env):
        env[self.var.name] = self.expr.eval(env)
        print(f"assigning {self.var.name} = {env[self.var.name]}")


class Define:
    def __init__(self, var_name, initializer):
        self.var_name = var_name
        self.initializer = initializer

    def resume(self, env):
        env.define(self.var_name, self.initializer.eval(env))
        print(f"defining {self.var_name} = {env[self.var_name]}")


def iterate(resumable, env):
    try:
        while True:
            print(f"yield --> [{resumable.resume(env)}]")
            print()
    except StopIteration:
        pass


print("-" * 80)
print("generator with conditionals and nested blocks")
print("-" * 80)

env = Env.new({"globals": "fibonacci"})
#
# for (item : fib(0)) {
#    println(item)
# }
#
# fun fib(n) {
#    var i = 0
#    println(globals)
#    if (n == 0) {
#       yield "> n == 0"
#       println(n)
#       yield "> printed n"
#       if (i == 1) {
#          yield ">> i == 1"
#          println(">> two levels deep")
#          yield ">> after printing"
#       } else
#          yield ">> i != 1"
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
                        Yield(Literal("> n == 0")),
                        Print(Var("n")),
                        Yield(Literal("> printed n")),
                        ResumableIf(
                            Equals(Var("i"), Literal(1)),
                            ResumableBlock(
                                [
                                    Yield(Literal(">> i == 1")),
                                    Print(Literal(">> two levels deep")),
                                    Yield(Literal(">> after printing")),
                                ]
                            ),
                            else_=Yield(Literal(">> i != 1")),
                        ),
                    ],
                    name="then-branch",
                ),
            ),
            Yield(Sum(Var("i"), Var("n"))),
        ],
        name="func body",
    ),
    args={"n": 0},
)
iterate(fib, env)

print("-" * 80)
print("generator with while")
print("-" * 80)

env = Env.new()
# for (item : upto(5)) {
#    println(item)
# }
#
# fun upto(n) {
#    var i = 0
#    while(i <= n) {
#       yield i
#       i = i + 1
#    }
# }
upto = ResumableFunction(
    ResumableBlock(
        [
            Define("i", Literal(0)),
            ResumableWhile(
                LessEquals(Var("i"), Var("n")),
                body=ResumableBlock(
                    [Yield(Var("i")), Assign(Var("i"), Sum(Var("i"), Literal(1)))],
                    name="while-body",
                ),
            ),
        ],
        name="func-body",
    ),
    args={"n": 5},
)
iterate(upto, env)
