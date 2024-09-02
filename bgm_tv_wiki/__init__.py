from __future__ import annotations

import dataclasses
from collections.abc import Generator


__all__ = (
    "ArrayNoCloseError",
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
    value: str | list[Item] | None = None


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Wiki:
    type: str | None = None
    fields: list[Field] = dataclasses.field(default_factory=list)

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
                    fields.append(Field(key=f.key, value=v))
                continue

        return Wiki(type=self.type, fields=fields)

    def get(self, key: str) -> str | list[Item] | None:
        for f in self.fields:
            if f.key == key:
                return f.value
        return None

    def get_str(self, key: str) -> str:
        for f in self.fields:
            if f.key == key:
                if isinstance(f.value, str):
                    return f.value
                raise ValueError(f"value of {key!r} is {type(f.value)}, not str")

        return ""

    def set(self, key: str, value: str | list[Item] | None = None) -> Wiki:
        return self.__set(field=Field(key=key, value=value))

    def set_values(self, values: dict[str, str | list[Item] | None]) -> Wiki:
        w = self
        for key, value in values.items():
            w = w.__set(field=Field(key=key, value=value))
        return w

    def __set(self, field: Field) -> Wiki:
        fields = []
        for f in self.fields:
            if f.key == field.key:
                fields.append(field)
            else:
                fields.append(f)

        return Wiki(type=self.type, fields=fields)

    def remove(self, key: str) -> Wiki:
        fields = [f for f in self.fields if f.key != key]
        return Wiki(type=self.type, fields=fields)

    def semantics_equal(self, other: Wiki) -> bool:
        if self.type != other.type:
            return False
        return {f.key: f.value for f in self.fields} == {
            f.key: f.value for f in other.fields
        }


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
        message: str = "missing '=' in line",
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
    s = s.replace("\r\n", "\n")
    s, line_offset = _process_input(s)
    if not s:
        return Wiki()

    if not s.startswith(prefix):
        raise GlobalPrefixError

    if not s.endswith(suffix):
        raise GlobalSuffixError

    w = Wiki(type=read_type(s))

    eol_count = s.count("\n")
    if eol_count <= 1:
        return w

    item_container: list[Item] = []

    # loop state
    in_array: bool = False
    current_key: str = ""

    for lino, line in enumerate(s.splitlines()):
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
                w.fields.append(Field(key=key))
                continue
            if value == "{":
                in_array = True
                current_key = key
                continue

            w.fields.append(Field(key=key, value=value))
            continue

        if in_array:
            if line == "}":  # close array
                in_array = False
                w.fields.append(Field(key=current_key, value=item_container))
                item_container = []
                continue

            # array item
            key, value = read_array_item(line, lino)
            item_container.append(Item(key=key, value=value))

        # if not in_array:
        #     raise ErrExpectingNewField(lino, line)

    if in_array:
        # array should be close have read all contents
        raise ArrayNoCloseError(s.count("\n") + line_offset, s.splitlines()[-2])

    return w


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
        match c:
            case "\n":
                offset += 1
            case " ", "\t":
                continue
            case _:
                return s.strip(), offset

    return s.strip(), offset


def render(w: Wiki) -> str:
    return "\n".join(__render(w))


def __render(w: Wiki) -> Generator[str, None, None]:
    if w.type:
        yield "{{Infobox " + w.type
    else:
        yield "{{Infobox"

    for field in w.fields:
        if isinstance(field.value, str):
            yield f"|{field.key}= {field.value}"
        elif isinstance(field.value, list):
            yield f"|{field.key}= {{"
            yield from __render_items(field.value)
            yield "}"
        elif field.value is None:
            yield f"|{field.key}="
        else:
            raise TypeError("type not support", type(field.value))

    yield "}}"


def __render_items(s: list[Item]) -> Generator[str, None, None]:
    for item in s:
        if item.key:
            yield f"[{item.key}| {item.value}]"
        else:
            yield f"[{item.value}]"
