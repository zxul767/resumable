import abc
import operator
from typing import Any, Callable

from .runtime import Env, RuntimeContext

Value = Any
BinaryOperator = Callable[[Value, Value], Value]

op_names: dict[BinaryOperator, str] = {
    operator.__add__: "+",
    operator.__eq__: "==",
    operator.__le__: "<=",
    operator.__lt__: "<",
    operator.__mod__: "mod",
}


def repr_string(value: Value) -> str:
    if isinstance(value, str):
        return f"'{value}'"
    return str(value)


class Expr(abc.ABC):
    @abc.abstractmethod
    def eval(self, env: Env, context: RuntimeContext) -> Value:
        raise NotImplementedError


class Var(Expr):
    def __init__(self, name: str) -> None:
        self.name = name

    def eval(self, env: Env, context: RuntimeContext) -> Value:
        return env[self.name]

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return str(self)


class Literal(Expr):
    def __init__(self, value: Value) -> None:
        self.value = value

    def eval(self, env: Env, context: RuntimeContext) -> Value:
        return self.value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return repr_string(self.value)


class Binary(Expr):
    def __init__(self, left: Expr, right: Expr, op: BinaryOperator) -> None:
        self.left = left
        self.right = right
        self.op = op

    def eval(self, env: Env, context: RuntimeContext) -> Value:
        left_value = self.left.eval(env, context)
        right_value = self.right.eval(env, context)

        context.writer.debugln(
            f"[({self.left}) {op_names[self.op]} ({self.right})"
            + f" => {self.op(left_value, right_value)}]"
        )

        return self.op(left_value, right_value)

    def __repr__(self) -> str:
        return op_names[self.op]


class Equals(Binary):
    def __init__(self, left: Expr, right: Expr) -> None:
        super().__init__(left, right, operator.__eq__)


class Mod(Binary):
    def __init__(self, left: Expr, right: Expr) -> None:
        super().__init__(left, right, operator.__mod__)


class Less(Binary):
    def __init__(self, left: Expr, right: Expr) -> None:
        super().__init__(left, right, operator.__lt__)


class LessEquals(Binary):
    def __init__(self, left: Expr, right: Expr) -> None:
        super().__init__(left, right, operator.__le__)


class Sum(Binary):
    def __init__(self, left: Expr, right: Expr) -> None:
        super().__init__(left, right, operator.__add__)
