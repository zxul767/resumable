from dataclasses import dataclass
from typing import Literal

from .ast_expressions import Expression

FunctionKind = Literal["fun", "gen"]


@dataclass(frozen=True, slots=True)
class Program:
    declarations: list["Declaration"]


@dataclass(frozen=True, slots=True)
class FunctionDeclaration:
    kind: FunctionKind
    name: str
    params: list[str]
    body: "Block"


@dataclass(frozen=True, slots=True)
class Block:
    declarations: list["Declaration"]


@dataclass(frozen=True, slots=True)
class VariableDeclaration:
    name: str
    initializer: Expression


@dataclass(frozen=True, slots=True)
class Assignment:
    name: str
    value: Expression


# An expression can be used for its side effects even when its value is ignored.
# Examples:
# - var value = next(g);
# - var value = counter();
@dataclass(frozen=True, slots=True)
class ExpressionStatement:
    expression: Expression


@dataclass(frozen=True, slots=True)
class If:
    condition: Expression
    then_branch: "Statement"
    else_branch: "Statement | None"


@dataclass(frozen=True, slots=True)
class While:
    condition: Expression
    body: "Statement"


@dataclass(frozen=True, slots=True)
class Return:
    value: Expression | None


@dataclass(frozen=True, slots=True)
class Yield:
    value: Expression


Statement = (
    Block
    | VariableDeclaration
    | Assignment
    | ExpressionStatement
    | If
    | While
    | Return
    | Yield
)

Declaration = FunctionDeclaration | Statement
