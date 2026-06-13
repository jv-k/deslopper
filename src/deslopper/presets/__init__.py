"""Built-in presets, one JSON file per preset in this directory.

A preset file is `<name>.json` with a top-level `tells` array. Add a preset by dropping a
new JSON file here, then reference it from a config as `deslopper:<name>` in `extends`.
"""

import json
from importlib import resources

from ..errors import ConfigError


def available() -> list:
    """The built-in preset names: the JSON file stems in this package."""
    names = []
    for entry in resources.files(__package__).iterdir():
        if entry.name.endswith(".json"):
            names.append(entry.name[: -len(".json")])
    return sorted(names)


def load_builtin(name: str) -> dict:
    """Return a built-in preset fragment `{"tells": [...]}` by name."""
    resource = resources.files(__package__).joinpath(f"{name}.json")
    if not resource.is_file():
        raise ConfigError(f"unknown built-in preset {name!r}")
    data = json.loads(resource.read_text(encoding="utf-8"))
    return {"tells": data["tells"]}
