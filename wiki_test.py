from pathlib import Path
from typing import Any

import pytest
import yaml

from bgm_tv_wiki import Field, Wiki, WikiSyntaxError, parse
from src.bgm_tv_wiki import render

spec_repo_path = Path(__file__, "../wiki-syntax-spec").resolve()


def as_dict(w: Wiki) -> dict[str, Any]:
    data: list[Any] = []
    for f in w.fields:
        if isinstance(f.value, tuple):
            data.append(
                {
                    "key": f.key,
                    "array": True,
                    "values": [
                        {"v": v.value} | ({"k": v.key} if v.key else {})
                        for v in f.value
                    ],
                },
            )
        else:
            data.append({"key": f.key, "value": f.value or ""})

    return {"type": w.type, "data": data}


valid = [
    file.name
    for file in spec_repo_path.joinpath("tests/valid").iterdir()
    if file.name.endswith(".wiki")
]


@pytest.mark.parametrize("name", valid)
def test_bangumi_wiki(name: str) -> None:
    file = spec_repo_path.joinpath("tests/valid", name)
    wiki_raw = file.read_text()
    assert as_dict(parse(wiki_raw)) == yaml.safe_load(
        file.with_suffix(".yaml").read_text()
    ), name


invalid = [
    file.name
    for file in spec_repo_path.joinpath("tests/invalid").iterdir()
    if file.name.endswith(".wiki")
]


@pytest.mark.parametrize("name", invalid)
def test_bangumi_wiki_invalid(name: str) -> None:
    file = spec_repo_path.joinpath("tests/invalid", name)
    wiki_raw = file.read_text()
    with pytest.raises(WikiSyntaxError):
        parse(wiki_raw)


def test_cast() -> None:
    parse("""
{{Infobox Crt
|简体中文名= 绵饴
|别名={
[第二中文名|]
[英文名|]
[日文名|]
[纯假名|]
[罗马字|]
[昵称|季節P]
}
|性别= 男
|生日=
|血型=
|身高=
|体重=
|BWH=
|引用来源= ニコニコ大百科
}}
""")


def test_field_semantically_equal() -> None:
    assert not Field(key="a").semantically_equal(Field(key="b"))

    assert Field(key="a", value=None).semantically_equal(Field(key="a", value=""))

    assert not Field(key="a", value=None).semantically_equal(Field(key="a", value=()))
    assert not Field(key="a", value="").semantically_equal(Field(key="a", value=()))


def test_index_of() -> None:
    w = parse(
        "\n".join(
            [
                "{{Infobox animanga/Manga",
                "|a= 9784061822337",
                "|b= 4061822330",
                "}}",
            ]
        )
    )

    assert w.index_of("a") == 0
    assert w.index_of("b") == 1
    assert w.index_of("c") == 2


def test_set_at() -> None:
    w = parse(
        "\n".join(
            [
                "{{Infobox animanga/Manga",
                "|a= 9784061822337",
                "|b= 4061822330",
                "}}",
            ]
        )
    )

    assert w.set_or_insert("a", "1", 0) == w.set("a", "1")
    assert w.set_or_insert("c", "1", 1) == parse(
        "\n".join(
            [
                "{{Infobox animanga/Manga",
                "|a= 9784061822337",
                "|c= 1",
                "|b= 4061822330",
                "}}",
            ]
        )
    )

    assert w.set_or_insert("c", "1", 10) == parse(
        "\n".join(
            [
                "{{Infobox animanga/Manga",
                "|a= 9784061822337",
                "|b= 4061822330",
                "|c= 1",
                "}}",
            ]
        )
    )


def test_equal() -> None:
    parse(
        "\n".join(
            [
                "{{Infobox Album",
                "|1=1",
                "|2=2",
                "|3=",
                "}}",
            ]
        )
    ).semantically_equal(
        parse(
            "\n".join(
                [
                    "{{Infobox Album",
                    "|3=",
                    "|2=2",
                    "|1=1",
                    "}}",
                ]
            )
        )
    )


def test_parse_version() -> None:
    r = parse(
        "\n".join(
            [
                "{{Infobox animanga/Novel",
                "|版本:磨铁版=",
                "|版本:泰国版=",
                "}}",
            ]
        )
    )

    assert as_dict(r) == {
        "data": [
            {
                "key": "版本:磨铁版",
                "value": "",
            },
            {
                "key": "版本:泰国版",
                "value": "",
            },
        ],
        "type": "animanga/Novel",
    }

    assert render(r) == "\n".join(
        [
            "{{Infobox animanga/Novel",
            "|版本:磨铁版= ",
            "|版本:泰国版= ",
            "}}",
        ]
    )
