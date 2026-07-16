"""File and config discovery, and the path base for emitted findings."""

import fnmatch
import os
import subprocess

CONFIG_NAME = "deslopper.config.json"


def find_config(start_dir: str):
    cur = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(cur, CONFIG_NAME)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def _git_toplevel(start_dir: str):
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start_dir, capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    top = out.stdout.strip()
    return top if out.returncode == 0 and top else None


def discovery_root(config_path, start_dir: str) -> str:
    if config_path:
        return os.path.dirname(os.path.abspath(config_path))
    top = _git_toplevel(start_dir)
    return top if top else os.path.abspath(start_dir)


def _match_glob(rel: str, pat: str) -> bool:
    """Match a relative path against a glob pattern, handling ** as a recursive wildcard."""
    if fnmatch.fnmatch(rel, pat):
        return True
    # If the pattern starts with **/, also try matching without the leading **/
    # so that e.g. **/vendor/** matches vendor/d.md at the tree root.
    if pat.startswith("**/"):
        return fnmatch.fnmatch(rel, pat[3:])
    return False


def _excluded(rel: str, exclude) -> bool:
    return any(_match_glob(rel, pat) for pat in exclude)


def _included(rel: str, include) -> bool:
    return any(_match_glob(rel, pat) for pat in include)


def _git_files(root: str):
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root, capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return [p for p in out.stdout.split("\0") if p]


def _walk_files(root: str):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirnames:
            dirnames.remove(".git")
        for name in filenames:
            full = os.path.join(dirpath, name)
            found.append(os.path.relpath(full, root))
    return found


def discover_files(root: str, include, exclude) -> list:
    candidates = _git_files(root)
    if candidates is None:
        candidates = _walk_files(root)
    rels = sorted(c.replace(os.sep, "/") for c in candidates)
    return [r for r in rels if _included(r, include) and not _excluded(r, exclude)]


def resolve_inputs(paths, root: str, start_dir: str, include, exclude) -> list:
    """Map inputs to (display, read) items: display relative to root, read absolute.

    An explicit relative path is resolved against start_dir, the directory the tool was
    run from — not root — so running from a subdirectory reads the file the user named.
    """
    if paths:
        items = []
        for p in paths:
            full = p if os.path.isabs(p) else os.path.join(start_dir, p)
            display = os.path.relpath(full, root).replace(os.sep, "/")
            items.append((display, full))
        return items
    rels = discover_files(root, include, exclude)
    return [(rel, os.path.join(root, rel)) for rel in rels]


def resolve_worklist(paths, config_path, start_dir: str, include, exclude) -> list:
    """Turn CLI inputs into the work list of (display, read) items.

    Owns the discovery root — a config directory, else the git top level, else start_dir —
    so callers never compute or pass it. With explicit paths, include and exclude do not
    apply; without them, the tracked or walked tree is filtered by both.
    """
    root = discovery_root(config_path, start_dir)
    return resolve_inputs(paths, root, start_dir, include, exclude)
