from __future__ import annotations

import dataclasses
from collections.abc import Generator, Iterator, Sequence
from typing import TypeAlias

from .ast import (
    ArrayItemNode,
    ArrayNoCloseError,
    ArrayValueNode,
    EolNode,
    ExpectingNewFieldError,
    ExpectingSignEqualError,
    FieldNode,
    GlobalPrefixError,
    GlobalSuffixError,
    InvalidArrayItemError,
    LeadingNode,
    Node,
    PrefixNode,
    ScalarValueNode,
    Span,
    SuffixNode,
    TrailingNode,
    TypeNode,
    WikiNode,
    WikiSyntaxError,
    ast_to_text,
    parse_ast,
    unparse,
)

__all__ = (
    "ArrayItemNode",
    "ArrayNoCloseError",
    "ArrayValueNode",
    "EolNode",
    "ExpectingNewFieldError",
    "ExpectingSignEqualError",
    "Field",
    "FieldNode",
    "GlobalPrefixError",
    "GlobalSuffixError",
    "InvalidArrayItemError",
    "Item",
    "LeadingNode",
    "Node",
    "PrefixNode",
    "ScalarValueNode",
    "Span",
    "SuffixNode",
    "TrailingNode",
    "TypeNode",
    "ValueInputType",
    "ValueType",
    "Wiki",
    "WikiNode",
    "WikiSyntaxError",
    "ast_to_text",
    "ast_to_wiki",
    "parse",
    "parse_ast",
    "render",
    "try_parse",
    "unparse",
)


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Item:
    key: str = ""
    value: str = ""


ValueType: TypeAlias = str | tuple[Item, ...] | None
ValueInputType: TypeAlias = str | Sequence[Item] | None


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Field:
    key: str
    value: str | tuple[Item, ...] | None = None

    def __lt__(self, other: Field) -> bool:
        if self.key != other.key:
            return self.key < other.key

        # None < str < list[Item]
        return self.__value_emp_key() < other.__value_emp_key()

    def semantically_equal(self, other: Field) -> bool:
        if self.key != other.key:
            return False

        if isinstance(self.value, tuple) or isinstance(other.value, tuple):
            return self.value == other.value

        if not self.value and not other.value:
            return True

        return self.value == other.value

    def __value_emp_key(self) -> int:
        if self.value is None:
            return 1
        if isinstance(self.value, str):
            return 2
        return 3


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Wiki:
    type: str | None = None
    fields: tuple[Field, ...] = dataclasses.field(default_factory=tuple)
    eol: str = "\n"

    def has_key(self, key: str) -> bool:
        for f in self.fields:
            if f.key == key:
                return True
        return False

    def field_keys(self) -> Iterator[str]:
        yield from (f.key for f in self.fields)

    def non_zero(self) -> Wiki:
        fields: list[Field] = []
        for f in self.fields:
            value = f.value

            if not f.key.strip():
                if not f.value:
                    continue

            if not value:
                continue

            if isinstance(value, str):
                if value:
                    fields.append(f)
                continue

            if isinstance(value, tuple):  # pyright: ignore[reportUnnecessaryIsInstance]
                v = [x for x in value if x.key or x.value]
                if v:
                    fields.append(Field(key=f.key, value=tuple(v)))
                continue

        return Wiki(type=self.type, fields=tuple(fields), eol=self.eol)

    def get(self, key: str) -> str | tuple[Item, ...] | None:
        for f in self.fields:
            if f.key == key:
                return f.value
        return None

    def get_all(self, key: str) -> list[str]:
        for f in self.fields:
            if f.key == key:
                if not f.value:
                    return []
                if isinstance(f.value, tuple):
                    return [item.value for item in f.value]
                return [f.value]
        return []

    def get_as_items(self, key: str) -> list[Item]:
        for f in self.fields:
            if f.key == key:
                if not f.value:
                    return []
                if isinstance(f.value, tuple):
                    return list(f.value)
                return [Item(value=f.value)]
        return []

    def get_as_str(self, key: str) -> str:
        """
        return empty string if key not exists or empty,
        throw ValueError if value is a array
        """

        for f in self.fields:
            if f.key == key:
                if not f.value:
                    return ""

                if isinstance(f.value, tuple):
                    raise ValueError(f"value of {key!r} is {type(f.value)}, not str")

                return f.value

        return ""

    def semantically_equal(self, other: Wiki) -> bool:
        if self.type != other.type:
            return False

        if len(self.fields) != len(other.fields):
            return False

        return all(
            a.semantically_equal(b)
            for a, b in zip(sorted(self.fields), sorted(other.fields), strict=True)
        )

    def __str__(self) -> str:
        return render(self)

    def render(self) -> str:
        return render(self)


def try_parse(s: str) -> Wiki:
    """If failed to parse, return zero value"""
    try:
        return parse(s)
    except WikiSyntaxError:
        pass
    return Wiki()


def parse(s: str) -> Wiki:
    return ast_to_wiki(parse_ast(s))


def ast_to_wiki(node: WikiNode) -> Wiki:
    if node.type is None:
        return Wiki(eol=_detect_eol(node.text))

    fields: list[Field] = []
    for f in node.fields:
        if f.value is None:
            fields.append(Field(key=f.key))
            continue

        if isinstance(f.value, ScalarValueNode):
            fields.append(Field(key=f.key, value=f.value.value or None))
            continue

        items = tuple(Item(key=i.name, value=i.value) for i in f.value.items)
        fields.append(Field(key=f.key, value=items))

    return Wiki(type=node.type, fields=tuple(fields), eol=_detect_eol(node.text))


def _detect_eol(s: str) -> str:
    crlf_count = s.count("\r\n")
    if crlf_count:
        lf_count = s.count("\n") - crlf_count
        return "\r\n" if crlf_count >= lf_count else "\n"
    return "\n"


def render(w: Wiki) -> str:
    return w.eol.join(__render(w))


def __render(w: Wiki) -> Generator[str, None, None]:
    if w.type:
        yield "{{Infobox " + w.type
    else:
        yield "{{Infobox"

    for field in w.fields:
        if isinstance(field.value, str):
            yield f"|{field.key}= {field.value}"
        elif isinstance(field.value, tuple):
            yield f"|{field.key}={{"
            yield from __render_items(field.value)
            yield "}"
        elif field.value is None:
            # default editor will add a space
            yield f"|{field.key}= "
        else:
            raise TypeError("type not support", type(field.value))

    yield "}}"


def __render_items(s: tuple[Item, ...]) -> Generator[str, None, None]:
    for item in s:
        if item.key:
            yield f"[{item.key}|{item.value}]"
        else:
            yield f"[{item.value}]"


def read_array_item(line: str, lino: int) -> tuple[str, str]:
    """Read whole line as an array item, spaces are trimmed.

    read_array_item("[简体中文名|鲁鲁修]") => "简体中文名", "鲁鲁修"
    read_array_item("[简体中文名|]") => "简体中文名", ""
    read_array_item("[鲁鲁修]") => "", "鲁鲁修"

    Raises:
        InvalidArrayItemError: syntax error
    """
    if line[0] != "[" or line[-1] != "]":
        raise InvalidArrayItemError(lino, line)

    content = line[1:-1]
    key, sep, value = content.partition("|")
    if sep:
        return key.strip(), value.strip()
    return "", content.strip()


def read_start_line(line: str, lino: int) -> tuple[str, str]:
    """Read line without leading '|' as key value pair, spaces are trimmed.

    read_start_line("播放日期 = 2017年4月16日") => 播放日期, 2017年4月16日
    read_start_line("播放日期 = ") => 播放日期, ""

    Raises:
        ExpectingSignEqualError: syntax error
    """
    s = line[1:].strip()
    key, sep, value = s.partition("=")
    if not sep:
        raise ExpectingSignEqualError(lino, line)
    return key.strip(), value.strip()
