from .core import Env, RuntimeContext, Value, format_value
from .generator_compiler import GeneratorValue
from .generator import collect_values


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

        value = args[0]
        if not isinstance(value, GeneratorValue):
            raise ValueError("collect expects a generator instance")
        return collect_values(value.generator, value.env, context)


class PrintBuiltin:
    def __call__(self, args: list[Value], _context: RuntimeContext) -> None:
        _require_zero_or_one_arg(args, "print")
        if not args:
            print("", end="")
            return
        value = args[0]
        if isinstance(value, str):
            print(value, end="")
            return
        print(format_value(value), end="")


class PrintlnBuiltin:
    def __call__(self, args: list[Value], _context: RuntimeContext) -> None:
        _require_zero_or_one_arg(args, "println")
        if not args:
            print("")
            return
        value = args[0]
        if isinstance(value, str):
            print(value)
            return
        print(format_value(value))


def install_stdlib(env: Env) -> None:
    env.define("next", NextBuiltin())
    env.define("collect", CollectBuiltin())
    env.define("print", PrintBuiltin())
    env.define("println", PrintlnBuiltin())


def _require_one_arg(args: list[Value], function_name: str) -> None:
    if len(args) != 1:
        raise ValueError(f"{function_name} expects exactly one argument")


def _require_zero_or_one_arg(args: list[Value], function_name: str) -> None:
    if len(args) > 1:
        raise ValueError(f"{function_name} expects at most one argument")
