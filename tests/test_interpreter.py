from io import StringIO

from resumable.runtime.interpreter import run_for_cli
from .helpers import assert_keywords_in_output


def test_interpret_source_reports_syntax_error_to_stderr() -> None:
    stderr = StringIO()
    state = run_for_cli("fun broken( { return 1; }", stderr=stderr)

    assert state is None
    assert_keywords_in_output(("syntax", "error"), stderr)


def test_interpret_source_reports_runtime_error_to_stderr() -> None:
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
    assert_keywords_in_output(("runtime", "error"), stderr)
