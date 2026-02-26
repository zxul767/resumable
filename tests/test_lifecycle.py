import pytest

from resumable.ast_programs import build_range_function
from resumable.resumable import Env, InvalidOperation, collect_values
from resumable.runtime import RuntimeContext


def test_resume_after_done_raises_invalid_operation() -> None:
    globals_env = Env(name="global")
    range_gen = build_range_function().new({"start": 0, "end": 1})

    context = RuntimeContext()
    assert collect_values(range_gen, globals_env, context) == [0]
    with pytest.raises(InvalidOperation):
        range_gen.resume(globals_env, context)
