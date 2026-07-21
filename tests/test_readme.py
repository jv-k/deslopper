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


def test_tell_table_shape():
    block = _renderer().render_block()
    assert "❌ error" in block and "⚠️ warn" in block   # legend above the table
    assert "| Tell | Tier | Example | Message |" in block
    assert "Phase" not in block
    assert " error " not in block.split("| --- |")[-1]  # tiers render as emoji rows


def test_every_example_fires_exactly_its_tell(tmp_path):
    from deslopper.config import resolve
    from deslopper.engine import lint_files

    examples = _renderer().EXAMPLES
    tells = resolve({}).tells
    assert set(examples) == {t.name for t in tells}, "one example per tell"
    for name, example in examples.items():
        p = tmp_path / "doc.md"
        p.write_text(example + "\n", encoding="utf-8")
        found = {f.name for f in lint_files([("doc.md", str(p))], tells).findings}
        assert name in found, f"example for {name!r} does not fire it: {example!r}"
