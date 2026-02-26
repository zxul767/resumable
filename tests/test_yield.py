from resumable.ast_programs import build_range_function
from resumable.resumable import Env
from resumable.runtime import RuntimeContext


def test_three_generators_keep_independent_state() -> None:
    range_fn = build_range_function()
    a = range_fn.new({"start": 0, "end": 3}, name="a")
    b = range_fn.new({"start": 10, "end": 12}, name="b")
    c = range_fn.new({"start": 100, "end": 102}, name="c")

    globals_env = Env(name="global")
    context = RuntimeContext()
    assert a.resume(globals_env, context) == 0
    assert b.resume(globals_env, context) == 10
    assert c.resume(globals_env, context) == 100
    assert a.resume(globals_env, context) == 1
    assert b.resume(globals_env, context) == 11
    assert c.resume(globals_env, context) == 101
    assert a.resume(globals_env, context) == 2
