import os
import subprocess

from deslopper.discovery import discovery_root, discover_files, resolve_inputs
from deslopper.config import DEFAULT_INCLUDE, BUILTIN_EXCLUDE


def make_files(root, rels):
    for rel in rels:
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("x\n")


def test_discovery_root_prefers_config_dir(tmp_path):
    cfg = tmp_path / "sub" / "deslopper.config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("{}", encoding="utf-8")
    assert discovery_root(str(cfg), str(tmp_path)) == str(cfg.parent)


def test_discover_files_filesystem_walk_filters_excludes(tmp_path):
    make_files(str(tmp_path), ["a.md", "docs/b.markdown", "node_modules/c.md", "vendor/d.md", "e.txt"])
    found = discover_files(str(tmp_path), DEFAULT_INCLUDE, BUILTIN_EXCLUDE)
    assert sorted(found) == ["a.md", "docs/b.markdown"]


def test_discover_files_uses_git_when_present(tmp_path):
    make_files(str(tmp_path), ["a.md", "untracked.md"])
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "add", "a.md"], cwd=str(tmp_path), check=True)
    found = discover_files(str(tmp_path), DEFAULT_INCLUDE, BUILTIN_EXCLUDE)
    assert found == ["a.md"]   # untracked.md is not tracked


def test_resolve_inputs_explicit_paths(tmp_path):
    make_files(str(tmp_path), ["a.md", "b.md"])
    items = resolve_inputs(["a.md"], str(tmp_path), DEFAULT_INCLUDE, BUILTIN_EXCLUDE)
    assert items == [("a.md", os.path.join(str(tmp_path), "a.md"))]


def test_discover_files_includes_mdx(tmp_path):
    make_files(str(tmp_path), ["a.md", "b.mdx", "docs/c.mdx", "d.txt"])
    found = discover_files(str(tmp_path), DEFAULT_INCLUDE, BUILTIN_EXCLUDE)
    assert sorted(found) == ["a.md", "b.mdx", "docs/c.mdx"]
