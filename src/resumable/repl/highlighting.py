from typing import Any, Callable

from lark import Token
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style

from ..frontend.parser import get_parser


REPL_STYLE = Style.from_dict(
    {
        "keyword": "ansimagenta bold",
        "number": "ansicyan",
        "string": "ansigreen",
        "operator": "ansiyellow",
        "punctuation": "ansibrightblack",
    }
)


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
            append("", source)
            return lines

        cursor = 0
        for token in tokens:
            start_pos = token.start_pos if token.start_pos is not None else cursor
            end_pos = (
                token.end_pos
                if token.end_pos is not None
                else start_pos + len(token.value)
            )

            if start_pos > cursor:
                append("", source[cursor:start_pos])
            append(self._style_for_token(token), token.value)
            cursor = end_pos

        if cursor < len(source):
            append("", source[cursor:])
        return lines

    def _style_for_token(self, token: Token) -> str:
        if token.type in self.keyword_types:
            return "class:keyword"
        if token.type in self.number_types:
            return "class:number"
        if token.type in self.string_types:
            return "class:string"
        if token.type in self.operator_types:
            return "class:operator"
        if token.type in self.punctuation_types:
            return "class:punctuation"
        return ""
