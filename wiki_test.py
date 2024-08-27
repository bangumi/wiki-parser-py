from pathlib import Path
from typing import Any

import pytest
import yaml

from bgm_tv_wiki import Wiki, parse

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
