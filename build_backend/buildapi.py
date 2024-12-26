"""
Build backend to build a meson-project when needed
"""

import os
import sys

if (os.environ.get("WIKI_PARSER_CYTHON") == "1") and (sys.implementation.name == "cpython"):
    from mesonpy import *  # noqa: F403
else:
    from flit_core.buildapi import *  # noqa: F403
