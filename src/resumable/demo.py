from .runtime.core import RuntimeContext
from .runtime.interpreter import run
from .runtime.generator_compiler import instantiate_generator
from .runtime.generator import collect_values
from .snippets import range_generator_source
from .writer import surrounding_box_title, IndentingWriter


def run_demo() -> None:
    writer = IndentingWriter()
    state = run(
        range_generator_source(include_empty_sentinel=True),
        RuntimeContext(writer=writer),
    )

    with surrounding_box_title(writer, omit_lower_line=True):
        writer.println("RANGE GENERATOR")

    with surrounding_box_title(writer, omit_lower_line=True):
        writer.println("collect_values(range(0, 0))")
        writer.newline(on_debug_only=True)
        values = collect_values(
            instantiate_generator(state, "range", {"start": 0, "end": 0}),
            state.global_env,
            state.context,
        )
        writer.println(f" -> {values}")

    with surrounding_box_title(writer, omit_lower_line=True):
        writer.println("collect_values(range(5, 10))")
        writer.newline(on_debug_only=True)
        values = collect_values(
            instantiate_generator(state, "range", {"start": 5, "end": 10}),
            state.global_env,
            state.context,
        )
        writer.println(f" -> {values}")


if __name__ == "__main__":
    run_demo()
