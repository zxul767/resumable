from io import StringIO

import pytest

from resumable.repl.app import execute_repl_source, is_complete_source, should_submit_source
from resumable.runtime.core import Env, RuntimeContext
from resumable.runtime.stdlib import install_stdlib


def create_repl_runtime() -> tuple[Env, RuntimeContext, StringIO, StringIO]:
    env = Env(name="repl-test")
    context = RuntimeContext()
    install_stdlib(env)
    stdout = StringIO()
    stderr = StringIO()
    return env, context, stdout, stderr


def test_execute_repl_source_prints_expression_result() -> None:
    env, context, stdout, stderr = create_repl_runtime()

    ok = execute_repl_source("1 + 2;", env, context, stdout=stdout, stderr=stderr)

    assert ok is True
    assert stdout.getvalue().strip() == "3"
    assert stderr.getvalue() == ""


def test_execute_repl_source_preserves_state_between_calls() -> None:
    env, context, stdout, stderr = create_repl_runtime()

    assert (
        execute_repl_source(
            """
            var x = 10;
            x = x + 1;
            """,
            env,
            context,
            stdout=stdout,
            stderr=stderr,
        )
        is True
    )
    assert execute_repl_source("x;", env, context, stdout=stdout, stderr=stderr) is True
    assert stdout.getvalue().strip().endswith("11")
    assert stderr.getvalue() == ""


def test_execute_repl_source_reports_syntax_errors() -> None:
    env, context, stdout, stderr = create_repl_runtime()

    ok = execute_repl_source("fun broken( {", env, context, stdout=stdout, stderr=stderr)

    assert ok is False
    message = stderr.getvalue().lower()
    assert "syntax" in message
    assert "error" in message


def test_is_complete_source_detects_incomplete_input() -> None:
    assert is_complete_source("fun f() {") is False
    assert is_complete_source("fun f() { return 1; }") is True


def test_should_submit_source_accepts_quit_commands_without_semicolon() -> None:
    assert should_submit_source("quit") is True
    assert should_submit_source("exit") is True


def test_execute_repl_source_prints_language_booleans_and_nil() -> None:
    env, context, stdout, stderr = create_repl_runtime()

    assert execute_repl_source("true;", env, context, stdout=stdout, stderr=stderr)
    assert execute_repl_source("false;", env, context, stdout=stdout, stderr=stderr)
    assert execute_repl_source("nil;", env, context, stdout=stdout, stderr=stderr)

    assert stdout.getvalue().splitlines() == ["true", "false", "nil"]
    assert stderr.getvalue() == ""


def test_execute_repl_source_suppresses_nil_result_for_call_expressions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    env, context, stdout, stderr = create_repl_runtime()

    assert execute_repl_source('print("x");', env, context, stdout=stdout, stderr=stderr)

    captured = capsys.readouterr()
    assert captured.out == "x"
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == ""


def test_execute_repl_source_prints_quoted_strings() -> None:
    env, context, stdout, stderr = create_repl_runtime()

    assert execute_repl_source('"hello";', env, context, stdout=stdout, stderr=stderr)

    assert stdout.getvalue().strip() == '"hello"'
    assert stderr.getvalue() == ""


def test_execute_repl_source_accepts_float_literals() -> None:
    env, context, stdout, stderr = create_repl_runtime()

    assert execute_repl_source("10.32;", env, context, stdout=stdout, stderr=stderr)

    assert stdout.getvalue().strip() == "10.32"
    assert stderr.getvalue() == ""


def test_execute_repl_source_reports_informative_runtime_errors() -> None:
    env, context, stdout, stderr = create_repl_runtime()

    ok = execute_repl_source("12 < true;", env, context, stdout=stdout, stderr=stderr)

    assert ok is False
    assert stdout.getvalue() == ""
    message = stderr.getvalue().lower()
    assert "runtime" in message
    assert "error" in message
    assert "invalid operands" in message
    assert "int" in message
    assert "bool" in message


def test_execute_repl_source_runtime_errors_do_not_expose_host_type_names() -> None:
    env, context, stdout, stderr = create_repl_runtime()

    ok = execute_repl_source("nil * 12;", env, context, stdout=stdout, stderr=stderr)

    assert ok is False
    assert stdout.getvalue() == ""
    message = stderr.getvalue().lower()
    assert "runtime" in message
    assert "error" in message
    assert "invalid operands" in message
    assert "nil" in message
    assert "int" in message
    assert "nonetype" not in message
