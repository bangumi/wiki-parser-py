import os

from setuptools import setup

ext_modules = []
if os.environ.get("BGM_TV_WIKI_MYPYC") == "1":
    from mypyc.build import mypycify

    ext_modules = mypycify(["src/bgm_tv_wiki/ast.py"])

setup(ext_modules=ext_modules)
