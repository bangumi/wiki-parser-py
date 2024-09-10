from pathlib import Path
from typing import Any

import pytest
import yaml
from bgm_tv_wiki import DuplicatedKeyError, Wiki, WikiSyntaxError, parse


spec_repo_path = Path(__file__, "../wiki-syntax-spec").resolve()


def as_dict(w: Wiki) -> dict[str, Any]:
    data = []
    for f in w.fields:
        if isinstance(f.value, list):
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
    parse(
        """
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
"""
    )


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


def test_duplicated_keys() -> None:
    with pytest.raises(DuplicatedKeyError) as e:
        parse(
            "\n".join(
                [
                    "{{Infobox animanga/Manga",
                    "|原作= 太田顕喜",
                    "|作画= むにゅう",
                    "|作画= むにゅ1",
                    "}}",
                ]
            )
        ).remove_duplicated_fields()

    assert e.value.keys == ["作画"]

    parse(
        "\n".join(
            [
                "{{Infobox animanga/Manga",
                "|原作= 太田顕喜",
                "|作画= むにゅう",
                "}}",
            ]
        )
    ).remove_duplicated_fields()

    parse(
        "\n".join(
            [
                "{{Infobox Album",
                "|版本特性= BLドラマCD",
                "|发售日期= 2016-03-26",
                "|价格= ￥ 3,240",
                "|艺术家= 小林裕介 / 佐藤拓也 / 高橋広樹 / 小堀幸 / 大隈健太 / 長野伸二",
                "|发行商= CROWN WORKS",
                "|原作= 安西リカ",
                "|播放时长= 78分11秒",
                "|录音= デルファイサウンド",
                "|碟片数量= 1",
                "|发行商= CROWN WORKS",
                "}}",
            ]
        )
    ).remove_duplicated_fields()


def test_equal():
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
