import sys
from pathlib import Path
from typing import TextIO

from lark.exceptions import UnexpectedEOF, UnexpectedInput
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

from ..frontend.ast_expressions import Call
from ..frontend.ast_statements import ExpressionStatement
from ..frontend.parser import parse_tree
from ..runtime.core import Env, RuntimeContext, format_value
from ..runtime.expression_evaluator import eval_expr
from ..runtime.interpreter import parse_source_for_cli, report_runtime_error
from ..runtime.statement_executor import execute_declaration
from ..runtime.stdlib import install_stdlib
from .highlighting import LarkGrammarLexer, REPL_STYLE


def run_in_repl(
    source: str,
    env: Env,
    context: RuntimeContext,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> bool:
    program = parse_source_for_cli(source, stderr)
    if program is None:
        return False

    try:
        declarations = program.declarations
        for index, declaration in enumerate(declarations):
            is_last = index == len(declarations) - 1
            if is_last and isinstance(declaration, ExpressionStatement):
                expression = declaration.expression
                value = eval_expr(expression, env, context)
                if not (value is None and isinstance(expression, Call)):
                    print(format_value(value), file=stdout)
                continue
            execute_declaration(declaration, env, context)
        return True
    except Exception as error:
        report_runtime_error(error, stderr)
        return False


def is_complete_source(source: str) -> bool:
    try:
        parse_tree(source)
        return True
    except UnexpectedEOF:
        return False
    except UnexpectedInput as error:
        token = getattr(error, "token", None)
        if token is not None and getattr(token, "type", None) == "$END":
            return False
        return True
    except Exception:
        return True


def should_eval_source(source: str) -> bool:
    stripped = source.strip()
    if stripped in {"exit", "quit"}:
        return True
    return is_complete_source(source)


def run_repl() -> None:
    context = RuntimeContext()
    env = Env(name="repl")
    install_stdlib(env)

    bindings = KeyBindings()

    def evaluate_if_complete(event: KeyPressEvent) -> None:
        buffer = event.current_buffer
        if should_eval_source(buffer.text):
            buffer.validate_and_handle()
        else:
            buffer.insert_text("\n")

    def indent(event: KeyPressEvent) -> None:
        event.current_buffer.insert_text("   ")

    def insert_newline(event: KeyPressEvent) -> None:
        event.current_buffer.insert_text("\n")

    bindings.add("enter")(evaluate_if_complete)
    bindings.add("tab")(indent)
    bindings.add("c-j")(insert_newline)

    history_path = Path.home() / ".resumable_repl_history"
    session = PromptSession[str](history=FileHistory(str(history_path)))
    banner = r"""
███╗   ██╗ ██████╗ ██╗  ██╗    ██████╗ ███████╗██████╗ ██╗
████╗  ██║██╔═══██╗╚██╗██╔╝    ██╔══██╗██╔════╝██╔══██╗██║
██╔██╗ ██║██║   ██║ ╚███╔╝     ██████╔╝█████╗  ██████╔╝██║
██║╚██╗██║██║   ██║ ██╔██╗     ██╔══██╗██╔══╝  ██╔═══╝ ██║
██║ ╚████║╚██████╔╝██╔╝ ██╗    ██║  ██║███████╗██║     ███████╗
╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝    ╚═╝  ╚═╝╚══════╝╚═╝     ╚══════╝
        """

    print(banner)
    print(
        "Resumable REPL. Run/continue: Enter. New line: Ctrl-J. Quit: exit/quit/Ctrl-D."
    )

    while True:
        try:
            source = session.prompt(
                ">>> ",
                multiline=True,
                prompt_continuation=lambda _width, _line, _wrap: "... ",
                key_bindings=bindings,
                lexer=LarkGrammarLexer(),
                style=REPL_STYLE,
                bottom_toolbar="Run/continue: Enter | New line: Ctrl-J | Quit: exit/quit/Ctrl-D",
            )
        except EOFError:
            print("bye")
            break
        except KeyboardInterrupt:
            continue

        if not source.strip():
            continue
        if source.strip() in {"exit", "quit"}:
            print("bye")
            break
        run_in_repl(source, env, context, stdout=sys.stdout, stderr=sys.stderr)
