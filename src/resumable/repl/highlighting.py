import os
from importlib import import_module
from typing import Any, Callable

from lark import Token
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
from prompt_toolkit.styles.pygments import style_from_pygments_cls

from ..frontend.parser import get_parser


_DEFAULT_REPL_STYLE = Style.from_dict(
    {
        "pygments.keyword": "ansimagenta bold",
        "pygments.number": "ansicyan",
        "pygments.string": "ansigreen",
        "pygments.operator": "ansiyellow",
        "pygments.punctuation": "ansibrightblack",
    }
)

def _resolve_pygments_style(style_name: str) -> Any | None:
    try:
        styles = import_module("pygments.styles")
        get_style_by_name = getattr(styles, "get_style_by_name", None)
        if not callable(get_style_by_name):
            return None
        return get_style_by_name(style_name)
    except Exception:
        return None


def get_repl_style() -> Style:
    default_style_class = _resolve_pygments_style("friendly")
    if default_style_class is not None:
        default_style = style_from_pygments_cls(default_style_class)
    else:
        default_style = _DEFAULT_REPL_STYLE

    style_name = os.getenv("RESUMABLE_REPL_STYLE", "").strip().lower()
    if not style_name:
        return default_style
    style_class = _resolve_pygments_style(style_name)
    if style_class is None:
        return default_style
    return style_from_pygments_cls(style_class)


class LarkGrammarLexer(Lexer):
    def __init__(self) -> None:
        parser: Any = get_parser()
        terminals = parser.parser.lexer_conf.terminals

        self.keyword_types: set[str] = set()
        self.operator_types: set[str] = set()
        self.punctuation_types: set[str] = set()

        for terminal in terminals:
            pattern = terminal.pattern
            if pattern.type != "str":
                continue
            value = str(pattern.value)
            if value.isalpha():
                self.keyword_types.add(terminal.name)
            elif all(char in "(){}[];," for char in value):
                self.punctuation_types.add(terminal.name)
            else:
                self.operator_types.add(terminal.name)

        self.number_types: set[str] = {"NUMBER", "FLOAT"}
        self.string_types: set[str] = {"STRING"}

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        lines = self._highlight(document.text)

        def get_line(line_number: int) -> StyleAndTextTuples:
            if line_number < len(lines):
                return lines[line_number]
            return []

        return get_line

    def _highlight(self, source: str) -> list[StyleAndTextTuples]:
        lines: list[StyleAndTextTuples] = [[]]

        def append(style: str, text: str) -> None:
            if not text:
                return
            # prompt_toolkit expects already-split per-line fragments from lex_document.
            # We split while preserving style boundaries and create new line buckets
            # whenever a newline is encountered.
            parts = text.split("\n")
            for index, part in enumerate(parts):
                if part:
                    lines[-1].append((style, part))
                if index < len(parts) - 1:
                    lines.append([])

        try:
            # this should be `parser: Lark` but `pyright` throws:
            # `error: Type of "lex" is partially unknown`
            parser: Any = get_parser()
            tokens = list(parser.lex(source))
        except Exception:
            # During live editing, partial/incomplete input can fail lexing.
            # Fallback to plain text so editing remains responsive.
            append("", source)
            return lines

        cursor = 0
        for token in tokens:
            # Lark may not always populate absolute positions in every mode.
            # Normalize missing positions to a best-effort contiguous range.
            start_pos = token.start_pos if token.start_pos is not None else cursor
            end_pos = (
                token.end_pos
                if token.end_pos is not None
                else start_pos + len(token.value)
            )

            if start_pos > cursor:
                # Preserve un-tokenized gaps (typically whitespace/comments)
                # so source text is reproduced exactly in the rendered buffer.
                append("", source[cursor:start_pos])
            append(self._style_for_token(token), token.value)
            cursor = end_pos

        if cursor < len(source):
            # Preserve any trailing text after the last token.
            append("", source[cursor:])
        return lines

    def _style_for_token(self, token: Token) -> str:
        if token.type in self.keyword_types:
            return "class:pygments.keyword"
        if token.type in self.number_types:
            return "class:pygments.number"
        if token.type in self.string_types:
            return "class:pygments.string"
        if token.type in self.operator_types:
            return "class:pygments.operator"
        if token.type in self.punctuation_types:
            return "class:pygments.punctuation"
        return ""
