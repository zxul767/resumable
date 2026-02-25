from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

# DEBUG = True
DEBUG = False


class IndentingWriter:
    def __init__(self, indent_size: int = 3) -> None:
        self._indent_size = indent_size
        self._indents = 0

    def debug(self, message: str) -> None:
        if DEBUG:
            self._print_indentation()
            print(message, end="")

    def debugln(self, message: str) -> None:
        if DEBUG:
            self.debug(message)
            print()

    def print(self, message: str, with_title_box: bool = False) -> None:
        if with_title_box:
            self.print_division_line()

        self._print_indentation()
        print(message, end="")

        if with_title_box:
            self.print_division_line()

    def println(self, message: str, with_title_box: bool = False) -> None:
        self.print(message + "\n", with_title_box)

    def indent(self) -> None:
        if DEBUG:
            self._indents += 1

    def dedent(self) -> None:
        if DEBUG:
            self._indents -= 1

    def newline(self, on_debug_only: bool = False) -> None:
        if on_debug_only:
            if DEBUG:
                print()
        else:
            print()

    def print_division_line(self, size: int = 80) -> None:
        print("-" * size)

    def _print_indentation(self) -> None:
        if DEBUG:
            print(" " * self._indent_size * self._indents, end="")


@contextmanager
def indented_output(output_writer: IndentingWriter) -> Iterator[None]:
    output_writer.indent()
    try:
        yield
    finally:
        output_writer.dedent()


@contextmanager
def surrounding_box_title(output_writer: IndentingWriter) -> Iterator[None]:
    output_writer.print_division_line()
    try:
        yield
    finally:
        output_writer.print_division_line()
