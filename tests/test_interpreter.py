from io import StringIO

from resumable.runtime.interpreter import run_for_cli
from .helpers import assert_keywords_in_output


def test_interpreter_reports_syntax_error_to_stderr() -> None:
    stderr = StringIO()
    state = run_for_cli("fun broken( { return 1; }", stderr=stderr)

    assert state is None
    assert_keywords_in_output(("syntax", "error", "unexpected", "token"), stderr)


def test_interpreter_reports_runtime_error_to_stderr() -> None:
    source = """
    gen one() {
      yield 1;
    }

    var g = one();
    next(g);
    next(g);
    """
    stderr = StringIO()
    state = run_for_cli(source, stderr=stderr)

    assert state is None
    assert_keywords_in_output(("runtime", "error", "generator", "exhausted"), stderr)


def test_interpreter_reports_exhausted_generator_final_value() -> None:
    source = """
    gen one_then_return() {
      yield 1;
      return 99;
    }

    var g = one_then_return();
    next(g);
    next(g);
    """
    stderr = StringIO()
    state = run_for_cli(source, stderr=stderr)

    assert state is None
    assert_keywords_in_output(
        ("runtime", "error", "exhausted", "final value", "99"), stderr
    )
