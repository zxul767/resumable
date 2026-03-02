from dataclasses import dataclass

from ..frontend.ast_statements import (
    Assignment,
    Block,
    Declaration,
    ExpressionStatement,
    FunctionDeclaration,
    If,
    Return,
    Statement,
    VariableDeclaration,
    While,
)
from .core import Env, RuntimeContext, Value
from .expression_evaluator import eval_expr
from .generator_compiler import instantiate_generator_value


@dataclass(frozen=True, slots=True)
class ReturnSignal(Exception):
    value: Value


@dataclass(frozen=True, slots=True)
class FunctionValue:
    declaration: FunctionDeclaration
    env: Env

    def __call__(self, args: list[Value], context: RuntimeContext) -> Value | None:
        declaration = self.declaration

        if len(args) != len(declaration.params):
            raise ValueError(
                f"wrong number of arguments for {declaration.name}: "
                f"expected {len(declaration.params)}, got {len(args)}"
            )

        if declaration.kind == "gen":
            return instantiate_generator_value(declaration, args, self.env)

        call_env = Env(parent_env=self.env, name=declaration.name)
        for param, value in zip(declaration.params, args, strict=True):
            call_env.define(param, value)

        try:
            execute_block(declaration.body, call_env, context, own_environment=False)
        except ReturnSignal as returned:
            return returned.value

        return None


def execute_declaration(
    declaration: Declaration,
    env: Env,
    context: RuntimeContext,
) -> None:
    if isinstance(declaration, FunctionDeclaration):
        env.define(declaration.name, FunctionValue(declaration=declaration, env=env))
        return

    execute_statement(declaration, env, context)


def execute_block(
    block: Block,
    env: Env,
    context: RuntimeContext,
    own_environment: bool = True,
) -> None:
    block_env = env
    if own_environment:
        block_env = Env(parent_env=env, name="block")

    for declaration in block.declarations:
        execute_declaration(declaration, block_env, context)


def execute_statement(
    statement: Statement,
    env: Env,
    context: RuntimeContext,
) -> None:
    if isinstance(statement, Block):
        execute_block(statement, env, context, own_environment=True)
        return

    if isinstance(statement, VariableDeclaration):
        env.define(statement.name, eval_expr(statement.initializer, env, context))
        return

    if isinstance(statement, Assignment):
        env[statement.name] = eval_expr(statement.value, env, context)
        return

    if isinstance(statement, ExpressionStatement):
        eval_expr(statement.expression, env, context)
        return

    if isinstance(statement, If):
        if eval_expr(statement.condition, env, context):
            execute_statement(statement.then_branch, env, context)
        elif statement.else_branch is not None:
            execute_statement(statement.else_branch, env, context)
        return

    if isinstance(statement, While):
        while eval_expr(statement.condition, env, context):
            execute_statement(statement.body, env, context)
        return

    if isinstance(statement, Return):
        value = None
        if statement.value is not None:
            value = eval_expr(statement.value, env, context)
        raise ReturnSignal(value)

    raise ValueError("yield is not supported by regular function execution")
