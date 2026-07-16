"""File and config discovery, and the path base for emitted findings."""

import os
import re
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


_GLOB_CACHE = {}


def _glob_to_regex(pat: str):
    """Compile a glob to a regex over a slash-separated path.

    `*` matches a run of non-slash characters, `?` one such character, and `**` as a whole
    path segment spans zero or more segments (`**/` at the start or middle) or the rest of
    the path (trailing `**`). Unlike fnmatch, `*` never crosses a slash.
    """
    rx = _GLOB_CACHE.get(pat)
    if rx is None:
        i, n, out = 0, len(pat), []
        while i < n:
            ch = pat[i]
            if ch == "*":
                j = i
                while j < n and pat[j] == "*":
                    j += 1
                stars, prev, nxt = j - i, pat[i - 1] if i else "", pat[j] if j < n else ""
                if stars >= 2 and prev in ("", "/") and nxt in ("", "/"):
                    if nxt == "/":
                        out.append("(?:[^/]+/)*")   # **/ : zero or more path segments
                        j += 1                        # absorb the slash
                    else:
                        out.append(".*")              # trailing ** : the rest of the path
                else:
                    out.append("[^/]*")               # * : a run of non-slash
                i = j
            elif ch == "?":
                out.append("[^/]")
                i += 1
            else:
                out.append(re.escape(ch))
                i += 1
        rx = re.compile("^" + "".join(out) + "$")
        _GLOB_CACHE[pat] = rx
    return rx


def _match_glob(rel: str, pat: str) -> bool:
    return _glob_to_regex(pat).match(rel) is not None


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
    kept = [r for r in rels if _included(r, include) and not _excluded(r, exclude)]
    # git ls-files lists index entries, so a tracked file deleted from the worktree would
    # otherwise reach the reader and be reported unreadable. Keep only what is on disk.
    return [r for r in kept if os.path.isfile(os.path.join(root, r))]


def resolve_inputs(paths, root: str, start_dir: str, include, exclude) -> list:
    """Map inputs to (display, read) items: the display path is relative to root.

    An explicit relative path is resolved against start_dir, the directory the tool was
    run from — not root — so running from a subdirectory reads the file the user named.
    """
    if paths:
        items = []
        for p in paths:
            full = p if os.path.isabs(p) else os.path.join(start_dir, p)
            display = os.path.relpath(full, root).replace(os.sep, "/")
            # A file outside root relpaths to ../.., which is not a usable finding path;
            # fall back to the absolute path so the finding still points somewhere real.
            if display == ".." or display.startswith("../"):
                display = os.path.abspath(full).replace(os.sep, "/")
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
