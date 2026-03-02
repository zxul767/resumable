from dataclasses import dataclass
from typing import Any, Literal as TypingLiteral

BinaryOp = TypingLiteral["+", "-", "*", "/", "==", "<=", "<", "mod"]


class Expression:
    pass


@dataclass(frozen=True, slots=True)
class Call(Expression):
    callee_name: str
    args: list[Expression]


@dataclass(frozen=True, slots=True)
class Var(Expression):
    name: str


@dataclass(frozen=True, slots=True)
class Literal(Expression):
    value: Any


@dataclass(frozen=True, slots=True)
class Binary(Expression):
    left: Expression
    right: Expression
    op: BinaryOp


@dataclass(frozen=True, slots=True)
class Neg(Expression):
    expr: Expression
