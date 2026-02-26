from .ast_programs import build_range_function
from .runtime import RuntimeContext
from .resumable import Env, iterate
from .writer import surrounding_box_title, IndentingWriter


def run_demo() -> None:
    writer = IndentingWriter()
    with surrounding_box_title(writer, omit_lower_line=True):
        writer.println("RANGE GENERATOR")
    range_fn = build_range_function()

    globals_env = Env(name="global")
    with surrounding_box_title(writer, omit_lower_line=True):
        writer.println("iterate(range_(0, 0))")
        writer.newline(on_debug_only=True)
        iterate(
            range_fn.new({"start": 0, "end": 0}),
            globals_env,
            RuntimeContext(writer=writer),
        )

    with surrounding_box_title(writer, omit_lower_line=True):
        writer.println("iterate(range_(5, 10))")
        writer.newline(on_debug_only=True)
        iterate(
            range_fn.new({"start": 5, "end": 10}),
            globals_env,
            RuntimeContext(writer=writer),
        )


if __name__ == "__main__":
    run_demo()
