import sys
from pathlib import Path
from typing import Any, TextIO, cast

from lark import Token
from lark.exceptions import UnexpectedEOF, UnexpectedInput
from prompt_toolkit import PromptSession
from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.filters import has_focus
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

from ..frontend.ast_expressions import Call, Expression
from ..frontend.ast_statements import ExpressionStatement, Declaration
from ..frontend.parser import parse_tree
from ..runtime.core import Env, RuntimeContext, format_repl_value
from ..runtime.expression_evaluator import eval_expr
from ..runtime.interpreter import parse_for_cli, report_runtime_error
from ..runtime.statement_executor import execute_declaration
from ..runtime.stdlib import install_stdlib
from .highlighting import LarkGrammarLexer, get_repl_style

REPL_HELP = "Run/continue: Enter | New line: Ctrl-J | Quit: exit/quit/Ctrl-D"


def run_in_repl(
    source: str,
    env: Env,
    context: RuntimeContext,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> bool:
    program = parse_for_cli(source, stderr)
    if program is None:
        return False

    try:
        declarations = program.declarations
        for index, declaration in enumerate(declarations):
            if _try_eval_last_expression(index, declarations, env, context, stdout):
                continue
            execute_declaration(declaration, env, context)
        return True
    except Exception as error:
        report_runtime_error(error, stderr)
        return False


def _try_eval_last_expression(
    index: int,
    declarations: list[Declaration],
    env: Env,
    context: RuntimeContext,
    stdout: TextIO,
) -> bool:
    is_last = index == len(declarations) - 1
    if is_last and (expression := _as_expression(declarations[index])):
        value = eval_expr(expression, env, context)
        # `nil` is mostly returned by functions used for side effects,
        # so there is no point in printing it
        if not (value is None and isinstance(expression, Call)):
            print(format_repl_value(value), file=stdout)
        return True
    return False


def _as_expression(declaration: Declaration) -> Expression | None:
    if isinstance(declaration, ExpressionStatement):
        return declaration.expression
    return None


def is_source_complete(source: str) -> bool:
    try:
        parse_tree(source)
        return True
    except UnexpectedEOF:
        # parser reached end-of-input while still expecting more tokens
        # (for example an open block or unfinished expression).
        return False
    except UnexpectedInput as error:
        token = cast(Any, error).token
        # lark sometimes reports "unexpected end of input" as UnexpectedInput
        # with the synthetic $END token instead of raising UnexpectedEOF.
        if isinstance(token, Token) and token.type == "$END":
            return False
        # any other UnexpectedInput means input is complete but invalid.
        # we should submit so the user sees a syntax error message.
        return True
    except Exception:
        # for non-parser failures, avoid trapping the user in multiline mode.
        # submit and let the normal error-reporting path handle it.
        return True


def is_command_or_complete_source(source: str) -> bool:
    if source.strip() in {"exit", "quit"}:
        return True
    return is_source_complete(source)


def run_repl() -> None:
    context = RuntimeContext()
    env = Env(name="repl")
    install_stdlib(env)

    bindings = KeyBindings()

    def evaluate_if_complete(event: KeyPressEvent) -> None:
        buffer = event.current_buffer
        if is_command_or_complete_source(buffer.text):
            buffer.validate_and_handle()
        else:
            buffer.insert_text("\n")

    def indent(event: KeyPressEvent) -> None:
        event.current_buffer.insert_text("   ")

    def insert_newline(event: KeyPressEvent) -> None:
        event.current_buffer.insert_text("\n")

    default_input_focus = has_focus(DEFAULT_BUFFER)
    bindings.add("enter", filter=default_input_focus)(evaluate_if_complete)
    bindings.add("tab", filter=default_input_focus)(indent)
    bindings.add("c-j", filter=default_input_focus)(insert_newline)

    history_path = Path.home() / ".resumable_repl_history"
    session = PromptSession[str](history=FileHistory(str(history_path)))
    repl_style = get_repl_style()
    banner = r"""
███╗   ██╗ ██████╗ ██╗  ██╗    ██████╗ ███████╗██████╗ ██╗
████╗  ██║██╔═══██╗╚██╗██╔╝    ██╔══██╗██╔════╝██╔══██╗██║
██╔██╗ ██║██║   ██║ ╚███╔╝     ██████╔╝█████╗  ██████╔╝██║
██║╚██╗██║██║   ██║ ██╔██╗     ██╔══██╗██╔══╝  ██╔═══╝ ██║
██║ ╚████║╚██████╔╝██╔╝ ██╗    ██║  ██║███████╗██║     ███████╗
╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝    ╚═╝  ╚═╝╚══════╝╚═╝     ╚══════╝
        """

    print(banner)
    print(f"Resumable REPL. {REPL_HELP}")

    while True:
        try:
            source = session.prompt(
                ">>> ",
                multiline=True,
                prompt_continuation=lambda _width, _line, _wrap: "... ",
                key_bindings=bindings,
                lexer=LarkGrammarLexer(),
                style=repl_style,
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
