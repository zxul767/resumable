from resumable.ast_programs import build_range_function
from resumable.runtime import RuntimeContext
from resumable.resumable import Env, ResumableBlock, collect_values, try_run_resumable


def test_try_run_resumable_respects_next_parent_index_zero() -> None:
    parent = ResumableBlock([], name="parent")
    child = ResumableBlock([], name="child")
    parent.index = 99

    try_run_resumable(
        child,
        Env(name="global"),
        RuntimeContext(),
        parent=parent,
        next_parent_index=0,
    )

    assert parent.index == 0


def test_range_semantics_across_small_grid() -> None:
    range_fn = build_range_function()
    globals_env = Env(name="global")

    for start in range(-2, 3):
        for end in range(-2, 3):
            values = collect_values(
                range_fn.new({"start": start, "end": end}),
                globals_env,
                RuntimeContext(),
            )
            if start == end:
                assert values == ["empty"]
            elif start < end:
                assert values == list(range(start, end))
            else:
                assert values == []
