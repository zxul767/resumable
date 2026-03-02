from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from ..writer import IndentingWriter

Value = Any


@dataclass
class ProgramState:
    global_env: Env
    context: RuntimeContext


class CallableValue(Protocol):
    def __call__(self, args: list[Value], context: RuntimeContext) -> Value | None: ...


class InvalidOperation(Exception):
    """The object is in a state that does not allow this operation."""


@dataclass
class RuntimeContext:
    writer: IndentingWriter = field(default_factory=IndentingWriter)


class Env:
    def __init__(
        self,
        args: Mapping[str, Value] | None = None,
        parent_env: "Env | None" = None,
        name: str = "",
    ) -> None:
        self.parent_env = parent_env
        self._name = name
        self._key_values: dict[str, Value] = {}

        if args is not None:
            for key, value in args.items():
                self.define(key, value)

    def __getitem__(self, key: str) -> Value:
        if key in self._key_values:
            return self._key_values[key]

        if self.parent_env:
            return self.parent_env[key]

        raise KeyError(key)

    def define(self, key: str, value: Value) -> None:
        self._key_values[key] = value

    def __setitem__(self, key: str, value: Value) -> None:
        if key in self._key_values:
            self._key_values[key] = value
        elif self.parent_env:
            self.parent_env[key] = value
        else:
            raise KeyError(key)

    def all_vars(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self._name,
            "self": list(self._key_values.items()),
            "parent_env": None,
        }
        if self.parent_env is not None:
            result["parent_env"] = {**self.parent_env.all_vars()}
        return result

    def __repr__(self) -> str:
        chain = self.all_vars()
        result = ""
        while chain:
            result += f"{chain['self']}:{chain['name']}"
            chain = chain["parent_env"]
            if chain:
                result += " -> "
        return result
