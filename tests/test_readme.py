import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _renderer():
    path = os.path.join(ROOT, "scripts", "readme_tells.py")
    spec = importlib.util.spec_from_file_location("readme_tells", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_readme_tell_table_matches_recommended_preset():
    # The README's tell table is a golden pinned to the shipped preset. When a
    # tell changes, regenerate with: python scripts/readme_tells.py
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        readme = fh.read()
    assert _renderer().render_block() in readme
