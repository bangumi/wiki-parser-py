from __future__ import annotations

import dataclasses
from collections import OrderedDict
from collections.abc import Generator

from typing_extensions import deprecated

__all__ = (
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
)


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Item:
    key: str = ""
    value: str = ""


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
    _eol: str = "\n"

    _keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "_keys", tuple(f.key for f in self.fields))

    def keys(self) -> tuple[str, ...]:
        return self._keys

    def field_keys(self) -> tuple[str, ...]:
        return self._keys

    def non_zero(self) -> Wiki:
        fields = []
        for f in self.fields:
            value = f.value

            if not value:
                continue

            if isinstance(value, str):
                if value:
                    fields.append(f)
                continue

            if isinstance(value, list):
                v = [x for x in value if x.key or x.value]
                if v:
                    fields.append(Field(key=f.key, value=tuple(v)))
                continue

        return Wiki(type=self.type, fields=tuple(fields), _eol=self._eol)

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

    @deprecated("use get_as_str instead")
    def get_str(self, key: str) -> str:
        for f in self.fields:
            if f.key == key:
                if isinstance(f.value, str):
                    return f.value
                raise ValueError(f"value of {key!r} is {type(f.value)}, not str")

        return ""

    def set(self, key: str, value: str | tuple[Item, ...] | None = None) -> Wiki:
        """Update or append field value"""
        return self.__set(field=Field(key=key, value=value))

    def index_of(self, key: str) -> int:
        """Find index by field key.

        This method doesn't raise IndexError but return length of fields,
        to work with `set_or_insert`

        Do not use this method to check if key exists in fields, ust `key in wiki.keys()` instead
        """
        for i, f in enumerate(self.fields):
            if f.key == key:
                return i
        return len(self.fields)

    def set_or_insert(
        self, key: str, value: str | tuple[Item, ...] | None, index: int
    ) -> Wiki:
        """If key exists, update current value.
        Overview insert field after give index

        Could be used with `index_of` to update

        ```python
        w = w.set_or_insert(
            "b",
            ...,
            w.index_of("a") + 1,
        )
        ```

        This will insert field `b` after field `a` if field 'a' exists, or append it to the end.
        """
        if key in self.keys():
            return self.__set(field=Field(key=key, value=value))

        fields = list(self.fields)
        fields.insert(index, Field(key=key, value=value))

        return Wiki(type=self.type, fields=tuple(fields), _eol=self._eol)

    def set_values(self, values: dict[str, str | tuple[Item, ...] | None]) -> Wiki:
        w = self
        for key, value in values.items():
            w = w.__set(field=Field(key=key, value=value))
        return w

    def __set(self, field: Field) -> Wiki:
        fields = []
        found = False
        for f in self.fields:
            if f.key != field.key:
                fields.append(f)
                continue

            if found:
                continue
            fields.append(field)
            found = True

        if not found:
            fields.append(field)

        return Wiki(type=self.type, fields=tuple(fields), _eol=self._eol)

    def remove(self, key: str) -> Wiki:
        fields = tuple(f for f in self.fields if f.key != key)
        return Wiki(type=self.type, fields=fields, _eol=self._eol)

    def semantically_equal(self, other: Wiki) -> bool:
        if self.type != other.type:
            return False

        if len(self.fields) != len(other.fields):
            return False

        return all(
            a.semantically_equal(b)
            for a, b in zip(sorted(self.fields), sorted(other.fields), strict=True)
        )

    def remove_duplicated_fields(self) -> Wiki:
        """Try remove duplicated fields, empty fields will be override"""
        fields: OrderedDict[str, str | tuple[Item, ...] | None] = OrderedDict()
        duplicated_keys: list[str] = []
        for f in self.fields:
            if f.key in duplicated_keys:
                continue

            if f.key not in fields:
                fields[f.key] = f.value
                continue

            if not f.value:
                continue

            if not fields[f.key]:
                fields[f.key] = f.value
            elif fields[f.key] == f.value:
                continue
            else:
                duplicated_keys.append(f.key)

        if duplicated_keys:
            raise DuplicatedKeyError(duplicated_keys)

        return Wiki(
            type=self.type,
            fields=tuple(Field(key=key, value=value) for key, value in fields.items()),
            _eol=self._eol,
        )

    def __str__(self) -> str:
        return render(self)

    def render(self) -> str:
        return render(self)


class DuplicatedKeyError(Exception):
    def __init__(self, keys: list[str]):
        super().__init__(f"found duplicated keys {repr(sorted(keys))!r}")
        self.keys = keys


class WikiSyntaxError(Exception):
    lino: int | None
    line: str | None
    message: str

    def __init__(
        self, lino: int | None = None, line: str | None = None, message: str = ""
    ):
        if lino is not None:
            super().__init__(f"{lino}: {message}")
        else:
            super().__init__(message)

        self.line = line
        self.lino = lino
        self.message = message


class GlobalPrefixError(WikiSyntaxError):
    def __init__(self) -> None:
        super().__init__(message="missing prefix '{{Infobox' at the start")


class GlobalSuffixError(WikiSyntaxError):
    def __init__(self) -> None:
        super().__init__(message="missing '}}' at the end")


class ArrayNoCloseError(WikiSyntaxError):
    def __init__(
        self,
        lino: int | None = None,
        line: str | None = None,
        message: str = "array not close",
    ):
        super().__init__(lino, line, message)


class InvalidArrayItemError(WikiSyntaxError):
    def __init__(
        self,
        lino: int | None = None,
        line: str | None = None,
        message: str = "invalid array item",
    ):
        super().__init__(lino, line, message)


class ExpectingNewFieldError(WikiSyntaxError):
    def __init__(
        self,
        lino: int | None = None,
        line: str | None = None,
        message: str = "missing '|' at the beginning of line",
    ):
        super().__init__(lino, line, message)


class ExpectingSignEqualError(WikiSyntaxError):
    def __init__(
        self,
        lino: int | None = None,
        line: str | None = None,
        message: str = "missing '=' in line",
    ):
        super().__init__(lino, line, message)


def try_parse(s: str) -> Wiki:
    """If failed to parse, return zero value"""
    try:
        return parse(s)
    except WikiSyntaxError:
        pass
    return Wiki()


prefix = "{{Infobox"
suffix = "}}"


def parse(s: str) -> Wiki:
    crlf = s.count("\r\n")
    lf = s.count("\n") - crlf
    if crlf >= lf:
        eol = "\r\n"
    else:
        eol = "\n"

    s = s.replace("\r\n", "\n")
    s, line_offset = _process_input(s)
    if not s:
        return Wiki()

    if not s.startswith(prefix):
        raise GlobalPrefixError

    if not s.endswith(suffix):
        raise GlobalSuffixError

    wiki_type = read_type(s)

    eol_count = s.count("\n")
    if eol_count <= 1:
        return Wiki(type=wiki_type, _eol=eol)

    item_container: list[Item] = []

    # loop state
    in_array: bool = False
    current_key: str = ""

    fields = []

    for lino, line in enumerate(s.splitlines()[1:-1]):
        lino += line_offset

        # now handle line content
        line = _trim_space(line)
        if not line:
            continue

        if line[0] == "|":
            # new field
            if in_array:
                raise ArrayNoCloseError(lino, line)

            current_key = ""

            key, value = read_start_line(line, lino)  # read "key = value"

            if not value:
                fields.append(Field(key=key))
                continue
            if value == "{":
                in_array = True
                current_key = key
                continue

            fields.append(Field(key=key, value=value))
            continue

        if not in_array:
            raise ExpectingNewFieldError(lino, line)

        if line == "}":  # close array
            in_array = False
            fields.append(Field(key=current_key, value=tuple(item_container)))
            item_container = []
            continue

        # array item
        key, value = read_array_item(line, lino)
        item_container.append(Item(key=key, value=value))

    if in_array:
        # array should be close have read all contents
        raise ArrayNoCloseError(s.count("\n") + line_offset, s.splitlines()[-2])

    return Wiki(type=wiki_type, fields=tuple(fields), _eol=eol)


def read_type(s: str) -> str:
    try:
        i = s.index("\n")
    except ValueError:
        i = s.index("}")  # {{Infobox Crt}}

    return _trim_space(s[len(prefix) : i])


def read_array_item(line: str, lino: int) -> tuple[str, str]:
    """Read whole line as an array item, spaces are trimmed.

    read_array_item("[简体中文名|鲁鲁修]") => "简体中文名", "鲁鲁修"
    read_array_item("[简体中文名|]") => "简体中文名", ""
    read_array_item("[鲁鲁修]") => "", "鲁鲁修"

    Raises:
        InvalidArrayItemError: syntax error
    """
    if line[0] != "[" or line[len(line) - 1] != "]":
        raise InvalidArrayItemError(lino, line)

    content = line[1 : len(line) - 1]

    try:
        i = content.index("|")
        return _trim_space(content[:i]), _trim_space(content[i + 1 :])
    except ValueError:
        return "", _trim_space(content)


def read_start_line(line: str, lino: int) -> tuple[str, str]:
    """Read line without leading '|' as key value pair, spaces are trimmed.

    read_start_line("播放日期 = 2017年4月16日") => 播放日期, 2017年4月16日
    read_start_line("播放日期 = ") => 播放日期, ""

    Raises:
        ExpectingSignEqualError: syntax error
    """
    s = _trim_left_space(line[1:])
    try:
        i = s.index("=")
    except ValueError:
        raise ExpectingSignEqualError(lino, line) from None

    return s[:i].strip(), s[i + 1 :].strip()


_space_str = " \t"


def _trim_space(s: str) -> str:
    return s.strip()


def _trim_left_space(s: str) -> str:
    return s.strip()


def _trim_right_space(s: str) -> str:
    return s.strip()


def _process_input(s: str) -> tuple[str, int]:
    offset = 1
    s = "\n".join(s.splitlines())

    for c in s:
        if c == "\n":
            offset += 1
        elif c == " " or c == "\t":
            continue
        else:
            return s.strip(), offset

    return s.strip(), offset


def render(w: Wiki) -> str:
    return w._eol.join(__render(w))


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
