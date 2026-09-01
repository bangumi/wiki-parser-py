import dataclasses

import pytest

from bgm_tv_wiki import (
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
    PrefixNode,
    ScalarValueNode,
    Span,
    SuffixNode,
    TrailingNode,
    TypeNode,
    WikiNode,
    WikiSyntaxError,
    ast_to_text,
    ast_to_wiki,
    parse,
    parse_ast,
    unparse,
)


def test_basic_structure() -> None:
    raw = "\n".join(
        [
            "{{Infobox animanga/TVAnime",
            "|中文名= 绵饴",
            "|别名={",
            "[第二中文名|]",
            "}",
            "|性别= 男",
            "}}",
        ]
    )
    field_1 = FieldNode(
        span=Span(start=27, end=35),
        text="|中文名= 绵饴",
        key="中文名",
        key_span=Span(start=28, end=31),
        value=ScalarValueNode(span=Span(start=33, end=35), text="绵饴", value="绵饴"),
    )
    item = ArrayItemNode(
        span=Span(start=42, end=50), text="[第二中文名|]", name="第二中文名", value=""
    )
    field_2 = FieldNode(
        span=Span(start=36, end=52),
        text="|别名={\n[第二中文名|]\n}",
        key="别名",
        key_span=Span(start=37, end=39),
        value=ArrayValueNode(
            span=Span(start=40, end=52),
            text="{\n[第二中文名|]\n}",
            children=(
                EolNode(span=Span(start=41, end=42), text="\n"),
                item,
                EolNode(span=Span(start=50, end=51), text="\n"),
            ),
            items=(item,),
        ),
    )
    field_3 = FieldNode(
        span=Span(start=53, end=59),
        text="|性别= 男",
        key="性别",
        key_span=Span(start=54, end=56),
        value=ScalarValueNode(span=Span(start=58, end=59), text="男", value="男"),
    )
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=62),
        text=raw,
        type="animanga/TVAnime",
        children=(
            PrefixNode(span=Span(start=0, end=9), text="{{Infobox"),
            TypeNode(
                span=Span(start=9, end=26),
                text=" animanga/TVAnime",
                name="animanga/TVAnime",
            ),
            EolNode(span=Span(start=26, end=27), text="\n"),
            field_1,
            EolNode(span=Span(start=35, end=36), text="\n"),
            field_2,
            EolNode(span=Span(start=52, end=53), text="\n"),
            field_3,
            EolNode(span=Span(start=59, end=60), text="\n"),
            SuffixNode(span=Span(start=60, end=62), text="}}"),
        ),
        fields=(field_1, field_2, field_3),
    )


def test_children_sequence() -> None:
    raw = "{{Infobox X\n|a= 1\n}}"
    field = FieldNode(
        span=Span(start=12, end=17),
        text="|a= 1",
        key="a",
        key_span=Span(start=13, end=14),
        value=ScalarValueNode(span=Span(start=16, end=17), text="1", value="1"),
    )
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=20),
        text=raw,
        type="X",
        children=(
            PrefixNode(span=Span(start=0, end=9), text="{{Infobox"),
            TypeNode(span=Span(start=9, end=11), text=" X", name="X"),
            EolNode(span=Span(start=11, end=12), text="\n"),
            field,
            EolNode(span=Span(start=17, end=18), text="\n"),
            SuffixNode(span=Span(start=18, end=20), text="}}"),
        ),
        fields=(field,),
    )


def test_type_node() -> None:
    raw = "{{Infobox animanga/TVAnime\n|a= 1\n}}"
    field = FieldNode(
        span=Span(start=27, end=32),
        text="|a= 1",
        key="a",
        key_span=Span(start=28, end=29),
        value=ScalarValueNode(span=Span(start=31, end=32), text="1", value="1"),
    )
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=35),
        text=raw,
        type="animanga/TVAnime",
        children=(
            PrefixNode(span=Span(start=0, end=9), text="{{Infobox"),
            TypeNode(
                span=Span(start=9, end=26),
                text=" animanga/TVAnime",
                name="animanga/TVAnime",
            ),
            EolNode(span=Span(start=26, end=27), text="\n"),
            field,
            EolNode(span=Span(start=32, end=33), text="\n"),
            SuffixNode(span=Span(start=33, end=35), text="}}"),
        ),
        fields=(field,),
    )

    raw = "{{Infobox X}}"
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=13),
        text=raw,
        type="X",
        children=(
            PrefixNode(span=Span(start=0, end=9), text="{{Infobox"),
            TypeNode(span=Span(start=9, end=11), text=" X", name="X"),
            SuffixNode(span=Span(start=11, end=13), text="}}"),
        ),
        fields=(),
    )

    raw = "{{Infobox\n}}"
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=12),
        text=raw,
        type="",
        children=(
            PrefixNode(span=Span(start=0, end=9), text="{{Infobox"),
            TypeNode(span=Span(start=9, end=9), text="", name=""),
            EolNode(span=Span(start=9, end=10), text="\n"),
            SuffixNode(span=Span(start=10, end=12), text="}}"),
        ),
        fields=(),
    )


def test_scalar_field_spans() -> None:
    raw = "{{Infobox\n| 中文名 = 绵饴 \n}}"
    field = FieldNode(
        span=Span(start=10, end=21),
        text="| 中文名 = 绵饴 ",
        key="中文名",
        key_span=Span(start=12, end=15),
        value=ScalarValueNode(span=Span(start=18, end=20), text="绵饴", value="绵饴"),
    )
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=24),
        text=raw,
        type="",
        children=(
            PrefixNode(span=Span(start=0, end=9), text="{{Infobox"),
            TypeNode(span=Span(start=9, end=9), text="", name=""),
            EolNode(span=Span(start=9, end=10), text="\n"),
            field,
            EolNode(span=Span(start=21, end=22), text="\n"),
            SuffixNode(span=Span(start=22, end=24), text="}}"),
        ),
        fields=(field,),
    )


def test_array_field() -> None:
    raw = "{{Infobox\n|d={\n[1]\n[a|b]\n[]\n}\n}}"
    item_1 = ArrayItemNode(span=Span(start=15, end=18), text="[1]", name="", value="1")
    item_2 = ArrayItemNode(
        span=Span(start=19, end=24), text="[a|b]", name="a", value="b"
    )
    item_3 = ArrayItemNode(span=Span(start=25, end=27), text="[]", name="", value="")
    field = FieldNode(
        span=Span(start=10, end=29),
        text="|d={\n[1]\n[a|b]\n[]\n}",
        key="d",
        key_span=Span(start=11, end=12),
        value=ArrayValueNode(
            span=Span(start=13, end=29),
            text="{\n[1]\n[a|b]\n[]\n}",
            children=(
                EolNode(span=Span(start=14, end=15), text="\n"),
                item_1,
                EolNode(span=Span(start=18, end=19), text="\n"),
                item_2,
                EolNode(span=Span(start=24, end=25), text="\n"),
                item_3,
                EolNode(span=Span(start=27, end=28), text="\n"),
            ),
            items=(item_1, item_2, item_3),
        ),
    )
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=32),
        text=raw,
        type="",
        children=(
            PrefixNode(span=Span(start=0, end=9), text="{{Infobox"),
            TypeNode(span=Span(start=9, end=9), text="", name=""),
            EolNode(span=Span(start=9, end=10), text="\n"),
            field,
            EolNode(span=Span(start=29, end=30), text="\n"),
            SuffixNode(span=Span(start=30, end=32), text="}}"),
        ),
        fields=(field,),
    )


def test_array_blank_line() -> None:
    raw = "{{Infobox\n|a={\n\n[1]\n}\n}}"
    item = ArrayItemNode(span=Span(start=16, end=19), text="[1]", name="", value="1")
    field = FieldNode(
        span=Span(start=10, end=21),
        text="|a={\n\n[1]\n}",
        key="a",
        key_span=Span(start=11, end=12),
        value=ArrayValueNode(
            span=Span(start=13, end=21),
            text="{\n\n[1]\n}",
            children=(
                EolNode(span=Span(start=14, end=15), text="\n"),
                EolNode(span=Span(start=15, end=16), text="\n"),
                item,
                EolNode(span=Span(start=19, end=20), text="\n"),
            ),
            items=(item,),
        ),
    )
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=24),
        text=raw,
        type="",
        children=(
            PrefixNode(span=Span(start=0, end=9), text="{{Infobox"),
            TypeNode(span=Span(start=9, end=9), text="", name=""),
            EolNode(span=Span(start=9, end=10), text="\n"),
            field,
            EolNode(span=Span(start=21, end=22), text="\n"),
            SuffixNode(span=Span(start=22, end=24), text="}}"),
        ),
        fields=(field,),
    )


def test_empty_value_field() -> None:
    raw = "{{Infobox\n|A=\n|b= \n}}"
    field_1 = FieldNode(
        span=Span(start=10, end=13),
        text="|A=",
        key="A",
        key_span=Span(start=11, end=12),
        value=ScalarValueNode(span=Span(start=13, end=13), text="", value=""),
    )
    field_2 = FieldNode(
        span=Span(start=14, end=18),
        text="|b= ",
        key="b",
        key_span=Span(start=15, end=16),
        value=ScalarValueNode(span=Span(start=17, end=17), text="", value=""),
    )
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=21),
        text=raw,
        type="",
        children=(
            PrefixNode(span=Span(start=0, end=9), text="{{Infobox"),
            TypeNode(span=Span(start=9, end=9), text="", name=""),
            EolNode(span=Span(start=9, end=10), text="\n"),
            field_1,
            EolNode(span=Span(start=13, end=14), text="\n"),
            field_2,
            EolNode(span=Span(start=18, end=19), text="\n"),
            SuffixNode(span=Span(start=19, end=21), text="}}"),
        ),
        fields=(field_1, field_2),
    )


def test_blank_line_between_fields() -> None:
    raw = "{{Infobox X\n\n|a= 1\n}}\n"
    field = FieldNode(
        span=Span(start=13, end=18),
        text="|a= 1",
        key="a",
        key_span=Span(start=14, end=15),
        value=ScalarValueNode(span=Span(start=17, end=18), text="1", value="1"),
    )
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=22),
        text=raw,
        type="X",
        children=(
            PrefixNode(span=Span(start=0, end=9), text="{{Infobox"),
            TypeNode(span=Span(start=9, end=11), text=" X", name="X"),
            EolNode(span=Span(start=11, end=12), text="\n"),
            EolNode(span=Span(start=12, end=13), text="\n"),
            field,
            EolNode(span=Span(start=18, end=19), text="\n"),
            SuffixNode(span=Span(start=19, end=21), text="}}"),
            EolNode(span=Span(start=21, end=22), text="\n"),
        ),
        fields=(field,),
    )


def test_leading_trailing() -> None:
    raw = "  {{Infobox X\n|a= 1\n}}\n\n"
    field = FieldNode(
        span=Span(start=14, end=19),
        text="|a= 1",
        key="a",
        key_span=Span(start=15, end=16),
        value=ScalarValueNode(span=Span(start=18, end=19), text="1", value="1"),
    )
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=24),
        text=raw,
        type="X",
        children=(
            LeadingNode(span=Span(start=0, end=2), text="  "),
            PrefixNode(span=Span(start=2, end=11), text="{{Infobox"),
            TypeNode(span=Span(start=11, end=13), text=" X", name="X"),
            EolNode(span=Span(start=13, end=14), text="\n"),
            field,
            EolNode(span=Span(start=19, end=20), text="\n"),
            SuffixNode(span=Span(start=20, end=22), text="}}"),
            EolNode(span=Span(start=22, end=23), text="\n"),
            TrailingNode(span=Span(start=23, end=24), text="\n"),
        ),
        fields=(field,),
    )


def test_eol_preserved() -> None:
    raw = "{{Infobox X\r\n|a= 1\r\n}}\r\n"
    field = FieldNode(
        span=Span(start=13, end=18),
        text="|a= 1",
        key="a",
        key_span=Span(start=14, end=15),
        value=ScalarValueNode(span=Span(start=17, end=18), text="1", value="1"),
    )
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=24),
        text=raw,
        type="X",
        children=(
            PrefixNode(span=Span(start=0, end=9), text="{{Infobox"),
            TypeNode(span=Span(start=9, end=11), text=" X", name="X"),
            EolNode(span=Span(start=11, end=13), text="\r\n"),
            field,
            EolNode(span=Span(start=18, end=20), text="\r\n"),
            SuffixNode(span=Span(start=20, end=22), text="}}"),
            EolNode(span=Span(start=22, end=24), text="\r\n"),
        ),
        fields=(field,),
    )


def test_leading_crlf() -> None:
    raw = "\r\n{{Infobox X\n|a= 1\n}}\n"
    field = FieldNode(
        span=Span(start=14, end=19),
        text="|a= 1",
        key="a",
        key_span=Span(start=15, end=16),
        value=ScalarValueNode(span=Span(start=18, end=19), text="1", value="1"),
    )
    assert parse_ast(raw) == WikiNode(
        span=Span(start=0, end=23),
        text=raw,
        type="X",
        children=(
            LeadingNode(span=Span(start=0, end=2), text="\r\n"),
            PrefixNode(span=Span(start=2, end=11), text="{{Infobox"),
            TypeNode(span=Span(start=11, end=13), text=" X", name="X"),
            EolNode(span=Span(start=13, end=14), text="\n"),
            field,
            EolNode(span=Span(start=19, end=20), text="\n"),
            SuffixNode(span=Span(start=20, end=22), text="}}"),
            EolNode(span=Span(start=22, end=23), text="\n"),
        ),
        fields=(field,),
    )


def test_children_contiguous() -> None:
    raws = [
        "{{Infobox X\n|a= 1\n}}\n",
        "  {{Infobox X\n|a= 1\n}}\n\n",
        "{{Infobox X}}",
        "{{Infobox\n|a={\n\n[1]\n}\n}}",
    ]
    for raw in raws:
        w = parse_ast(raw)
        cursor = 0
        for c in w.children:
            assert c.span.start == cursor
            cursor = c.span.end
        assert cursor == len(raw)


def test_empty_input() -> None:
    w = parse_ast("")
    assert w.type is None
    assert w.fields == ()
    assert unparse(w) == ""

    w = parse_ast("  \n ")
    assert w.type is None
    assert w.fields == ()


def test_unparse_roundtrip() -> None:
    raws = [
        "{{Infobox X\n|a= 1\n}}",
        "{{Infobox X\n|a= 1\n}}\n",
        "{{Infobox X}}",
        "{{Infobox\n}}",
        "{{Infobox\n|d={\n[1]\n[a|b]\n}\n|e= 2\n}}",
        "  {{Infobox X\r\n|a= 1\r\n}}\r\n",
    ]
    for raw in raws:
        assert unparse(parse_ast(raw)) == raw


@pytest.mark.parametrize(
    "raw",
    [
        "{{Infobox X\n|a= 1\n}}\n",
        "{{Infobox X\n|a= 1\n}}\r\n",
        "{{Infobox X\n|a= 1\n}}",
        "{{Infobox X}}",
        "{{Infobox\n|d={\n[1]\n[a|b]\n}\n}}",
    ],
)
def test_ast_to_wiki_matches_parse(raw: str) -> None:
    assert ast_to_wiki(parse_ast(raw)) == parse(raw)


def test_ast_to_text_matches_parse() -> None:
    raws = [
        "{{Infobox X\n|a= 1\n}}",
        "{{Infobox X\n|a= 1\n}}\n",
        "{{Infobox X}}",
        "{{Infobox\n}}",
        "{{Infobox\n|d={\n[1]\n[a|b]\n[]\n}\n|e= 2\n}}",
    ]
    for raw in raws:
        assert parse(ast_to_text(parse_ast(raw))) == parse(raw)


def test_ast_to_text_reflects_edit() -> None:
    w = parse_ast("{{Infobox X\n|a= 1\n|d={\n[1]\n}\n}}")

    # children 是权威结构，修改需重建 children 元组
    new_children = []
    for c in w.children:
        if isinstance(c, FieldNode) and c.key == "a":
            assert isinstance(c.value, ScalarValueNode)
            c = dataclasses.replace(
                c,
                key="a2",
                value=ScalarValueNode(span=c.value.span, text="2", value="2"),
            )
        new_children.append(c)
    new_w = dataclasses.replace(w, children=tuple(new_children))

    text = ast_to_text(new_w)
    assert text == "{{Infobox X\n|a2= 2\n|d={\n[1]\n}\n}}"
    assert parse(text).get("a2") == "2"


def test_ast_to_text_keeps_eol() -> None:
    w = parse_ast("{{Infobox X\r\n|a= 1\r\n}}\r\n")
    assert ast_to_text(w) == "{{Infobox X\r\n|a= 1\r\n}}\r\n"


def test_eol_detection() -> None:
    assert parse("{{Infobox X\r\n|a= 1\r\n}}\r\n").eol == "\r\n"
    assert parse("{{Infobox X\n|a= 1\n}}\n").eol == "\n"
    assert parse("{{Infobox X\n|a= 1\r\n}}\r\n").eol == "\r\n"


def test_str_tree() -> None:
    w = parse_ast("{{Infobox X\n|a= 1\n}}\n")
    s = str(w)
    assert "WikiNode(" in s
    assert "PrefixNode(" in s
    assert "TypeNode(" in s
    assert "FieldNode(" in s
    assert "SuffixNode(" in s
    assert "EolNode(" in s
    # 每个节点单独一行（树形缩进）
    assert s.index("WikiNode") < s.index("PrefixNode") < s.index("SuffixNode")


def test_repr_is_dataclass_format() -> None:
    w = parse_ast("{{Infobox X\n|a= 1\n}}\n")
    r = repr(w)
    assert "\n" not in r
    assert "children=(" in r  # dataclass repr 完整展开字段


@pytest.mark.parametrize(
    ("raw", "error"),
    [
        ("hello", GlobalPrefixError),
        ("\r{{Infobox X\n}}", GlobalPrefixError),
        ("{{Infobox X", GlobalSuffixError),
        ("{{Infobox\nhello\n}}", ExpectingNewFieldError),
        ("{{Infobox\n|a\n}}", ExpectingSignEqualError),
        ("{{Infobox\n|a={\n|b= 1\n}\n}}", ArrayNoCloseError),
        ("{{Infobox\n|a={\n[1]\n}}", ArrayNoCloseError),
        ("{{Infobox\n|a={\nhello\n}\n}}", InvalidArrayItemError),
    ],
)
def test_errors(raw: str, error: type[WikiSyntaxError]) -> None:
    with pytest.raises(error):
        parse_ast(raw)
    with pytest.raises(WikiSyntaxError):
        parse(raw)
