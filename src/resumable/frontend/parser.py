import ast
from functools import lru_cache
from importlib.resources import files
from typing import Any, cast

from lark import Lark, Token, Transformer, Tree

from .ast_expressions import (
    Binary,
    BinaryOp,
    Call,
    Expression,
    Literal,
    Neg,
    Var,
)
from .ast_statements import (
    Assignment,
    Block,
    Declaration,
    ExpressionStatement,
    FunctionDeclaration,
    FunctionKind,
    If,
    Program,
    Return,
    Statement,
    VariableDeclaration,
    While,
    Yield,
)
from .semantic import validate_program


class AstTransformer(Transformer[Token, object]):
    def start(self, children: list[object]) -> Program:
        program = children[0]
        assert isinstance(program, Program)
        return program

    def program(self, children: list[object]) -> Program:
        declarations = [self._as_declaration(child) for child in children]
        return Program(declarations=declarations)

    def declaration(self, children: list[object]) -> object:
        [declaration] = children
        return declaration

    def statement(self, children: list[object]) -> object:
        [statement] = children
        return statement

    def parameters(self, children: list[object]) -> list[str]:
        return [str(child) for child in children]

    def fun_declaration(self, children: list[object]) -> FunctionDeclaration:
        return self._function_declaration("fun", children)

    def gen_declaration(self, children: list[object]) -> FunctionDeclaration:
        return self._function_declaration("gen", children)

    def _function_declaration(
        self, kind: FunctionKind, children: list[object]
    ) -> FunctionDeclaration:
        if len(children) == 2:
            [name, body] = children
            params: list[str] = []
        else:
            [name, params_value, body] = children
            if params_value is None:
                params = []
            else:
                assert isinstance(params_value, list)
                params_items = cast(list[object], params_value)
                params = [str(param) for param in params_items]
        assert isinstance(name, Token)
        assert isinstance(body, Block)
        return FunctionDeclaration(kind=kind, name=str(name), params=params, body=body)

    def block(self, children: list[object]) -> Block:
        declarations = [self._as_declaration(child) for child in children]
        return Block(declarations=declarations)

    def var_declaration(self, children: list[object]) -> VariableDeclaration:
        [name, initializer] = children
        assert isinstance(name, Token)
        assert isinstance(initializer, Expression)
        return VariableDeclaration(name=str(name), initializer=initializer)

    def assign(self, children: list[object]) -> Assignment:
        [name, value] = children
        assert isinstance(name, Token)
        assert isinstance(value, Expression)
        return Assignment(name=str(name), value=value)

    def expression_statement(self, children: list[object]) -> ExpressionStatement:
        [expr] = children
        assert isinstance(expr, Expression)
        return ExpressionStatement(expression=expr)

    def return_statement(self, children: list[object]) -> Return:
        if not children:
            return Return(value=None)
        [value] = children
        if value is None:
            return Return(value=None)
        assert isinstance(value, Expression)
        return Return(value=value)

    def yield_statement(self, children: list[object]) -> Yield:
        [value] = children
        assert isinstance(value, Expression)
        return Yield(value=value)

    def if_statement(self, children: list[object]) -> If:
        if len(children) == 2:
            [condition, then_branch] = children
            else_branch = None
        else:
            [condition, then_branch, else_branch] = children
        assert isinstance(condition, Expression)
        return If(
            condition=condition,
            then_branch=self._as_statement(then_branch),
            else_branch=None
            if else_branch is None
            else self._as_statement(else_branch),
        )

    def while_statement(self, children: list[object]) -> While:
        [condition, body] = children
        assert isinstance(condition, Expression)
        return While(condition=condition, body=self._as_statement(body))

    def arguments(self, children: list[object]) -> list[Expression]:
        return [self._as_expression(child) for child in children]

    def eq(self, children: list[object]) -> Expression:
        return self._binary(children, "==")

    def lt(self, children: list[object]) -> Expression:
        return self._binary(children, "<")

    def le(self, children: list[object]) -> Expression:
        return self._binary(children, "<=")

    def add(self, children: list[object]) -> Expression:
        return self._binary(children, "+")

    def sub(self, children: list[object]) -> Expression:
        return self._binary(children, "-")

    def mul(self, children: list[object]) -> Expression:
        return self._binary(children, "*")

    def div(self, children: list[object]) -> Expression:
        return self._binary(children, "/")

    def mod(self, children: list[object]) -> Expression:
        return self._binary(children, "mod")

    def _binary(self, children: list[object], op: BinaryOp) -> Expression:
        [left, right] = children
        return Binary(self._as_expression(left), self._as_expression(right), op)

    def neg(self, children: list[object]) -> Neg:
        [expr] = children
        return Neg(self._as_expression(expr))

    def call(self, children: list[object]) -> Call:
        if len(children) == 1:
            [name] = children
            args: list[Expression] = []
        else:
            [name, args_value] = children
            if args_value is None:
                args = []
            else:
                assert isinstance(args_value, list)
                args_items = cast(list[object], args_value)
                args = [self._as_expression(arg) for arg in args_items]
        assert isinstance(name, Token)
        return Call(callee_name=str(name), args=args)

    def var(self, children: list[object]) -> Var:
        [name] = children
        assert isinstance(name, Token)
        return Var(str(name))

    def number(self, children: list[object]) -> Literal:
        [number] = children
        assert isinstance(number, Token)
        return Literal(int(str(number)))

    def string(self, children: list[object]) -> Literal:
        [value] = children
        assert isinstance(value, Token)
        return Literal(ast.literal_eval(str(value)))

    def true(self, children: list[object]) -> Literal:
        return Literal(True)

    def false(self, children: list[object]) -> Literal:
        return Literal(False)

    def nil(self, children: list[object]) -> Literal:
        return Literal(None)

    def _as_expression(self, value: object) -> Expression:
        assert isinstance(value, Expression)
        return value

    def _as_statement(self, value: object) -> Statement:
        assert isinstance(
            value,
            (
                Block,
                VariableDeclaration,
                Assignment,
                ExpressionStatement,
                If,
                While,
                Return,
                Yield,
            ),
        )
        return value

    def _as_declaration(self, value: object) -> Declaration:
        if isinstance(value, FunctionDeclaration):
            return value
        return self._as_statement(value)


def _load_grammar_text() -> str:
    grammar_file = files("resumable.frontend").joinpath("grammar.lark")
    return grammar_file.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def get_parser() -> Lark:
    grammar = _load_grammar_text()
    return Lark(grammar, start="start", parser="lalr")


def parse_tree(source: str) -> Tree[Token]:
    parser: Any = get_parser()
    tree = parser.parse(source)
    return cast(Tree[Token], tree)


def parse_program(source: str) -> Program:
    parsed = parse_tree(source)
    program = AstTransformer().transform(parsed)
    assert isinstance(program, Program)
    return program


def parse_and_validate(source: str) -> Program:
    program = parse_program(source)
    validate_program(program)
    return program
