from dataclasses import dataclass, field
from typing import Any, Mapping

from .writer import IndentingWriter

Value = Any


@dataclass
class RuntimeContext:
    writer: IndentingWriter = field(default_factory=IndentingWriter)


class Env:
    def __init__(
        self,
        args: Mapping[str, Value] | None = None,
        enclosing: "Env | None" = None,
        name: str = "",
    ) -> None:
        self.enclosing = enclosing
        self._name = name
        self._key_values: dict[str, Value] = {}

        if args is not None:
            for key, value in args.items():
                self.define(key, value)

    def __getitem__(self, key: str) -> Value:
        if key in self._key_values:
            return self._key_values[key]

        if self.enclosing:
            return self.enclosing[key]

        raise KeyError(key)

    def define(self, key: str, value: Value) -> None:
        self._key_values[key] = value

    def __setitem__(self, key: str, value: Value) -> None:
        if key in self._key_values:
            self._key_values[key] = value
        elif self.enclosing:
            self.enclosing[key] = value
        else:
            raise KeyError(key)

    def all_vars(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self._name,
            "self": list(self._key_values.items()),
            "parent_env": None,
        }
        if self.enclosing is not None:
            result["parent_env"] = {**self.enclosing.all_vars()}
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
