from dataclasses import dataclass
from typing import Mapping, cast

from ..frontend.ast_expressions import Var
from .core import ProgramState
from ..frontend.ast_statements import (
    Assignment,
    Block,
    ExpressionStatement,
    FunctionDeclaration,
    If,
    Return as ReturnStatement,
    Statement,
    VariableDeclaration,
    While,
    Yield as YieldStatement,
)
from .resumable import (
    ResumableAssignment,
    ResumableDefine,
    ResumableEvaluateExpression,
    Resumable,
    ResumableBlock,
    Generator,
    ResumableIf,
    ResumableWhile,
    ResumableReturn,
    ResumableYield,
    collect_values,
)
from .core import CallableValue, Env, RuntimeContext, Value


@dataclass(frozen=True, slots=True)
class GeneratorValue:
    generator: Generator
    env: Env

    def next_value(self, context: RuntimeContext) -> Value | None:
        return self.generator.resume(self.env, context)

    def collect(self, context: RuntimeContext) -> list[Value]:
        return collect_values(self.generator, self.env, context)


def instantiate_generator_value(
    declaration: FunctionDeclaration,
    args: list[Value],
    closure_env: Env,
) -> GeneratorValue:
    arg_mapping = {
        name: value for name, value in zip(declaration.params, args, strict=True)
    }
    compiled = compile_generator_function(declaration)
    generator = compiled.new(arg_mapping)
    return GeneratorValue(generator=generator, env=closure_env)


def instantiate_generator(
    state: ProgramState,
    name: str,
    args: Mapping[str, Value],
    instance_name: str = "",
) -> Generator:
    value = state.global_env[name]
    if not callable(value):
        raise ValueError(f"{name} is not a function")

    declaration = getattr(value, "declaration", None)
    if not isinstance(declaration, FunctionDeclaration):
        raise ValueError(f"{name} is not a function")
    if declaration.kind != "gen":
        raise ValueError(f"{name} is not a generator function")

    call_args: list[Value] = []
    for param_name in declaration.params:
        if param_name not in args:
            raise ValueError(f"Required arguments are missing: ['{param_name}']")
        call_args.append(args[param_name])
    extra = sorted(set(args.keys()) - set(declaration.params))
    if extra:
        raise ValueError(f"Unexpected arguments: {extra}")

    callable_value = cast(CallableValue, value)
    generator_value = callable_value(call_args, state.context)
    if not isinstance(generator_value, GeneratorValue):
        raise ValueError(f"{name} did not return a generator instance")
    if instance_name:
        generator_value.generator.name = instance_name
    return generator_value.generator


def compile_generator_function(declaration: FunctionDeclaration) -> Generator:
    if declaration.kind != "gen":
        raise ValueError(f"Expected generator declaration, got: {declaration.kind}")

    params = [Var(name) for name in declaration.params]
    body = _compile_block(declaration.body, own_environment=False, name="function")
    return Generator(params=params, body=body, name=declaration.name)


def _compile_block(
    block: Block,
    own_environment: bool,
    name: str,
) -> ResumableBlock:
    statements: list[Resumable] = []
    for declaration in block.declarations:
        if isinstance(declaration, FunctionDeclaration):
            raise ValueError(
                "nested function declarations are not supported in generators"
            )
        statements.append(_compile_statement(declaration))
    return ResumableBlock(
        statements=statements,
        own_environment=own_environment,
        name=name,
    )


def _compile_statement(statement: Statement) -> Resumable:
    if isinstance(statement, Block):
        return _compile_block(statement, own_environment=True, name="block")

    if isinstance(statement, VariableDeclaration):
        return ResumableDefine(statement.name, statement.initializer)

    if isinstance(statement, Assignment):
        return ResumableAssignment(Var(statement.name), statement.value)

    if isinstance(statement, ExpressionStatement):
        return ResumableEvaluateExpression(statement.expression)

    if isinstance(statement, If):
        else_branch: Resumable | None = None
        if statement.else_branch is not None:
            else_branch = _compile_statement(statement.else_branch)
        return ResumableIf(
            condition=statement.condition,
            then=_compile_statement(statement.then_branch),
            else_=else_branch,
        )

    if isinstance(statement, While):
        body = _compile_statement(statement.body)
        if isinstance(body, ResumableBlock):
            while_body = body
        else:
            while_body = ResumableBlock([body], own_environment=False, name="while")
        return ResumableWhile(statement.condition, body=while_body)

    if isinstance(statement, ReturnStatement):
        return ResumableReturn(statement.value)

    assert isinstance(statement, YieldStatement)
    return ResumableYield(statement.value)
