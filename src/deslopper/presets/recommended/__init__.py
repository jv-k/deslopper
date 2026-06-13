"""The bundled `recommended` preset: the carried-over de-slop tells."""

import json
from importlib import resources


def load() -> dict:
    """Return the preset config fragment: {"tells": [...]}, in file order."""
    text = resources.files(__package__).joinpath("tells.json").read_text(encoding="utf-8")
    data = json.loads(text)
    return {"tells": data["tells"]}
