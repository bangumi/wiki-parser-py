from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

__all__ = [
    "ArrayNoCloseError",
    "DuplicatedKeyError",
    "ExpectingNewFieldError",
    "ExpectingSignEqualError",
    "Field",
    "GlobalPrefixError",
    "GlobalSuffixError",
    "InvalidArrayItemError",
    "Item",
    "Wiki",
    "WikiSyntaxError",
    "parse",
    "render",
    "try_parse",
    "ValueType",
    "ValueInputType",
]


class Item:
    key: str
    value: str

    def __init__(self, *, key: str = "", value: str = "") -> None: ...


ValueType: TypeAlias = str | tuple[Item, ...] | None
ValueInputType: TypeAlias = str | Sequence[Item] | None


class Field:
    key: str
    value: ValueType

    def __init__(self, *, key: str, value: ValueType = None) -> None: ...
    def __lt__(self, other: Field) -> bool: ...
    def semantically_equal(self, other: Field) -> bool: ...


class Wiki:
    type: str | None
    fields: tuple[Field, ...]
    _eol: str

    def __init__(
        self,
        *,
        type: str | None = None,
        fields: tuple[Field, ...] = (),
        _eol: str = "\n",
    ) -> None: ...
    def keys(self) -> tuple[str, ...]: ...
    def field_keys(self) -> tuple[str, ...]: ...
    def non_zero(self) -> Wiki: ...
    def get(self, key: str) -> ValueType: ...
    def get_all(self, key: str) -> list[str]: ...
    def get_as_items(self, key: str) -> list[Item]: ...
    def get_as_str(self, key: str) -> str: ...
    def set(self, key: str, value: ValueInputType = None) -> Wiki: ...
    def index_of(self, key: str) -> int: ...
    def set_or_insert(self, key: str, value: ValueInputType, index: int) -> Wiki: ...
    def set_values(self, values: dict[str, ValueType]) -> Wiki: ...
    def remove(self, key: str) -> Wiki: ...
    def semantically_equal(self, other: Wiki) -> bool: ...
    def remove_duplicated_fields(self) -> Wiki: ...
    def render(self) -> str: ...


class DuplicatedKeyError(Exception):
    keys: list[str]

    def __init__(self, keys: list[str]) -> None: ...


class WikiSyntaxError(Exception):
    lino: int | None
    line: str | None
    message: str

    def __init__(
        self,
        lino: int | None = None,
        line: str | None = None,
        message: str = "",
    ) -> None: ...


class GlobalPrefixError(WikiSyntaxError): ...


class GlobalSuffixError(WikiSyntaxError): ...


class ArrayNoCloseError(WikiSyntaxError): ...


class InvalidArrayItemError(WikiSyntaxError): ...


class ExpectingNewFieldError(WikiSyntaxError): ...


class ExpectingSignEqualError(WikiSyntaxError): ...


def try_parse(s: str) -> Wiki: ...
def parse(s: str) -> Wiki: ...
def render(w: Wiki) -> str: ...
