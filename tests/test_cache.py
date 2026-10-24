"""The answer cache: a JSON file per key, which never fails the caller."""

import os

from deslopper import cache


def test_a_stored_value_comes_back_for_the_same_key(tmp_path):
    store = cache.Store(str(tmp_path))
    store.put({"tell": "em-dash", "context": [[True, "a — b"]]}, {"verdict": "keep"})
    assert store.get({"context": [[True, "a — b"]], "tell": "em-dash"}) == {"verdict": "keep"}


def test_a_key_never_stored_is_a_miss(tmp_path):
    store = cache.Store(str(tmp_path))
    store.put({"tell": "em-dash"}, {"verdict": "keep"})
    assert store.get({"tell": "semicolon"}) is None


def test_a_corrupt_entry_is_a_miss(tmp_path):
    store = cache.Store(str(tmp_path))
    store.put({"tell": "em-dash"}, {"verdict": "keep"})
    (entry,) = [os.path.join(d, f) for d, _, fs in os.walk(tmp_path) for f in fs]
    with open(entry, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    assert store.get({"tell": "em-dash"}) is None


def test_an_unwritable_folder_is_silently_an_empty_cache(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("in the way", encoding="utf-8")
    store = cache.Store(str(blocker / "cache"))
    store.put({"tell": "em-dash"}, {"verdict": "keep"})
    assert store.get({"tell": "em-dash"}) is None


def test_the_default_folder_follows_xdg_cache_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert cache.default_dir("jev") == os.path.join(str(tmp_path), "deslopper", "jev")


def test_the_default_folder_falls_back_to_dot_cache(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert cache.default_dir("jev") == os.path.join(str(tmp_path), ".cache", "deslopper", "jev")
