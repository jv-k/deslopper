"""Self-update: find the tool that installed deslopper and run its upgrade.

deslopper never replaces its own files. Each install tool leaves a marker in or beside
the environment it built, and the tool that wrote the marker does the upgrade. An
install with no marker gets the command to run by hand.
"""

import json
import os
import shlex
import shutil
import subprocess
import sys
from importlib import metadata
from typing import NamedTuple, Optional, Tuple

from . import ui
from .errors import UsageError

REPO = "git+https://github.com/jv-k/deslopper"


class Install(NamedTuple):
    method: str
    command: Optional[Tuple[str, ...]]
    hint: str = ""


def _direct_url():
    """The PEP 610 record of where the package came from, or None."""
    try:
        text = metadata.distribution("deslopper").read_text("direct_url.json")
    except metadata.PackageNotFoundError:
        return None
    try:
        return json.loads(text) if text else None
    except ValueError:
        return None


def detect(prefix, direct_url) -> Install:
    """The install that owns the environment at `prefix`."""
    if direct_url and direct_url.get("dir_info", {}).get("editable"):
        source = direct_url.get("url", "").replace("file://", "", 1)
        return Install("source checkout", None,
                       f"This is an editable install from {source}. Run git pull there.")
    # Homebrew builds the venv as <keg>/libexec and writes its receipt in the keg.
    if os.path.exists(os.path.join(os.path.dirname(prefix), "INSTALL_RECEIPT.json")):
        return Install("Homebrew", ("brew", "upgrade", "jv-k/tap/deslopper"))
    if os.path.exists(os.path.join(prefix, "pipx_metadata.json")):
        return Install("pipx", ("pipx", "upgrade", "deslopper"))
    if os.path.exists(os.path.join(prefix, "uv-receipt.toml")):
        return Install("uv", ("uv", "tool", "upgrade", "deslopper"))
    if os.sep + "uv" + os.sep in prefix and "archive-v" in prefix:
        return Install("uvx", None,
                       f"uvx runs a cached build. Add --refresh: "
                       f"uvx --refresh --from {REPO} deslopper")
    return Install("pip", None,
                   f"Run: {shlex.quote(sys.executable)} -m pip install --upgrade {REPO}")


def run(dry_run=False) -> int:
    install = detect(sys.prefix, _direct_url())
    if install.command is None:
        ui.log_info(install.hint)
        return 0
    shown = shlex.join(install.command)
    if dry_run:
        ui.log_info(f"{install.method} installed deslopper. Would run: {shown}")
        return 0
    ui.log_info(f"{install.method} installed deslopper. Running: {shown}")
    if shutil.which(install.command[0]) is None:
        raise UsageError(f"{install.command[0]} is not on PATH, so run {shown} by hand")
    if subprocess.call(install.command) != 0:
        ui.log_error(f"{shown} failed")
        return 1
    ui.log_success("updated. Run deslopper --version to see the version")
    return 0
