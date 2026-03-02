from .core import Env, RuntimeContext, Value
from .generator_compiler import GeneratorValue


class NextBuiltin:
    def __call__(self, args: list[Value], context: RuntimeContext) -> Value | None:
        _require_one_arg(args, "next")

        candidate = args[0]
        if not isinstance(candidate, GeneratorValue):
            raise ValueError("next expects a generator instance")
        return candidate.next_value(context)


class CollectBuiltin:
    def __call__(self, args: list[Value], context: RuntimeContext) -> list[Value]:
        _require_one_arg(args, "collect")

        candidate = args[0]
        if not isinstance(candidate, GeneratorValue):
            raise ValueError("collect expects a generator instance")
        return candidate.collect(context)


def install_stdlib(env: Env) -> None:
    env.define("next", NextBuiltin())
    env.define("collect", CollectBuiltin())


def _require_one_arg(args: list[Value], function_name: str) -> None:
    if len(args) != 1:
        raise ValueError(f"{function_name} expects exactly one argument")
