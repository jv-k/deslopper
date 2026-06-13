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
