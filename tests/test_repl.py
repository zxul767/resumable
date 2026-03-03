from io import StringIO

from resumable.repl.app import run_in_repl, is_source_complete, should_eval_source
from resumable.runtime.core import Env, RuntimeContext
from resumable.runtime.stdlib import install_stdlib
from .helpers import (
    assert_keywords_in_output,
    assert_keywords_not_in_output,
    assert_empty_output,
    assert_exact_output,
)

import pytest


def _create_repl_runtime() -> tuple[Env, RuntimeContext, StringIO, StringIO]:
    env = Env(name="repl-test")
    context = RuntimeContext()
    install_stdlib(env)
    stdout = StringIO()
    stderr = StringIO()
    return env, context, stdout, stderr


def test_repl_prints_expression_result() -> None:
    env, context, stdout, stderr = _create_repl_runtime()

    ok = run_in_repl("1 + 2;", env, context, stdout=stdout, stderr=stderr)

    assert ok is True
    assert stdout.getvalue().strip() == "3"
    assert_empty_output(stderr)


def test_repl_prints_last_expression_in_multi_statement_input() -> None:
    env, context, stdout, stderr = _create_repl_runtime()

    ok = run_in_repl("var i = 1; 2 * i;", env, context, stdout=stdout, stderr=stderr)

    assert ok is True
    assert stdout.getvalue().strip() == "2"
    assert_empty_output(stderr)


def test_repl_preserves_state_between_calls() -> None:
    env, context, stdout, stderr = _create_repl_runtime()

    assert (
        run_in_repl(
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
    assert run_in_repl("x;", env, context, stdout=stdout, stderr=stderr) is True
    assert stdout.getvalue().strip().endswith("11")
    assert_empty_output(stderr)


def test_repl_reports_syntax_errors() -> None:
    env, context, stdout, stderr = _create_repl_runtime()

    ok = run_in_repl("fun broken( {", env, context, stdout=stdout, stderr=stderr)

    assert ok is False
    assert_keywords_in_output(("syntax", "error"), stderr)


def test_is_complete_source_detects_incomplete_input() -> None:
    assert is_source_complete("fun f() {") is False
    assert is_source_complete("fun f() { return 1; }") is True


def test_should_submit_source_accepts_quit_commands_without_semicolon() -> None:
    assert should_eval_source("quit") is True
    assert should_eval_source("exit") is True


def test_repl_prints_language_booleans_and_nil() -> None:
    env, context, stdout, stderr = _create_repl_runtime()

    assert run_in_repl("true;", env, context, stdout=stdout, stderr=stderr)
    assert run_in_repl("false;", env, context, stdout=stdout, stderr=stderr)
    assert run_in_repl("nil;", env, context, stdout=stdout, stderr=stderr)

    assert_exact_output(("true", "false", "nil"), stdout)
    assert_empty_output(stderr)


def test_repl_suppresses_nil_result_for_call_expressions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    env, context, stdout, stderr = _create_repl_runtime()

    assert run_in_repl('print("x");', env, context, stdout=stdout, stderr=stderr)

    captured = capsys.readouterr()
    assert captured.out == "x"
    assert_empty_output(stdout)
    assert_empty_output(stderr)


def test_repl_prints_quoted_strings() -> None:
    env, context, stdout, stderr = _create_repl_runtime()

    assert run_in_repl('"hello";', env, context, stdout=stdout, stderr=stderr)

    assert stdout.getvalue().strip() == '"hello"'
    assert stderr.getvalue() == ""


def test_repl_accepts_float_literals() -> None:
    env, context, stdout, stderr = _create_repl_runtime()

    assert run_in_repl("10.32;", env, context, stdout=stdout, stderr=stderr)

    assert stdout.getvalue().strip() == "10.32"
    assert stderr.getvalue() == ""


def test_repl_reports_informative_runtime_errors() -> None:
    env, context, stdout, stderr = _create_repl_runtime()

    ok = run_in_repl("12 < true;", env, context, stdout=stdout, stderr=stderr)

    assert ok is False
    assert_empty_output(stdout)
    assert_keywords_in_output(
        ("runtime", "error", "invalid", "int", "bool"), stream=stderr
    )


def test_repl_runtime_errors_do_not_expose_host_type_names() -> None:
    env, context, stdout, stderr = _create_repl_runtime()

    ok = run_in_repl("nil * 12;", env, context, stdout=stdout, stderr=stderr)

    assert ok is False
    assert_empty_output(stdout)
    assert_keywords_in_output(
        ("runtime", "error", "invalid operands", "nil", "int"), stderr
    )
    assert_keywords_not_in_output(("nonetype",), stderr)
