from io import StringIO
from typing import Callable


def assert_keywords_in_output(keywords: tuple[str, ...], stream: StringIO) -> None:
    _assert_keywords_pass_condition(
        keywords, lambda keyword, output: keyword in output, stream
    )


def assert_keywords_not_in_output(keywords: tuple[str, ...], stream: StringIO) -> None:
    _assert_keywords_pass_condition(
        keywords, lambda keyword, output: keyword not in output, stream
    )


def _assert_keywords_pass_condition(
    keywords: tuple[str, ...], condition: Callable[[str, str], bool], stream: StringIO
) -> None:
    output = _as_text(stream)
    for keyword in keywords:
        assert condition(keyword.lower(), output)


def assert_empty_output(stream: StringIO) -> None:
    assert _as_text(stream) == ""


def assert_exact_output(lines: tuple[str, ...], stream: StringIO) -> None:
    assert lines == tuple(_as_text(stream).splitlines())


def _as_text(stream: StringIO) -> str:
    return stream.getvalue().lower()
