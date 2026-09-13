"""pdm-backend build hook.

pdm-backend only packages the sources. When ``BGM_TV_WIKI_NATIVE=1`` the
``ast`` extension is compiled by meson (see meson.build); otherwise nothing is
compiled and pdm-backend emits a pure-Python wheel.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sysconfig

from pdm.backend.hooks.base import Context
from pdm.backend.structures import FileMap


def _native_build() -> bool:
    return os.environ.get("BGM_TV_WIKI_NATIVE") == "1"


def pdm_build_initialize(context: Context) -> None:
    context.builder.config.build_config["is-purelib"] = not _native_build()


def pdm_build_update_files(context: Context, files: FileMap) -> None:
    if context.target != "wheel" or not _native_build():
        return

    # meson writes a whole build tree, which pdm-backend would pick up as
    # package data, so keep only the extension module it produced.
    meson_dir = context.build_dir / "meson"
    meson_dir.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["meson", "setup", str(meson_dir), str(context.root)])
    subprocess.check_call(["meson", "compile", "-C", str(meson_dir)])

    extension = f"ast{sysconfig.get_config_var('EXT_SUFFIX')}"
    package_dir = context.build_dir / "bgm_tv_wiki"
    package_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(meson_dir / extension, package_dir / extension)
    shutil.rmtree(meson_dir)
