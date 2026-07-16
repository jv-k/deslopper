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


def test_discover_skips_a_tracked_file_deleted_from_the_worktree(tmp_path):
    # git ls-files lists index entries, so a tracked-but-deleted file would be handed to
    # the reader and reported unreadable, failing an otherwise-clean tree.
    make_files(str(tmp_path), ["kept.md", "gone.md"])
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "add", "kept.md", "gone.md"], cwd=str(tmp_path), check=True)
    os.remove(os.path.join(str(tmp_path), "gone.md"))
    found = discover_files(str(tmp_path), DEFAULT_INCLUDE, BUILTIN_EXCLUDE)
    assert found == ["kept.md"]


def test_resolve_inputs_explicit_paths(tmp_path):
    make_files(str(tmp_path), ["a.md", "b.md"])
    items = resolve_inputs(["a.md"], str(tmp_path), str(tmp_path), DEFAULT_INCLUDE, BUILTIN_EXCLUDE)
    assert items == [("a.md", os.path.join(str(tmp_path), "a.md"))]


def test_resolve_inputs_path_outside_root_shows_absolute_not_dotdot(tmp_path):
    # A file outside the discovery root would render as ../../x.md, which is not a usable
    # finding path (github annotations reject it). Show the absolute path instead.
    root = tmp_path / "proj"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "x.md").write_text("x\n", encoding="utf-8")
    target = str(outside / "x.md")
    (display, read) = resolve_inputs([target], str(root), str(root), DEFAULT_INCLUDE, BUILTIN_EXCLUDE)[0]
    assert not display.startswith("../")
    assert display == target.replace(os.sep, "/")
    assert read == target


def test_discover_files_includes_mdx(tmp_path):
    make_files(str(tmp_path), ["a.md", "b.mdx", "docs/c.mdx", "d.txt"])
    found = discover_files(str(tmp_path), DEFAULT_INCLUDE, BUILTIN_EXCLUDE)
    assert sorted(found) == ["a.md", "b.mdx", "docs/c.mdx"]


# Glob matching follows the ** / * conventions: * stops at a slash, ** spans zero or more
# path segments. fnmatch got both wrong.

def test_include_star_does_not_cross_a_slash(tmp_path):
    make_files(str(tmp_path), ["docs/a.md", "docs/deep/b.md"])
    found = discover_files(str(tmp_path), ["docs/*.md"], [])
    assert found == ["docs/a.md"]           # deep/b.md is one level too deep


def test_include_globstar_spans_zero_or_more_segments(tmp_path):
    make_files(str(tmp_path), ["docs/a.md", "docs/deep/b.md"])
    found = discover_files(str(tmp_path), ["docs/**/*.md"], [])
    assert sorted(found) == ["docs/a.md", "docs/deep/b.md"]   # top-level a.md included


def test_exclude_star_does_not_cross_a_slash(tmp_path):
    make_files(str(tmp_path), ["docs/index.md", "docs/guide/intro.md"])
    found = discover_files(str(tmp_path), DEFAULT_INCLUDE, ["docs/*.md"])
    assert found == ["docs/guide/intro.md"]  # only the top-level file is excluded


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


def test_resolve_worklist_relative_path_reads_from_cwd_not_root(tmp_path):
    # A relative explicit path means "relative to where the tool was run" (start_dir),
    # not the discovery root. Regression: it used to be read from the root, so running
    # from a subdirectory linted a same-named file higher up and passed silently.
    proj = tmp_path / "proj"
    sub = proj / "sub"
    sub.mkdir(parents=True)
    cfg = proj / "deslopper.config.json"
    cfg.write_text("{}", encoding="utf-8")
    make_files(str(proj), ["note.md", "sub/note.md"])   # same name at two levels
    items = resolve_worklist(["note.md"], str(cfg), str(sub), DEFAULT_INCLUDE, BUILTIN_EXCLUDE)
    # reads the note.md in the cwd (sub/), displayed relative to the root (proj/)
    assert items == [("sub/note.md", os.path.join(str(sub), "note.md"))]
