from typing import TextIO


def assert_keywords_in_output(keywords: tuple[str, ...], stream: TextIO) -> None:
    getvalue = getattr(stream, "getvalue", None)
    assert callable(getvalue)
    output = str(getvalue()).lower()
    for keyword in keywords:
        assert keyword.lower() in output
