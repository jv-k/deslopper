import os
import subprocess

from deslopper.discovery import discovery_root, discover_files, resolve_inputs, resolve_worklist
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


# resolve_worklist owns the discovery root, so callers never handle it. These pin the
# composition (root computation + input resolution) that used to live inline in the CLI,
# including the case the old test never reached: start_dir is not the root.

def test_resolve_worklist_roots_at_config_dir_not_start_dir(tmp_path):
    proj = tmp_path / "proj"
    (proj / "docs").mkdir(parents=True)
    cfg = proj / "deslopper.config.json"
    cfg.write_text("{}", encoding="utf-8")
    make_files(str(proj), ["a.md", "docs/b.md"])
    # start_dir is the parent; the config pins the root to proj/
    items = resolve_worklist([], str(cfg), str(tmp_path), DEFAULT_INCLUDE, BUILTIN_EXCLUDE)
    assert sorted(rel for rel, _ in items) == ["a.md", "docs/b.md"]
    assert all(read.startswith(str(proj)) for _, read in items)


def test_resolve_worklist_explicit_paths_join_the_root(tmp_path):
    # Current behavior: an explicit relative path is resolved against the root, and
    # include/exclude are not applied to it.
    cfg = tmp_path / "deslopper.config.json"
    cfg.write_text("{}", encoding="utf-8")
    make_files(str(tmp_path), ["a.md"])
    items = resolve_worklist(["a.md"], str(cfg), str(tmp_path), DEFAULT_INCLUDE, BUILTIN_EXCLUDE)
    assert items == [("a.md", os.path.join(str(tmp_path), "a.md"))]
