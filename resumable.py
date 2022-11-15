#!/usr/bin/env python3

END = object()

import operator
import abc
from collections import UserDict
from contextlib import contextmanager

DEBUG = False
# DEBUG = True

op_names = {
    operator.__add__: "+",
    operator.__eq__: "==",
    operator.__le__: "<=",
    operator.__mod__: "mod",
}


class IndentingWriter:
    def __init__(self, indent_size=3):
        self._indent_size = indent_size
        self._indents = 0

    def debug(self, message):
        if DEBUG:
            self._print_indentation()
            print(message, end="")

    def debugln(self, message):
        if DEBUG:
            self.debug(message)
            print()

    def print(self, message):
        self._print_indentation()
        print(message, end="")

    def println(self, message):
        self.print(message)
        print()

    def indent(self):
        if DEBUG:
            self._indents += 1

    def dedent(self):
        if DEBUG:
            self._indents -= 1

    def _print_indentation(self):
        if DEBUG:
            print(" " * self._indent_size * self._indents, end="")


writer = IndentingWriter()


def repr_string(value):
    if isinstance(value, str):
        return f"'{value}'"
    return str(value)


@contextmanager
def indented_output(writer):
    writer.indent()
    try:
        yield
    finally:
        writer.dedent()


class Env:
    @staticmethod
    def new(args=None, name=""):
        env = Env(name=name)
        if args:
            for key, value in args.items():
                env.define(key, value)
        return env

    def __init__(self, enclosing=None, name=""):
        self.enclosing = enclosing
        self.name = name
        self.key_values = dict()

    def __getitem__(self, key):
        if key in self.key_values:
            return self.key_values[key]

        if self.enclosing:
            return self.enclosing[key]

        raise KeyError(key)

    # `env.define(...)` will *add* the key and value to *this* environment
    def define(self, key, value):
        writer.debugln(f"defining {key}={value} on env:{self.name}")
        self.key_values[key] = value

    # `env[key]=value` will just update an existing key wherever in the
    # environments' chain it is found (or raise an error if not found)
    def __setitem__(self, key, value):
        if key in self.key_values:
            self.key_values[key] = value

        elif self.enclosing:
            self.enclosing[key] = value

        else:
            raise KeyError(key)

    def all_vars(self):
        result = {"self": list(self.key_values.items()), "parent": None, "object": self}
        if self.enclosing is not None:
            result["parent"] = {**self.enclosing.all_vars()}
        return result

    def __repr__(self):
        chain = self.all_vars()
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
        # move on to next statement
        if _yield.sender is resumable:
            parent.index = next_parent_index
        raise _yield

    # composite child statements always raise `StopIteration` when they're done
    except StopIteration:
        parent.index = next_parent_index
        if on_stop_iteration:
            on_stop_iteration()


class Expr(abc.ABC):
    # all expressions should support evaluation
    @abc.abstractmethod
    def eval(self, env):
        pass


class Resumable(abc.ABC):
    def __init__(self, children=None, name=None):
        self.name = name or ""
        self.children = children
        # all "resumables" start at `index=0`
        self.index = 0

    # all "resumables" should support resuming in a given environment
    @abc.abstractmethod
    def resume(self, env):
        pass

    def exit(self, env):
        # all "resumables" end at `index=None`, which is a terminal state
        # that always raises `StopIteration` (at least until being resetted)
        self.index = None
        raise StopIteration

    def reset(self, first_time=False):
        writer.debugln(
            "{0} {1} block".format(
                "setting up" if first_time else "resetting", self.name
            )
        )
        self.index = 0
        if not first_time:
            self._reset_children()

    def _reset_children(self):
        for child in self.children or []:
            # some children are optional for some statements
            if child:
                child.reset()

    def __repr__(self):
        return self.name.upper()

    @abc.abstractmethod
    def clone(self):
        pass


class Yield(Resumable):
    def __init__(self, expr):
        super().__init__(name="yield")
        self.expr = expr

    def resume(self, env):
        value = self.expr.eval(env)
        writer.debug(repr_string(value))

        _yield = YieldValue(value, sender=self)
        raise _yield

    def clone(self):
        return Yield(self.expr)


class YieldValue(Exception):
    def __init__(self, value, sender):
        self.value = value
        # we use `sender` to identify when to advance the instruction index in
        # parent statements, since "yield" statements don't throw `StopIteration`
        # (the other way in which parent statements know when to advance their
        # instruction pointer)
        self.sender = sender


class ResumableFunction(Resumable):
    def __init__(self, params, body, name=""):
        assert isinstance(
            body, ResumableBlock
        ), "function body can only be a `ResumableBlock`"

        super().__init__(name=name, children=body)

        self.params = params
        self.body = body
        self.env = None

    def clone(self):
        return ResumableFunction(
            params=self.params, body=self.body.clone(), name=self.name
        )

    def new(self, args=None):
        self._validate_call_args(args)
        _clone = self.clone()
        # bind arguments to parameters in a fresh environment
        _clone.env = Env.new(args, name=self.name)
        return _clone

    def resume(self, env):
        if self.env is None:
            raise ValueError("`call` needs to be invoked to generate a new instance!")

        if self.index is None:
            self.exit(env)

        try:
            # make sure that outer environments are reachable
            self.env.enclosing = env
            writer.debugln(f"resuming function...")
            self.body.resume(self.env)

        except YieldValue as _yield:
            return _yield.value

        except StopIteration as stop:
            self.exit(env)

    def restart(self):
        raise ValueError("`ResumableFunction`s cannot be restarted!")

    def _validate_call_args(self, args):
        if not isinstance(args, dict):
            raise ValueError("Expected arguments as a dictionary")

        missing = set([param.name for param in self.params]) - set(args.keys())
        if missing:
            raise ValueError(f"Required arguments are missing: {list(missing)}")


class ResumableBlock(Resumable):
    def __init__(self, stmts, name="block", own_environment=True):
        super().__init__(name=name, children=stmts)

        # ast
        self.stmts = stmts

        # state machine
        self.own_environment = own_environment
        self.reset(first_time=True)

    def clone(self):
        return ResumableBlock(
            stmts=[stmt.clone() for stmt in self.stmts],
            name=self.name,
            own_environment=self.own_environment,
        )

    def resume(self, env):
        if self.index is None:
            self.exit(env)

        with indented_output(writer):
            self._resume(env)

    def _resume(self, env):
        self._execute_statements(env)
        writer.debugln(f"({self.name}:block) completed")

        self.exit(env)

    def _execute_statements(self, env):
        if self.env is not None:
            # ensure outer environments are reachable
            self.env.enclosing = env
            env = self.env

        if self.index < len(self.stmts):
            writer.debugln(f"executing ({self.name}:block) in env ({repr(env)})")

        while self.index < len(self.stmts):
            stmt = self.stmts[self.index]

            writer.debugln(f"[{self.index}]({stmt.name}): ")
            with indented_output(writer):
                try_run_resumable(
                    stmt, env, parent=self, next_parent_index=self.index + 1
                )

    def reset(self, first_time=False):
        super().reset(first_time)

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

    def clone(self):
        return ResumableWhile(
            condition=self.condition, body=self.body.clone(), name=self.name
        )

    def resume(self, env):
        while True:
            self.instructions[self.index](env)

    def _execute_condition(self, env):
        writer.debugln(f"evaluating condition ({self.name})...")
        if self.condition.eval(env):
            with indented_output(writer):
                self._execute_body(env)
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

    def clone(self):
        else_ = else_.clone() if else_ else None
        return ResumableIf(
            condition=condition, then=then.clone(), else_=else_, name=self.name
        )

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

    def clone(self):
        # we can return the same object since it has no mutable state
        return self

    def resume(self, env):
        writer.println(f"printing {self.expr.eval(env)}")


class Var(Expr):
    def __init__(self, name):
        self.name = name

    def eval(self, env):
        return env[self.name]

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)


class Literal(Expr):
    def __init__(self, value):
        self.value = value

    def eval(self, env):
        return self.value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return repr_string(self.value)


class Binary(Expr):
    def __init__(self, left, right, op):
        self.left = left
        self.right = right
        self.op = op

    def eval(self, env):
        left_value = self.left.eval(env)
        right_value = self.right.eval(env)

        writer.debugln(
            f"[({self.left}) {op_names[self.op]} ({self.right})"
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

    def clone(self):
        # we can return the same object since it has no mutable state
        return self

    def resume(self, env):
        env[self.var.name] = self.expr.eval(env)
        writer.println(f"assigning {self.var.name} = {env[self.var.name]}")


class Define(Resumable):
    def __init__(self, var_name, initializer):
        super().__init__(name="define")
        self.var_name = var_name
        self.initializer = initializer

    def clone(self):
        # we can return the same object since it has no mutable state
        return self

    def resume(self, env):
        env.define(self.var_name, self.initializer.eval(env))


def iterate(resumable, args, env):
    try:
        resumable = resumable.new(args)
        while True:
            value = resumable.resume(env)
            writer.println(" --> [{}]".format(repr_string(value)))
    except StopIteration:
        pass


writer.println("-" * 80)
writer.println("range_ generator")
writer.println("-" * 80)

env = Env.new(name="global")
# for (item : range_(5)) {
#    println(item)
# }
#
# fun range(start, end) {
#    var i = start
#    while(i <= end) {
#       yield i
#       i = i + 1
#    }
# }
range_ = ResumableFunction(
    params=[Var("start"), Var("end")],
    body=ResumableBlock(
        [
            Define("i", Var("start")),
            ResumableWhile(
                LessEquals(Var("i"), Var("end")),
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
    name="range_",
)
writer.println("iterate(range_(0, 5))")
iterate(range_, {"start": 0, "end": 5}, env)
writer.println("-" * 80)

writer.println("iterate(range_(5, 10))")
iterate(range_, {"start": 5, "end": 10}, env)
writer.println("-" * 80)

it1 = range_.new({"start": 5, "end": 10})
it2 = range_.new({"start": 0, "end": 10})
writer.println(it1.resume(env))
writer.println(it2.resume(env))
writer.println("-" * 80)

writer.println(it1.resume(env))
writer.println(it2.resume(env))
writer.println("-" * 80)

try:
    it3 = range_.new({})
    assert False, "range_.new({}) should have thrown an exception"
except ValueError:
    pass
