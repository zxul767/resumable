from typing import TextIO, Callable


def assert_keywords_in_output(keywords: tuple[str, ...], stream: TextIO) -> None:
    _assert_keywords_pass_condition(
        keywords, lambda keyword, output: keyword in output, stream
    )


def assert_keywords_not_in_output(keywords: tuple[str, ...], stream: TextIO) -> None:
    _assert_keywords_pass_condition(
        keywords, lambda keyword, output: keyword not in output, stream
    )


def _assert_keywords_pass_condition(
    keywords: tuple[str, ...], condition: Callable[[str, str], bool], stream: TextIO
) -> None:
    output = _as_text(stream)
    for keyword in keywords:
        assert condition(keyword.lower(), output)


def assert_empty_output(stream: TextIO) -> None:
    assert _as_text(stream) == ""


def assert_exact_output(lines: tuple[str, ...], stream: TextIO) -> None:
    assert lines == tuple(_as_text(stream).splitlines())


def _as_text(stream: TextIO) -> str:
    getvalue = getattr(stream, "getvalue", None)
    assert callable(getvalue), "stream must be io.StringIO or io.BytesIO"
    return str(getvalue()).lower()
