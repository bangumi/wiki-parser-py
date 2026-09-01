from __future__ import annotations

import dataclasses

prefix = "{{Infobox"
suffix = "}}"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Span:
    start: int
    end: int


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Node:
    span: Span
    text: str

    def __str__(self) -> str:
        return self._tree(0)

    def _tree(self, indent: int) -> str:
        pad = "  " * indent
        header = f"{type(self).__name__}({', '.join(self._repr_fields())})"
        lines = [pad + header]
        for child in getattr(self, "children", ()):
            lines.append(child._tree(indent + 1))
        return "\n".join(lines)

    def _repr_fields(self) -> list[str]:
        parts = [f"span={self.span}"]
        text = self.text
        shown = text[:20]
        parts.append(f"text={shown!r}" + ("..." if len(text) > 20 else ""))
        for field in dataclasses.fields(self):
            if field.name in ("span", "text", "children"):
                continue
            value = getattr(self, field.name)
            if field.name == "value":
                if value is None:
                    parts.append("value=None")
                elif isinstance(value, str):
                    parts.append(f"value={value!r}")
                elif isinstance(value, ArrayValueNode):
                    parts.append(f"value=ArrayValueNode({len(value.items)} items)")
                else:
                    parts.append(f"value=ScalarValueNode({value.value!r})")
            elif isinstance(value, tuple):
                parts.append(f"{field.name}=({len(value)})")
            else:
                parts.append(f"{field.name}={value!r}")
        return parts


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WikiNode(Node):
    """Root node, text holds the whole input."""

    children: tuple[Node, ...] = ()
    type: str | None = None
    fields: tuple[FieldNode, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PrefixNode(Node):
    """The ``{{Infobox`` prefix."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TypeNode(Node):
    name: str = ""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class EolNode(Node):
    """A single newline, ``text`` keeps the original form (``\\n`` or ``\\r\\n``)."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class FieldNode(Node):
    key: str = ""
    key_span: Span = dataclasses.field(default_factory=lambda: Span(start=0, end=0))
    value: ScalarValueNode | ArrayValueNode | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ScalarValueNode(Node):
    value: str = ""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ArrayValueNode(Node):
    children: tuple[Node, ...] = ()
    items: tuple[ArrayItemNode, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ArrayItemNode(Node):
    name: str = ""
    value: str = ""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SuffixNode(Node):
    """The trailing ``}}``."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class LeadingNode(Node):
    """Whitespace before the prefix."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TrailingNode(Node):
    """Whitespace after the suffix line's eol."""


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


def unparse(node: WikiNode) -> str:
    return node.text


def ast_to_text(node: WikiNode) -> str:
    """Render the AST back to text from its structure.

    Unlike `unparse` (which returns the exact original text), this rebuilds
    from node structure in a normalized format, so edits to nodes are reflected.
    """
    return "".join(_render_node(child) for child in node.children)


def _render_node(node: Node) -> str:
    if isinstance(node, FieldNode):
        return _render_field(node)
    return node.text


def _render_field(field: FieldNode) -> str:
    if isinstance(field.value, ArrayValueNode):
        lines = [f"|{field.key}={{"]
        lines.extend(_render_item(item) for item in field.value.items)
        lines.append("}")
        return "\n".join(lines)
    if field.value is None:
        return f"|{field.key}="
    return f"|{field.key}= {field.value.value}"


def _render_item(item: ArrayItemNode) -> str:
    if item.name:
        return f"[{item.name}|{item.value}]"
    return f"[{item.value}]"


def parse_ast(s: str) -> WikiNode:
    start = 0
    line_offset = 1
    while start < len(s):
        c = s[start]
        if c == "\n":
            line_offset += 1
            start += 1
        elif c == "\r" and start + 1 < len(s) and s[start + 1] == "\n":
            line_offset += 1
            start += 2
        elif c in " \t":
            start += 1
        else:
            break

    if start == len(s):
        return WikiNode(span=Span(start=0, end=len(s)), text=s)

    if not s.startswith(prefix, start):
        raise GlobalPrefixError

    stripped_end = len(s.rstrip())
    if stripped_end < 2 or not s.startswith(suffix, stripped_end - 2):
        raise GlobalSuffixError

    lines = _split_lines(s, start, stripped_end)

    n = len(lines)
    first_text, first_start, first_end, first_eol = lines[0]

    prefix_span = Span(start=first_start, end=first_start + len(prefix))
    prefix_node = PrefixNode(span=prefix_span, text=prefix)

    if first_text.endswith(suffix):
        type_raw = first_text[len(prefix) : -len(suffix)]
    else:
        type_raw = first_text[len(prefix) :]
    type_name = type_raw.strip()
    type_node = TypeNode(
        span=Span(
            start=first_start + len(prefix),
            end=first_start + len(prefix) + len(type_raw),
        ),
        text=type_raw,
        name=type_name,
    )

    children: list[Node] = [prefix_node, type_node]
    fields: list[FieldNode] = []

    if n == 1:
        suffix_node = SuffixNode(
            span=Span(start=first_end - 2, end=first_end), text=suffix
        )
        children.append(suffix_node)
    else:
        if first_eol is not None:
            children.append(_eol(s, first_end, first_eol))

        in_array = False
        array_key = ""
        array_key_span = Span(start=0, end=0)
        array_value_start = 0
        array_field_start = 0
        array_items: list[ArrayItemNode] = []
        array_children: list[Node] = []

        for idx in range(1, n - 1):
            line_text, line_start, line_end, line_eol = lines[idx]
            lino = line_offset + idx

            stripped_line = line_text.strip()
            if not stripped_line:
                if line_eol is not None:
                    eol_node = _eol(s, line_end, line_eol)
                    (array_children if in_array else children).append(eol_node)
                continue

            lstrip_len = len(line_text) - len(line_text.lstrip())

            if stripped_line[0] == "|":
                if in_array:
                    raise ArrayNoCloseError(lino, stripped_line)

                eq = line_text.find("=", lstrip_len + 1)
                if eq == -1:
                    raise ExpectingSignEqualError(lino, stripped_line)

                key_raw = line_text[lstrip_len + 1 : eq]
                key = key_raw.strip()
                key_span = _trim_span(key_raw, line_start + lstrip_len + 1)

                value_raw = line_text[eq + 1 : line_end]
                value = value_raw.strip()

                if value == "{":
                    in_array = True
                    array_key = key
                    array_key_span = key_span
                    array_value_start = _trim_span(value_raw, line_start + eq + 1).start
                    array_field_start = line_start
                    array_items = []
                    array_children = []
                    if line_eol is not None:
                        array_children.append(_eol(s, line_end, line_eol))
                    continue

                field_node = FieldNode(
                    span=Span(start=line_start, end=line_end),
                    text=line_text,
                    key=key,
                    key_span=key_span,
                    value=ScalarValueNode(
                        span=_trim_span(value_raw, line_start + eq + 1),
                        text=value,
                        value=value,
                    ),
                )
                fields.append(field_node)
                children.append(field_node)
                if line_eol is not None:
                    children.append(_eol(s, line_end, line_eol))
                continue

            if not in_array:
                raise ExpectingNewFieldError(lino, stripped_line)

            if stripped_line == "}":
                in_array = False
                rbrace_start = line_start + lstrip_len
                value_node = ArrayValueNode(
                    span=Span(start=array_value_start, end=rbrace_start + 1),
                    text=s[array_value_start : rbrace_start + 1],
                    children=tuple(array_children),
                    items=tuple(array_items),
                )
                field_node = FieldNode(
                    span=Span(start=array_field_start, end=line_end),
                    text=s[array_field_start:line_end],
                    key=array_key,
                    key_span=array_key_span,
                    value=value_node,
                )
                fields.append(field_node)
                children.append(field_node)
                if line_eol is not None:
                    children.append(_eol(s, line_end, line_eol))
                continue

            if stripped_line[0] != "[" or stripped_line[-1] != "]":
                raise InvalidArrayItemError(lino, stripped_line)

            inner = stripped_line[1:-1]
            name_raw, sep, item_value_raw = inner.partition("|")
            if sep:
                name = name_raw.strip()
                item_value = item_value_raw.strip()
            else:
                name = ""
                item_value = inner.strip()

            item_node = ArrayItemNode(
                span=Span(start=line_start, end=line_end),
                text=line_text,
                name=name,
                value=item_value,
            )
            array_items.append(item_node)
            array_children.append(item_node)
            if line_eol is not None:
                array_children.append(_eol(s, line_end, line_eol))

        if in_array:
            raise ArrayNoCloseError(n - 1 + line_offset, lines[-2][0])

        suffix_line_text, suffix_line_start, suffix_line_end, _ = lines[-1]
        suffix_node = SuffixNode(
            span=Span(start=suffix_line_start, end=suffix_line_end),
            text=suffix_line_text,
        )
        children.append(suffix_node)

    after = stripped_end
    if s.startswith("\r\n", after):
        children.append(_eol(s, after, "\r\n"))
        after += 2
    elif after < len(s) and s[after] == "\n":
        children.append(_eol(s, after, "\n"))
        after += 1

    if after < len(s):
        children.append(
            TrailingNode(span=Span(start=after, end=len(s)), text=s[after:])
        )

    if start > 0:
        children.insert(0, LeadingNode(span=Span(start=0, end=start), text=s[:start]))

    return WikiNode(
        span=Span(start=0, end=len(s)),
        text=s,
        children=tuple(children),
        type=type_name,
        fields=tuple(fields),
    )


def _trim_span(text: str, base: int) -> Span:
    stripped = text.strip()
    if not stripped:
        return Span(start=base, end=base)
    start = base + text.find(stripped)
    return Span(start=start, end=start + len(stripped))


def _eol(s: str, offset: int, text: str) -> EolNode:
    return EolNode(span=Span(start=offset, end=offset + len(text)), text=text)


def _split_lines(
    s: str, start: int, end: int
) -> list[tuple[str, int, int, str | None]]:
    lines: list[tuple[str, int, int, str | None]] = []
    pos = start
    while pos < end:
        nl = s.find("\n", pos, end)
        if nl == -1:
            lines.append((s[pos:end], pos, end, None))
            break
        if nl > pos and s[nl - 1] == "\r":
            lines.append((s[pos : nl - 1], pos, nl - 1, "\r\n"))
        else:
            lines.append((s[pos:nl], pos, nl, "\n"))
        pos = nl + 1
    return lines
