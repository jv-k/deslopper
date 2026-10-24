"""A JSON file store for answers worth keeping between runs.

Each value is one file under the user cache folder, named by the SHA-256 of its
key. A key is any JSON-able structure, so a caller puts everything the answer
depends on into it and a change to any part is a miss. Reads and writes never
raise: a cache that cannot be read or written acts as an empty one, so it can
never fail a lint.
"""

import hashlib
import json
import os
import tempfile


def default_dir(name: str) -> str:
    """The `name` folder under `$XDG_CACHE_HOME/deslopper`, or `~/.cache/deslopper`."""
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "deslopper", name)


class Store:
    """Values by key, one file each under `root`. The folder is made on first write."""

    def __init__(self, root: str):
        self.root = root

    def _path(self, key) -> str:
        canonical = json.dumps(key, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return os.path.join(self.root, digest[:2], digest + ".json")

    def get(self, key):
        """The value stored for `key`, or None when there is none or it cannot be read."""
        try:
            with open(self._path(key), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def put(self, key, value) -> None:
        """Store `value` for `key`. The write is atomic, so a reader never sees half a file."""
        path = self._path(key)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        except OSError:
            return
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(value, fh)
            os.replace(tmp, path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
