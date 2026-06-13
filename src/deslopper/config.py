"""Config discovery, loading, and resolution (v0.1: single built-in base)."""

import json
import os
from dataclasses import dataclass

from .discovery import find_config
from .errors import ConfigError
from .presets import load_builtin
from .rules import compile_tell

DEFAULT_INCLUDE = ["**/*.md", "**/*.markdown"]
BUILTIN_EXCLUDE = ["**/node_modules/**", "**/.git/**", "**/vendor/**", "**/reference/**"]
DEFAULT_EXCLUDE = list(BUILTIN_EXCLUDE)
ALWAYS_EXCLUDE = ["**/node_modules/**", "**/.git/**"]
CONFIG_NAME = "deslopper.config.json"
RECOMMENDED = "deslopper:recommended"


@dataclass
class ResolvedConfig:
    tells: list
    strict: bool
    include: list
    exclude: list
    rewrite_ruleset: object  # str | None


def _parse_key(token: str):
    if "@" in token:
        name, phase = token.split("@", 1)
        return (name, phase)
    return (token, None)


def _match_indices(raw_tells, token):
    name, phase = _parse_key(token)
    out = []
    for i, t in enumerate(raw_tells):
        t_phase = t.get("phase", "post-entity")
        if t["name"] == name and (phase is None or t_phase == phase):
            out.append(i)
    return out


def _resolve_target(raw_tells, token, op):
    idx = _match_indices(raw_tells, token)
    if not idx:
        raise ConfigError(f"{op} target {token!r} matches no tell")
    if len(idx) > 1:
        raise ConfigError(
            f"{op} target {token!r} is ambiguous; qualify it as name@phase"
        )
    return idx[0]


def _resolve_raw_tells(config: dict) -> list:
    extends = config.get("extends", [RECOMMENDED])
    if not isinstance(extends, list):
        raise ConfigError("`extends` must be an array")
    if config.get("plugins"):
        raise ConfigError("`plugins` are not available in this version")

    # Resolve each built-in preset left to right, merging by (name, phase) so a later
    # preset replaces an inherited tell in place. Third-party (pip) presets are v0.3.
    raw = []
    for ref in extends:
        if not isinstance(ref, str) or not ref.startswith("deslopper:"):
            raise ConfigError(
                f"extends {ref!r} must be a built-in preset like {RECOMMENDED!r}; "
                "third-party presets are not available in this version"
            )
        for tell in load_builtin(ref[len("deslopper:"):])["tells"]:
            key = f"{tell['name']}@{tell.get('phase', 'post-entity')}"
            idx = _match_indices(raw, key)
            if idx:
                raw[idx[0]] = tell
            else:
                raw.append(tell)

    tells = config.get("tells", {})
    for add in tells.get("add", []):
        idx = _match_indices(raw, f"{add['name']}@{add.get('phase', 'post-entity')}")
        if idx:
            raw[idx[0]] = add
        else:
            raw.append(add)
    for token, patch in tells.get("override", {}).items():
        raw[_resolve_target(raw, token, "override")].update(patch)
    for token in tells.get("disable", []):
        del raw[_resolve_target(raw, token, "disable")]
    return raw


def resolve(config: dict) -> ResolvedConfig:
    raw = _resolve_raw_tells(config)
    compiled = [compile_tell(t) for t in raw]
    files = config.get("files", {})
    include = files.get("include", DEFAULT_INCLUDE)
    user_exclude = files.get("exclude", BUILTIN_EXCLUDE if "files" not in config else [])
    exclude = list(dict.fromkeys(user_exclude + BUILTIN_EXCLUDE))
    rewrite = config.get("rewrite", {})
    return ResolvedConfig(
        tells=compiled,
        strict=bool(config.get("strict", False)),
        include=include,
        exclude=exclude,
        rewrite_ruleset=rewrite.get("ruleset"),
    )


def load_config(config_path, start_dir: str):
    path = config_path or find_config(start_dir)
    if not path:
        return resolve({}), ""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read config {path}: {exc}") from exc
    return resolve(data), path
