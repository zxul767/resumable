from __future__ import annotations

from ast_programs import build_range_function
from resumable import Env, iterate
from writer import surrounding_box_title, IndentingWriter

writer = IndentingWriter()


def run_demo() -> None:
    writer.println("RANGE GENERATOR", with_title_box=True)
    range_fn = build_range_function()

    globals_env = Env(name="global")
    with surrounding_box_title(writer):
        writer.println("iterate(range_(0, 0))")
        writer.newline(on_debug_only=True)
        iterate(range_fn.new({"start": 0, "end": 0}), globals_env)

    with surrounding_box_title(writer):
        writer.println("iterate(range_(5, 10))")
        writer.newline(on_debug_only=True)
        iterate(range_fn.new({"start": 5, "end": 10}), globals_env)


if __name__ == "__main__":
    run_demo()
