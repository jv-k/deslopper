"""The update command: detect the install, then run that tool's upgrade."""

import pytest

from deslopper import update
from deslopper.cli import main


def venv(tmp_path, *parts):
    prefix = tmp_path.joinpath(*parts)
    prefix.mkdir(parents=True)
    return prefix


def homebrew(tmp_path):
    prefix = venv(tmp_path, "Cellar", "deslopper", "1.5.0", "libexec")
    (prefix.parent / "INSTALL_RECEIPT.json").write_text("{}")
    return prefix


def pipx(tmp_path):
    prefix = venv(tmp_path, "pipx", "venvs", "deslopper")
    (prefix / "pipx_metadata.json").write_text("{}")
    return prefix


def uv_tool(tmp_path):
    prefix = venv(tmp_path, "uv", "tools", "deslopper")
    (prefix / "uv-receipt.toml").write_text("")
    return prefix


def test_detects_homebrew(tmp_path):
    install = update.detect(str(homebrew(tmp_path)), None)
    assert install.method == "Homebrew"
    assert install.command == ("brew", "upgrade", "jv-k/tap/deslopper")


def test_detects_pipx(tmp_path):
    install = update.detect(str(pipx(tmp_path)), None)
    assert install.method == "pipx"
    assert install.command == ("pipx", "upgrade", "deslopper")


def test_detects_a_uv_tool(tmp_path):
    install = update.detect(str(uv_tool(tmp_path)), None)
    assert install.method == "uv"
    assert install.command == ("uv", "tool", "upgrade", "deslopper")


def test_an_editable_install_is_never_upgraded(tmp_path):
    direct_url = {"dir_info": {"editable": True}, "url": "file:///src/deslopper"}
    install = update.detect(str(pipx(tmp_path)), direct_url)
    assert install.command is None
    assert "git pull" in install.hint
    assert "/src/deslopper" in install.hint


def test_a_uvx_run_names_the_refresh_flag(tmp_path):
    prefix = venv(tmp_path, ".cache", "uv", "archive-v0", "abc123")
    install = update.detect(str(prefix), None)
    assert install.command is None
    assert "uvx --refresh" in install.hint


def test_any_other_install_names_the_pip_command(tmp_path):
    install = update.detect(str(venv(tmp_path, "myenv")), None)
    assert install.command is None
    assert "pip install --upgrade git+https://github.com/jv-k/deslopper" in install.hint


class Calls(list):
    """The commands the fake subprocess.call saw, and the code it returns."""

    code = 0

    def __call__(self, command):
        self.append(tuple(command))
        return self.code


@pytest.fixture
def calls(monkeypatch):
    seen = Calls()
    monkeypatch.setattr(update.subprocess, "call", seen)
    monkeypatch.setattr(update.shutil, "which", lambda name: f"/bin/{name}")
    return seen


def run(args, capsys):
    code = main(args)
    out = capsys.readouterr()
    return code, out.out, out.err


def test_update_runs_the_detected_upgrade(tmp_path, monkeypatch, capsys, calls):
    monkeypatch.setattr(update.sys, "prefix", str(homebrew(tmp_path)))
    monkeypatch.setattr(update, "_direct_url", lambda: None)
    code, out, _ = run(["update"], capsys)
    assert code == 0
    assert calls == [("brew", "upgrade", "jv-k/tap/deslopper")]
    assert "brew upgrade jv-k/tap/deslopper" in out
    assert "deslopper --version" in out


def test_dry_run_prints_the_command_and_runs_nothing(tmp_path, monkeypatch, capsys, calls):
    monkeypatch.setattr(update.sys, "prefix", str(pipx(tmp_path)))
    monkeypatch.setattr(update, "_direct_url", lambda: None)
    code, out, _ = run(["update", "--dry-run"], capsys)
    assert code == 0
    assert calls == []
    assert "pipx upgrade deslopper" in out


def test_a_failed_upgrade_exits_one(tmp_path, monkeypatch, capsys, calls):
    monkeypatch.setattr(update.sys, "prefix", str(uv_tool(tmp_path)))
    monkeypatch.setattr(update, "_direct_url", lambda: None)
    calls.code = 3
    code, _, err = run(["update"], capsys)
    assert code == 1
    assert "uv tool upgrade deslopper" in err


def test_a_missing_tool_exits_two(tmp_path, monkeypatch, capsys, calls):
    monkeypatch.setattr(update.sys, "prefix", str(pipx(tmp_path)))
    monkeypatch.setattr(update, "_direct_url", lambda: None)
    monkeypatch.setattr(update.shutil, "which", lambda name: None)
    code, _, err = run(["update"], capsys)
    assert code == 2
    assert calls == []
    assert "pipx" in err


def test_an_install_it_cannot_upgrade_prints_the_hint(tmp_path, monkeypatch, capsys, calls):
    monkeypatch.setattr(update.sys, "prefix", str(venv(tmp_path, "myenv")))
    monkeypatch.setattr(update, "_direct_url", lambda: None)
    code, out, _ = run(["update"], capsys)
    assert code == 0
    assert calls == []
    assert "pip install --upgrade" in out
