from deslopper.presets.recommended import load


def test_recommended_has_twelve_tells_including_both_phase_variants():
    fragment = load()
    tells = fragment["tells"]
    assert len(tells) == 12
    names = [t["name"] for t in tells]
    assert names.count("em-dash") == 2
    assert names.count("section-sign") == 2
    # both phases present for the duplicated names
    phases = {(t["name"], t.get("phase", "post-entity")) for t in tells}
    assert ("em-dash", "pre-entity") in phases
    assert ("em-dash", "post-entity") in phases
    assert ("section-sign", "pre-entity") in phases
    assert ("section-sign", "post-entity") in phases


import json

import pytest

from deslopper.config import load_config, DEFAULT_INCLUDE, DEFAULT_EXCLUDE
from deslopper.errors import ConfigError


def write_config(tmp_path, obj):
    p = tmp_path / "deslopper.config.json"
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


def names(cfg):
    return [t.name for t in cfg.tells]


def test_no_config_uses_recommended_and_default_files(tmp_path):
    cfg, path = load_config(None, str(tmp_path))
    assert path == ""
    assert len(cfg.tells) == 12
    assert cfg.strict is False
    assert cfg.include == DEFAULT_INCLUDE
    assert cfg.exclude == DEFAULT_EXCLUDE


def test_disable_by_unique_name(tmp_path):
    write_config(tmp_path, {"tells": {"disable": ["semicolon"]}})
    cfg, _ = load_config(None, str(tmp_path))
    assert "semicolon" not in names(cfg)
    assert len(cfg.tells) == 11


def test_disable_ambiguous_bare_name_is_error(tmp_path):
    write_config(tmp_path, {"tells": {"disable": ["em-dash"]}})
    with pytest.raises(ConfigError):
        load_config(None, str(tmp_path))


def test_disable_one_phase_variant_with_qualified_name(tmp_path):
    write_config(tmp_path, {"tells": {"disable": ["em-dash@pre-entity"]}})
    cfg, _ = load_config(None, str(tmp_path))
    keys = {t.key for t in cfg.tells}
    assert ("em-dash", "pre-entity") not in keys
    assert ("em-dash", "post-entity") in keys


def test_override_tier_in_place(tmp_path):
    write_config(tmp_path, {"tells": {"override": {"filler-verb": {"tier": "error"}}}})
    cfg, _ = load_config(None, str(tmp_path))
    by_name = {t.name: t for t in cfg.tells}
    assert by_name["filler-verb"].tier == "error"


def test_add_appends_new_tell(tmp_path):
    write_config(tmp_path, {"tells": {"add": [
        {"name": "no-foo", "tier": "warn", "kind": "regex", "pattern": "foo", "message": "no foo"}
    ]}})
    cfg, _ = load_config(None, str(tmp_path))
    assert "no-foo" in names(cfg)
    assert names(cfg)[-1] == "no-foo"


def test_override_missing_target_is_error(tmp_path):
    write_config(tmp_path, {"tells": {"override": {"nope": {"tier": "error"}}}})
    with pytest.raises(ConfigError):
        load_config(None, str(tmp_path))


def test_plugins_entry_is_error_in_v01(tmp_path):
    write_config(tmp_path, {"plugins": ["deslopper-passive"]})
    with pytest.raises(ConfigError):
        load_config(None, str(tmp_path))


def test_non_builtin_extends_is_error_in_v01(tmp_path):
    write_config(tmp_path, {"extends": ["deslopper:recommended", "deslopper-british"]})
    with pytest.raises(ConfigError):
        load_config(None, str(tmp_path))


def test_strict_and_files_from_config(tmp_path):
    write_config(tmp_path, {"strict": True, "files": {"include": ["docs/**/*.md"], "exclude": ["x/**"]}})
    cfg, _ = load_config(None, str(tmp_path))
    assert cfg.strict is True
    assert cfg.include == ["docs/**/*.md"]
    # built-in skips are always unioned in
    assert "**/node_modules/**" in cfg.exclude
    assert "x/**" in cfg.exclude


def test_malformed_json_is_error(tmp_path):
    (tmp_path / "deslopper.config.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(None, str(tmp_path))


from importlib import resources


def test_schemas_are_packaged():
    for name in ("config.schema.json", "output.schema.json"):
        text = resources.files("deslopper.schema").joinpath(name).read_text(encoding="utf-8")
        assert json.loads(text)["title"].startswith("deslopper")
