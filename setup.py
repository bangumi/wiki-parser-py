from mypyc.build import mypycify
from setuptools import setup

setup(
    name="bgm_tv_wiki",
    package_dir={"": "src"},
    packages=["bgm_tv_wiki"],
    ext_modules=mypycify(
        [
            "--disallow-untyped-defs",  # mypy flag
            "src/",
        ]
    ),
)
