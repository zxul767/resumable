import sys
from typing import TextIO, overload

from lark.exceptions import LarkError

from ..frontend.ast_statements import Program
from ..frontend.parser import parse_and_validate
from ..frontend.semantic import SemanticError
from .core import Env, ProgramState, RuntimeContext, format_value
from .statement_executor import execute_declaration
from .stdlib import install_stdlib


def parse_source_for_cli(source: str, stderr: TextIO) -> Program | None:
    try:
        return parse_and_validate(source)
    except (LarkError, SemanticError, ValueError) as error:
        print(f"Syntax error: {error}", file=stderr)
        return None
    except Exception as error:
        print(f"Syntax error (host): {error}", file=stderr)
        return None


def report_runtime_error(error: Exception, stderr: TextIO) -> None:
    if isinstance(error, StopIteration):
        if error.value is None:
            print("Runtime error: generator is exhausted", file=stderr)
            return
        print(
            f"Runtime error: generator is exhausted (final value: {format_value(error.value)})",
            file=stderr,
        )
        return
    print(f"Runtime error: {error}", file=stderr)


def run_for_cli(
    source: str,
    context: RuntimeContext | None = None,
    stderr: TextIO | None = None,
) -> ProgramState | None:
    stream = stderr if stderr is not None else sys.stderr

    program = parse_source_for_cli(source, stream)
    if program is None:
        return None

    try:
        return run(program, context)
    except Exception as error:
        report_runtime_error(error, stream)
        return None


@overload
def run(
    program_or_source: Program, context: RuntimeContext | None = None
) -> ProgramState: ...


@overload
def run(
    program_or_source: str, context: RuntimeContext | None = None
) -> ProgramState: ...


def run(
    program_or_source: Program | str, context: RuntimeContext | None = None
) -> ProgramState:
    if isinstance(program_or_source, str):
        program = parse_and_validate(program_or_source)
    else:
        program = program_or_source

    context = context or RuntimeContext()
    global_env = Env(name="global")
    install_stdlib(global_env)
    _run(program, global_env, context)

    return ProgramState(global_env=global_env, context=context)


def _run(program: Program, env: Env, context: RuntimeContext) -> None:
    for declaration in program.declarations:
        execute_declaration(declaration, env, context)
