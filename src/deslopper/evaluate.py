"""The rewrite-pass eval: sandbox seeding, the two judges, and the run loop.

An eval seeds a sandbox with slop fixtures, hands it to the rewrite command under
test, and judges the result twice: efficacy (the lint findings must be gone) and
preservation (the protected content must be untouched).
"""

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from importlib import resources

from . import report
from .config import resolve
from .digest import diff_components, digest_text
from .engine import lint_files

FIXTURE_SUFFIX = ".md.txt"

# The eval's distinct exit codes. 2 stays reserved for usage and config errors,
# matching the lint command.
EXIT_PASS = 0
EXIT_EFFICACY = 1
EXIT_PRESERVATION = 3
EXIT_HARNESS_BROKEN = 4


def seed_sandbox(dest: str) -> list:
    """Copy the packaged fixtures into dest, renamed from .md.txt to .md.

    The .md.txt suffix keeps the fixtures out of any lint run over this package's
    own tree; the rename makes them real Markdown for the command under test.
    Returns the seeded names in sorted order.
    """
    seeded = []
    root = resources.files("deslopper.data").joinpath("eval")
    for entry in sorted(root.iterdir(), key=lambda e: e.name):
        if not entry.name.endswith(FIXTURE_SUFFIX):
            continue
        name = entry.name[: -len(FIXTURE_SUFFIX)] + ".md"
        with open(os.path.join(dest, name), "wb") as fh:
            fh.write(entry.read_bytes())
        seeded.append(name)
    return seeded


def _lint_sandbox(sandbox, names, tells):
    return lint_files([(n, os.path.join(sandbox, n)) for n in names], tells)


def _read(sandbox, name):
    with open(os.path.join(sandbox, name), encoding="utf-8") as fh:
        return fh.read()


def _broken(why: str) -> int:
    print(f"deslopper eval: harness broken: {why}", file=sys.stderr)
    return EXIT_HARNESS_BROKEN


def run_eval(command: str, keep: bool = False) -> int:
    """Seed a sandbox, run the rewrite command over it, judge the result.

    The command runs through the shell. A `{dir}` placeholder receives the
    sandbox path; without one the path is appended as the final argument.
    """
    tells = resolve({}).tells
    sandbox = tempfile.mkdtemp(prefix="deslopper-eval-")
    try:
        names = seed_sandbox(sandbox)

        baseline = _lint_sandbox(sandbox, names, tells)
        if baseline.errors == 0:
            return _broken("the raw fixtures produced no error-tier findings")
        if baseline.warnings == 0:
            # The strictly-below warn gate needs headroom, so a warnless baseline
            # could never pass either.
            return _broken("the raw fixtures produced no warn-tier findings")
        before = {n: digest_text(_read(sandbox, n)) for n in names}
        print(
            f"deslopper eval: seeded {len(names)} fixture(s), baseline "
            f"{baseline.errors} error(s), {baseline.warnings} warning(s)",
            file=sys.stderr,
        )

        # {dir} receives the path itself, so a template can place its own quotes.
        if "{dir}" in command:
            shell_command = command.replace("{dir}", sandbox)
        else:
            shell_command = f"{command} {shlex.quote(sandbox)}"
        proc = subprocess.run(shell_command, shell=True)

        result = _lint_sandbox(sandbox, names, tells)
        sys.stdout.write(report.format_text(result))
        efficacy_failures = []
        if result.errors:
            efficacy_failures.append(f"{result.errors} error(s) remain")
        if result.warnings >= baseline.warnings:
            efficacy_failures.append(
                f"warnings {result.warnings} not below baseline {baseline.warnings}"
            )

        preservation_failures = []
        for name in names:
            for label in diff_components(before[name], digest_text(_read(sandbox, name))):
                preservation_failures.append(f"{name}: {label} differs")
        for line in preservation_failures:
            print(f"preservation: {line}")

        # A nonzero command exit is judged and reported like any run, but the
        # broken-harness code wins over both judges.
        if proc.returncode != 0:
            return _broken(f"the rewrite command exited {proc.returncode}")

        if preservation_failures:
            verdict, code = "FAIL (preservation)", EXIT_PRESERVATION
        elif efficacy_failures:
            verdict, code = "FAIL (efficacy)", EXIT_EFFICACY
        else:
            verdict, code = "PASS", EXIT_PASS
        detail = "; ".join(efficacy_failures + preservation_failures) or (
            f"0 error(s), {result.warnings} warning(s) < baseline {baseline.warnings}"
        )
        print(f"deslopper eval: {verdict}: {detail}", file=sys.stderr)
        return code
    finally:
        if keep:
            print(f"deslopper eval: sandbox kept at {sandbox}", file=sys.stderr)
        else:
            shutil.rmtree(sandbox, ignore_errors=True)
