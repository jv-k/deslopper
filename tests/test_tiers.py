from deslopper import tiers


def test_known_is_the_closed_set():
    assert tiers.KNOWN == frozenset({"error", "warn"})
    assert tiers.is_known("error")
    assert not tiers.is_known("info")
    assert not tiers.is_known(None)


def test_github_level_per_tier():
    assert tiers.github_level("error") == "error"
    assert tiers.github_level("warn") == "warning"


def test_is_failing_reproduces_the_exit_rule():
    # error fails regardless of strict; warn fails only under strict.
    assert tiers.is_failing("error", strict=False) is True
    assert tiers.is_failing("error", strict=True) is True
    assert tiers.is_failing("warn", strict=False) is False
    assert tiers.is_failing("warn", strict=True) is True
