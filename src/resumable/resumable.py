from __future__ import annotations

import abc
from typing import Any, Callable, Mapping, Self, Sequence

from .ast_expressions import Expr, Var, repr_string
from .runtime import Env, RuntimeContext
from .writer import indented_output


Value = Any

def try_run_resumable(
    resumable: Resumable,
    env: Env,
    context: RuntimeContext,
    parent: Resumable,
    next_parent_index: int | None = None,
    on_resumable_done: Callable[[], None] | None = None,
) -> None:
    assert parent is not None, f"{parent} should not be None!"
    assert parent.index is not None, f"{parent.index} should not be None!"

    def update_parent_index() -> None:
        nonlocal parent
        if next_parent_index is not None:
            parent.index = next_parent_index
        else:
            assert parent.index is not None
            parent.index = parent.index + 1

    try:
        resumable.resume(env, context)
        update_parent_index()

    except YieldValue as _yield:
        if _yield.sender is resumable:
            update_parent_index()
        raise _yield

    except ResumableDone:
        update_parent_index()
        if on_resumable_done:
            context.writer.debugln("invoking on_resumable_done()")
            on_resumable_done()


class Resumable(abc.ABC):
    def __init__(
        self,
        children: Sequence[Resumable | None] | None = None,
        name: str | None = None,
    ) -> None:
        self.name = name or ""
        self.children = list(children) if children is not None else []
        self.index: int | None = 0

    @abc.abstractmethod
    def clone(self, name: str = "") -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def resume(self, env: Env, context: RuntimeContext) -> Value | None:
        raise NotImplementedError

    def _mark_as_done(self, _env: Env) -> None:
        self.index = None
        raise ResumableDone

    def reset(self, first_time: bool = False) -> None:
        self.index = 0
        if not first_time:
            self._reset_children()

    def _reset_children(self) -> None:
        for child in self.children:
            if child:
                child.reset()

    def _raise_if_done(self) -> None:
        if self.index is None:
            raise InvalidOperation(
                f"This resumable ({self}) cannot be resumed in the terminal `done` state!"
            )

    def __repr__(self) -> str:
        return self.name.upper()


class NonStatefulResumable(Resumable):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def clone(self, name: str = "") -> Self:
        return self


class Yield(NonStatefulResumable):
    def __init__(self, expr: Expr) -> None:
        super().__init__(name="yield")
        self._expr = expr

    def resume(self, env: Env, context: RuntimeContext) -> None:
        value = self._expr.eval(env, context)
        context.writer.debug(repr_string(value))
        raise YieldValue(value, sender=self)


class YieldValue(Exception):
    def __init__(self, value: Value, sender: Resumable) -> None:
        self.value = value
        self.sender = sender


class ResumableFunction(Resumable):
    def __init__(self, params: list[Var], body: ResumableBlock, name: str = "") -> None:
        super().__init__(name=name, children=[body])
        self._params = params
        self._body = body
        self._env: Env | None = None

    def clone(self, name: str = "") -> ResumableFunction:
        return ResumableFunction(
            params=self._params,
            body=self._body.clone(),
            name=name or self.name,
        )

    def resume(self, env: Env, context: RuntimeContext) -> Value:
        self._raise_if_done()

        if self._env is None:
            raise ValueError("`new` needs to be invoked to generate a new instance!")

        try:
            self._env.enclosing = env
            context.writer.debugln("resuming function...")
            self._body.resume(self._env, context)

        except YieldValue as _yield:
            return _yield.value

        except ResumableDone:
            self._mark_as_done(env)

        raise RuntimeError(
            "Unreachable state: resumable function did not yield or finish"
        )

    def reset(self, first_time: bool = False) -> None:
        raise ValueError(
            f"`ResumableFunction`s cannot be reset by design! first_time={first_time}"
        )

    def new(
        self, args: Mapping[str, Value] | None = None, name: str = ""
    ) -> ResumableFunction:
        self._validate_call_args(args)
        cloned_function = self.clone(name=name)
        cloned_function._env = Env(args, name=self.name)
        return cloned_function

    def _validate_call_args(self, args: Mapping[str, Value] | None) -> None:
        if not isinstance(args, Mapping):
            raise ValueError("Expected arguments as a dictionary-like mapping")

        seen: set[str] = set()
        duplicates: set[str] = set()
        for param in self._params:
            if param.name in seen:
                duplicates.add(param.name)
            seen.add(param.name)

        if duplicates:
            raise ValueError(f"Duplicate parameter names: {sorted(duplicates)}")

        param_names = {param.name for param in self._params}
        missing = param_names - set(args.keys())
        if missing:
            raise ValueError(f"Required arguments are missing: {sorted(missing)}")
        extra = set(args.keys()) - param_names
        if extra:
            raise ValueError(f"Unexpected arguments: {sorted(extra)}")


class ResumableBlock(Resumable):
    def __init__(
        self,
        stmts: list[Resumable],
        name: str = "block",
        own_environment: bool = True,
    ) -> None:
        super().__init__(name=name, children=stmts)
        self.stmts = stmts
        self._own_environment = own_environment
        self._env: Env | None = None
        self.reset(first_time=True)

    def clone(self, name: str = "") -> ResumableBlock:
        return ResumableBlock(
            stmts=[stmt.clone() for stmt in self.stmts],
            name=name or self.name,
            own_environment=self._own_environment,
        )

    def resume(self, env: Env, context: RuntimeContext) -> None:
        self._raise_if_done()

        with indented_output(context.writer):
            self._execute_statements(env, context)
            context.writer.debugln(f"({self.name}:block) completed")
        self._mark_as_done(env)

    def _execute_statements(self, env: Env, context: RuntimeContext) -> None:
        assert self.index is not None, "BlockResumable cannot execute when finished"

        env = self._maybe_chain_environment(env)

        if self.index < len(self.stmts):
            context.writer.debugln(
                f"executing ({self.name}:block) in env ({repr(env)})"
            )

        while self.index < len(self.stmts):
            stmt = self.stmts[self.index]
            context.writer.debugln(f"[{self.index}]({stmt.name}): ")
            with indented_output(context.writer):
                try_run_resumable(
                    stmt,
                    env,
                    context,
                    parent=self,
                    next_parent_index=self.index + 1,
                )

    def reset(self, first_time: bool = False) -> None:
        super().reset(first_time)
        self._env = None
        if self._own_environment:
            self._env = Env(name=self.name)

    def _maybe_chain_environment(self, env: Env) -> Env:
        if self._env is not None:
            self._env.enclosing = env
            env = self._env
        return env


class ResumableWhile(Resumable):
    def __init__(
        self, condition: Expr, body: ResumableBlock, name: str = "while"
    ) -> None:
        super().__init__(name=name, children=[body])
        self.condition = condition
        self.body = body
        self._instructions: dict[int | None, Callable[[Env, RuntimeContext], None]] = {
            0: self._execute_condition,
            1: self._execute_body,
            None: lambda env, _ctx: self._mark_as_done(env),
        }
        self.reset(first_time=True)

    def clone(self, name: str = "") -> ResumableWhile:
        return ResumableWhile(
            condition=self.condition,
            body=self.body.clone(),
            name=name or self.name,
        )

    def resume(self, env: Env, context: RuntimeContext) -> None:
        while True:
            self._instructions[self.index](env, context)

    def _execute_condition(self, env: Env, context: RuntimeContext) -> None:
        context.writer.debugln(f"evaluating condition ({self.name})...")
        if self.condition.eval(env, context):
            with indented_output(context.writer):
                self._execute_body(env, context)
        else:
            self._mark_as_done(env)

    def _execute_body(self, env: Env, context: RuntimeContext) -> None:
        self.index = 1
        try_run_resumable(
            self.body,
            env,
            context,
            parent=self,
            next_parent_index=0,
            on_resumable_done=self.reset,
        )


class ResumableIf(Resumable):
    def __init__(
        self,
        condition: Expr,
        then: Resumable,
        else_: Resumable | None = None,
        name: str = "if",
    ) -> None:
        assert then is not None, "`then` branch is not optional"

        super().__init__(name=name, children=[then, else_])
        self.condition = condition
        self.then = then
        self.else_ = else_
        self._instructions: dict[int | None, Callable[[Env, RuntimeContext], None]] = {
            0: self._execute_condition,
            1: self._execute_if_branch,
            2: self._execute_else_branch,
            3: lambda env, _ctx: self._mark_as_done(env),
        }
        self._condition_value: Value | None = None
        self.reset(first_time=True)

    def clone(self, name: str = "") -> ResumableIf:
        return ResumableIf(
            condition=self.condition,
            then=self.then.clone(),
            else_=self.else_.clone() if self.else_ else None,
            name=name or self.name,
        )

    def resume(self, env: Env, context: RuntimeContext) -> None:
        self._instructions[self.index](env, context)

    def _execute_condition(self, env: Env, context: RuntimeContext) -> None:
        if self._condition_value is None:
            context.writer.debug(f"evaluating condition ({self.name}): ")
            self._condition_value = self.condition.eval(env, context)

        if self._condition_value:
            self._execute_if_branch(env, context)
        elif self.else_:
            self._execute_else_branch(env, context)

        self._mark_as_done(env)

    def _execute_if_branch(self, env: Env, context: RuntimeContext) -> None:
        self.index = 1
        context.writer.debugln("then branch")
        try_run_resumable(self.then, env, context, parent=self, next_parent_index=3)
        self._mark_as_done(env)

    def _execute_else_branch(self, env: Env, context: RuntimeContext) -> None:
        self.index = 2
        context.writer.debugln("else branch")
        assert self.else_ is not None
        try_run_resumable(self.else_, env, context, parent=self, next_parent_index=3)
        self._mark_as_done(env)

    def reset(self, first_time: bool = False) -> None:
        super().reset(first_time)
        self._condition_value = None


class Print(NonStatefulResumable):
    def __init__(self, expr: Expr) -> None:
        super().__init__(name="print")
        self.expr = expr

    def resume(self, env: Env, context: RuntimeContext) -> None:
        context.writer.println(f"printing {self.expr.eval(env, context)}")


class InvalidOperation(Exception):
    """The object is in a state that does not allow this operation."""


class ResumableDone(Exception):
    """Signals that a resumable statement has completed its execution entirely."""


class Assign(NonStatefulResumable):
    def __init__(self, var: Var, expr: Expr) -> None:
        super().__init__(name="assign")
        self._var = var
        self._expr = expr

    def resume(self, env: Env, context: RuntimeContext) -> None:
        env[self._var.name] = self._expr.eval(env, context)
        context.writer.debugln(f"assigning {self._var.name} = {env[self._var.name]}")


class Define(NonStatefulResumable):
    def __init__(self, var_name: str, initializer: Expr) -> None:
        super().__init__(name="define")
        self._var_name = var_name
        self._initializer = initializer

    def resume(self, env: Env, context: RuntimeContext) -> None:
        value = self._initializer.eval(env, context)
        context.writer.debugln(f"defining {self._var_name} = {value}")
        env.define(self._var_name, value)


def iterate(
    resumable: ResumableFunction,
    env: Env,
    context: RuntimeContext,
) -> list[Value]:
    values: list[Value] = []
    try:
        context.writer.newline()
        while True:
            value = resumable.resume(env, context)
            values.append(value)
            context.writer.println(f" --> [{repr_string(value)}]")
            context.writer.newline()
    except ResumableDone:
        return values


def collect_values(
    resumable: ResumableFunction,
    env: Env,
    context: RuntimeContext,
) -> list[Value]:
    values: list[Value] = []
    try:
        while True:
            values.append(resumable.resume(env, context))
    except ResumableDone:
        return values
