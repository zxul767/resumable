#!/usr/bin/env python3

END = object()

import operator
import abc
from collections import UserDict

DEBUG = False
DEBUG = True

op_names = {
    operator.__add__: "+",
    operator.__eq__: "==",
    operator.__le__: "<=",
    operator.__mod__: "mod",
}


class IndentingWriter:
    def __init__(self, indent_size=3):
        self.indent_size = indent_size
        self.indents = 0

    def debug(self, message):
        if DEBUG:
            self._print_indentation()
            print(message, end="")

    def debugln(self, message):
        self.debug(message)
        print()

    def print(self, message):
        self._print_indentation()
        print(message, end="")

    def println(self, message):
        self.print(message)
        print()

    def indent(self):
        self.indents += 1

    def dedent(self):
        self.indents -= 1

    def _print_indentation(self):
        print(" " * self.indent_size * self.indents, end="")


writer = IndentingWriter()


def raise_(exception):
    raise exception


class Env(UserDict):
    @staticmethod
    def new(args=None, name=""):
        env = Env(name=name)
        if args:
            for key, value in args.items():
                env.define(key, value)
        return env

    def __init__(self, enclosing=None, name=""):
        super().__init__()
        self.enclosing = enclosing
        self.name = name

    def __getitem__(self, key):
        if key in self:
            return super().__getitem__(key)

        if self.enclosing:
            return self.enclosing[key]

        raise KeyError(key)

    # `env.define(...)` will *add* the key and value to *this* environment
    def define(self, key, value):
        writer.debugln(f"defining {key}={value} on env:{self.name}")
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

    def vars(self):
        result = {"self": list(self.items()), "parent": None, "object": self}
        if self.enclosing is not None:
            result["parent"] = {**self.enclosing.vars()}
        return result

    def vars_repr(self):
        chain = self.vars()
        result = ""
        while chain:
            result += f"{chain['self']}:{chain['object'].name}"
            chain = chain["parent"]
            if chain:
                result += " -> "
        return result


def try_run_resumable(
    resumable, env, parent, next_parent_index=None, on_stop_iteration=None
):
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
        if on_stop_iteration:
            on_stop_iteration()


class Resumable(abc.ABC):
    def __init__(self, children=None, name=None):
        self.name = name or ""
        self.children = children or list()
        self.index = 0

    @abc.abstractmethod
    def resume(self, env):
        pass

    def reset(self, first_time=False):
        # debugln(f"resetting {self.name}")
        self.index = 0
        for child in self.children:
            # some children are optional for some statements
            if child and not first_time:
                # becase each statement calls `reset(first_time=True)` in their
                # constructor, there is no need to reset again if it's the first
                # time
                child.reset()

    def exit(self, env):
        self.index = None
        raise StopIteration

    def __repr__(self):
        return self.name.upper()


class Yield(Resumable):
    def __init__(self, expr):
        super().__init__(name="yield")
        self.expr = expr

    def resume(self, env):
        value = self.expr.eval(env)
        _yield = YieldValue(value, sender=self)
        if isinstance(value, str):
            writer.debug(f"yield ('{value}')")
        else:
            writer.debug(f"yield ({value})")
        raise _yield


class YieldValue(Exception):
    def __init__(self, value, sender):
        self.value = value
        # we use `sender` to identify when to advance the instruction index in
        # parent statements, since "yield" statements don't throw `StopIteration`
        # (the other way in which parent statements know when to advance their
        # instruction pointer)
        self.sender = sender


# TODO:
# + implement `call` so it always returns an indepedent clone
class ResumableFunction(Resumable):
    def __init__(self, params, body, args=None, name=""):
        assert isinstance(
            body, ResumableBlock
        ), "function body can only be a `ResumableBlock`"

        super().__init__(name=name, children=body)

        self.body = body
        self.params = params
        # bind arguments to parameters in a fresh environment
        self.env = Env.new(args, name=self.name)
        self.yield_value = None

    def resume(self, env):
        if self.yield_value is END:
            writer.debug(f"resumable is exhausted!")
            raise StopIteration

        try:
            # make sure that outer environments are reachable
            self.env.enclosing = env
            writer.debugln(f"resuming function...")
            self.body.resume(self.env)

        except YieldValue as _yield:
            self.yield_value = _yield.value
            return self.yield_value

        except StopIteration as stop:
            self.yield_value = END
            raise stop

    def restart(self):
        raise ValueError("`ResumableFunction`s cannot be restarted!")


class ResumableBlock(Resumable):
    def __init__(self, stmts, name="block", own_environment=True):
        super().__init__(name=name, children=stmts)

        # ast
        self.stmts = stmts

        # state machine
        self.own_environment = own_environment
        self.reset(first_time=True)

    def resume(self, env):
        try:
            writer.indent()
            self._resume(env)
        finally:
            writer.dedent()

    def _resume(self, env):
        if self.env is not None:
            self.env.enclosing = env
            env = self.env

        if self.index < len(self.stmts):
            writer.debugln(f"executing ({self.name}:block) in env ({env.vars_repr()})")

        while self.index < len(self.stmts):
            stmt = self.stmts[self.index]
            writer.debugln(f"[{self.index}]({stmt.name}): ")
            try:
                writer.indent()
                try_run_resumable(
                    stmt, env, parent=self, next_parent_index=self.index + 1
                )
            finally:
                writer.dedent()

        writer.debugln(f"({self.name}:block) completed")
        raise StopIteration

    def reset(self, first_time=False):
        super().reset(first_time)

        if first_time:
            writer.debugln(f"setting up {self.name} block")
        else:
            writer.debugln(f"resetting {self.name} block")

        self.env = None
        if self.own_environment:
            self.env = Env.new(name=self.name)


class ResumableWhile(Resumable):
    def __init__(self, condition, body, name="while"):
        super().__init__(name=name, children=[body])

        # ast
        self.condition = condition
        self.body = body

        # state machine
        self.instructions = {
            0: self._execute_condition,
            1: self._execute_body,
            None: self.exit,
        }

    def resume(self, env):
        while True:
            self.instructions[self.index](env)

    def _execute_condition(self, env):
        writer.debugln(f"evaluating condition ({self.name})...")
        if self.condition.eval(env):
            try:
                writer.indent()
                self._execute_body(env)
            finally:
                writer.dedent()
        else:
            self.exit(env)

    def _execute_body(self, env):
        self.index = 1
        try_run_resumable(
            self.body,
            env,
            parent=self,
            next_parent_index=0,
            on_stop_iteration=self.body.reset,
        )


class ResumableIf(Resumable):
    def __init__(self, condition, then, else_=None, name="if"):
        assert then is not None, "then branch is not optional"

        super().__init__(name=name, children=[then, else_])

        # ast
        self.condition = condition
        self.then = then
        self.else_ = else_

        # state machine
        self.instructions = {
            0: self._execute_condition,
            1: self._execute_if_branch,
            2: self._execute_else_branch,
            None: self.exit,
        }
        self.reset(first_time=True)

    def resume(self, env):
        self.instructions[self.index](env)

    def _execute_condition(self, env):
        if self.condition_value is None:
            writer.debugln(f"evaluating condition ({self.name}): ")
            self.condition_value = self.condition.eval(env)

        if self.condition_value:
            self._execute_if_branch(env)

        elif self.else_:
            self._execute_else_branch(env)

        else:
            self.exit(env)

    def _execute_if_branch(self, env):
        self.index = 1
        writer.debugln("then branch")
        try_run_resumable(self.then, env, parent=self, next_parent_index=None)

    def _execute_else_branch(self, env):
        self.index = 2
        writer.debugln("else branch")
        try_run_resumable(self.else_, env, parent=self, next_parent_index=None)

    def reset(self, first_time=False):
        super().reset(first_time)
        self.condition_value = None


class Print(Resumable):
    def __init__(self, expr):
        super().__init__(name="print")
        self.expr = expr

    def resume(self, env):
        writer.println(f"printing {self.expr.eval(env)}")


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
        if isinstance(self.value, str):
            return f"'{self.value}'"
        return str(self.value)


class Binary:
    def __init__(self, left, right, op):
        self.left = left
        self.right = right
        self.op = op

    def eval(self, env):
        left_value = self.left.eval(env)
        right_value = self.right.eval(env)

        writer.debugln(
            f"[({self.left}={left_value}) {op_names[self.op]} ({self.right}={right_value})"
            + f" => {self.op(left_value, right_value)}]"
        )

        return self.op(left_value, right_value)

    def __repr__(self):
        return op_names[self.op]


class Equals(Binary):
    def __init__(self, left, right):
        super().__init__(left, right, operator.__eq__)


class Mod(Binary):
    def __init__(self, left, right):
        super().__init__(left, right, operator.__mod__)


class LessEquals(Binary):
    def __init__(self, left, right):
        super().__init__(left, right, operator.__le__)


class Sum(Binary):
    def __init__(self, left, right):
        super().__init__(left, right, operator.__add__)


class Assign(Resumable):
    def __init__(self, var, expr):
        super().__init__(name="assign")
        self.var = var
        self.expr = expr

    def resume(self, env):
        env[self.var.name] = self.expr.eval(env)
        writer.println(f"assigning {self.var.name} = {env[self.var.name]}")


class Define(Resumable):
    def __init__(self, var_name, initializer):
        super().__init__(name="define")
        self.var_name = var_name
        self.initializer = initializer

    def resume(self, env):
        env.define(self.var_name, self.initializer.eval(env))


def iterate(resumable, env):
    try:
        while True:
            value = resumable.resume(env)
            if isinstance(value, str):
                writer.println(f" --> ['{value}']")
            else:
                writer.println(f" --> [{value}]")
    except StopIteration:
        pass


writer.println("-" * 80)
writer.println("generator with conditionals and nested blocks")
writer.println("-" * 80)

env = Env.new({"fib": "<fn ...>"}, name="global")
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
    params=[Var("n")],
    body=ResumableBlock(
        [
            Define("i", Literal(0)),
            Print(Var("fib")),
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
                    name="then",
                ),
            ),
            Yield(Sum(Var("i"), Var("n"))),
        ],
        name="function",
        own_environment=False,
    ),
    args={"n": 0},
    name="fib",
)
iterate(fib, env)

writer.println("-" * 80)
writer.println("generator with while")
writer.println("-" * 80)

env = Env.new(name="global")
# for (item : upto(5)) {
#    println(item)
# }
#
# fun upto(n) {
#    var i = 0
#    while(i <= n) {
#       var j = i + 1
#       yield j
#       if (i % 2 == 0) {
#          var z = 0
#          println("i was even")
#          yield i + j
#       }
#       i = i + 1
#    }
# }
upto = ResumableFunction(
    params=[Var("n")],
    body=ResumableBlock(
        [
            Define("i", Literal(0)),
            ResumableWhile(
                LessEquals(Var("i"), Var("n")),
                body=ResumableBlock(
                    [
                        Define("j", Sum(Var("i"), Literal(1))),
                        Yield(Var("j")),
                        ResumableIf(
                            Equals(Mod(Var("i"), Literal(2)), Literal(0)),
                            ResumableBlock(
                                [
                                    Define("z", Literal(0)),
                                    Print(Literal("i was even")),
                                    Yield(Sum(Var("i"), Var("j"))),
                                ],
                                name="then",
                            ),
                        ),
                        Assign(Var("i"), Sum(Var("i"), Literal(1))),
                    ],
                    name="while",
                ),
            ),
        ],
        own_environment=False,
        name="function",
    ),
    args={"n": 5},
    name="upto",
)
iterate(upto, env)
