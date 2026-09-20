"""The rewrite-pass eval: sandbox seeding, the judges, and the run loop.

An eval seeds a sandbox with slop fixtures, hands it to the rewrite command under
test, and judges the result twice: efficacy (the lint findings must be gone) and
preservation (the protected content must be untouched). An opt-in third judge,
plainness, asks Jev to score each fixture before and after the rewrite and
reports the scores without touching the verdict.
"""

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from importlib import resources

from . import jev, report, ui
from .config import resolve
from .digest import diff_components, digest_text
from .engine import lint_files

FIXTURE_SUFFIX = ".md.txt"

# The eval's distinct exit codes. 2 stays reserved for usage and config errors,
# matching the lint command.
EXIT_PASS = 0
EXIT_USAGE = 2
EXIT_EFFICACY = 1
EXIT_PRESERVATION = 3
EXIT_HARNESS_BROKEN = 4

# The plainness judge's three buckets, in score order. The reported number is
# Jev's 0..1 score over them.
PLAINNESS_BUCKETS = (
    "pure machine-generated cadence",
    "readable with some tics",
    "plain engineering prose",
)


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


class PlainnessPass:
    """One Jev request over the fixtures: a score per readable fixture, the
    names it could not read, and the request's usage."""

    def __init__(self, scores, unreadable, tokens, cost):
        self.scores = scores
        self.unreadable = unreadable
        self.tokens = tokens
        self.cost = cost

    @property
    def mean(self):
        return sum(self.scores.values()) / len(self.scores) if self.scores else None


def score_plainness(sandbox, names, pal, label: str):
    """Ask Jev how plainly each fixture reads, in one request.

    Every fixture goes into `state` under a heading of its name, with one score
    question per fixture keyed by that name. A fixture that cannot be read is
    left out and listed as unreadable. A gateway failure, or a state over the
    client's budget, prints one error line and returns None, and the eval
    carries on without this pass.
    """
    texts, unreadable = {}, []
    for name in names:
        try:
            texts[name] = _read(sandbox, name)
        except OSError:
            unreadable.append(name)
    if not texts:
        return PlainnessPass({}, unreadable, None, None)
    state = "".join(f"===== {name} =====\n{text}\n" for name, text in texts.items())
    if len(state) > jev.STATE_CHAR_BUDGET:
        ui.log_error(pal, f"plainness ({label}): fixtures exceed the Jev state budget, skipped")
        return None
    questions = {
        name: jev.score(
            f"How plainly does the fixture headed '{name}' read, judged on its prose "
            "alone? Ignore code, front matter, tables, and links.",
            PLAINNESS_BUCKETS,
        )
        for name in texts
    }
    try:
        result = jev.evaluate(state, questions)
    except (jev.JevError, jev.JevUnavailable) as err:
        ui.log_error(pal, f"plainness ({label}): {err}")
        return None
    scores = {}
    for name in texts:
        answer = result.answers.get(name)
        if answer is not None and isinstance(answer.value, (int, float)):
            scores[name] = float(answer.value)
    tokens = None
    if result.input_tokens is not None or result.output_tokens is not None:
        tokens = (result.input_tokens or 0) + (result.output_tokens or 0)
    cost = None
    if result.market_cost is not None:
        try:
            cost = Decimal(str(result.market_cost))
        except InvalidOperation:
            cost = None
    return PlainnessPass(scores, unreadable, tokens, cost)


def _plainness_pair(pal, before, after) -> str:
    """`0.12 -> 0.84`, or just the one side that was scored."""
    sides = [f"{v:.2f}" for v in (before, after) if v is not None]
    return f" {pal.arrow} ".join(sides)


def report_plainness(pal, names, before, after):
    """Print one line per fixture and the mean, `before -> after`.

    Either pass may be None when it failed; a line then shows the side it has.
    A fixture the after pass could not read is reported as unreadable.
    """
    for name in names:
        if after is not None and name in after.unreadable:
            ui.log_info(pal, f"plainness {name}: unreadable")
            continue
        pair = _plainness_pair(
            pal,
            before.scores.get(name) if before else None,
            after.scores.get(name) if after else None,
        )
        ui.log_info(pal, f"plainness {name}: {pair or 'unscored'}")
    mean = _plainness_pair(pal, before.mean if before else None, after.mean if after else None)
    tokens = [p.tokens for p in (before, after) if p is not None and p.tokens is not None]
    costs = [p.cost for p in (before, after) if p is not None and p.cost is not None]
    tail = []
    if tokens:
        tail.append(f"{sum(tokens)} tokens")
    if costs:
        tail.append(f"${sum(costs)}")
    line = f"plainness mean: {mean or 'unscored'}"
    if tail:
        line += f" {pal.sep} " + ", ".join(tail)
    ui.log_info(pal, line)


def _broken(pal, why: str) -> int:
    ui.log_error(pal, f"eval harness broken: {why}")
    return EXIT_HARNESS_BROKEN


def run_eval(command: str, keep: bool = False, pal=None, plainness: bool = False) -> int:
    """Seed a sandbox, run the rewrite command over it, judge the result.

    The command runs through the shell. A `{dir}` placeholder receives the
    sandbox path; without one the path is appended as the final argument.
    With `plainness`, Jev scores the fixtures before and after the rewrite
    and the scores are reported without touching the verdict.
    """
    pal = ui.palette() if pal is None else pal
    if plainness and not os.environ.get(jev.KEY_VAR):
        # Checked before the sandbox exists, so no rewrite runs unscored.
        ui.log_error(pal, f"--plainness needs {jev.KEY_VAR}; export it to ask Jev")
        return EXIT_USAGE
    tells = resolve({}).tells
    sandbox = tempfile.mkdtemp(prefix="deslopper-eval-")
    try:
        names = seed_sandbox(sandbox)

        baseline = _lint_sandbox(sandbox, names, tells)
        if baseline.errors == 0:
            return _broken(pal, "the raw fixtures produced no error-tier findings")
        if baseline.warnings == 0:
            # The strictly-below warn gate needs headroom, so a warnless baseline
            # could never pass either.
            return _broken(pal, "the raw fixtures produced no warn-tier findings")
        before = {n: digest_text(_read(sandbox, n)) for n in names}
        ui.log_info(
            pal,
            f"seeded {len(names)} fixture(s), baseline "
            f"{baseline.errors} error(s), {baseline.warnings} warning(s)",
            stream=sys.stderr,
        )
        plain_before = None
        if plainness:
            plain_before = score_plainness(sandbox, names, pal, "baseline")

        # {dir} receives the path itself, so a template can place its own quotes.
        if "{dir}" in command:
            shell_command = command.replace("{dir}", sandbox)
        else:
            shell_command = f"{command} {shlex.quote(sandbox)}"
        proc = subprocess.run(shell_command, shell=True)

        result = _lint_sandbox(sandbox, names, tells)
        sys.stdout.write(report.format_text(result, pal))
        efficacy_failures = []
        if result.errors:
            efficacy_failures.append(f"{result.errors} error(s) remain")
        if result.warnings >= baseline.warnings:
            efficacy_failures.append(
                f"warnings {result.warnings} not below baseline {baseline.warnings}"
            )

        preservation_failures = []
        for name in names:
            try:
                after_text = _read(sandbox, name)
            except OSError:
                # A fixture the rewrite deleted or made unreadable has lost
                # every protected component at once.
                preservation_failures.append(f"{name}: unreadable")
                continue
            for label in diff_components(before[name], digest_text(after_text)):
                preservation_failures.append(f"{name}: {label} differs")
        for line in preservation_failures:
            print(f"preservation: {line}")

        # Reported, never gated: the verdict below does not read these.
        if plainness:
            plain_after = score_plainness(sandbox, names, pal, "after")
            report_plainness(pal, names, plain_before, plain_after)

        # A nonzero command exit is judged and reported like any run, but the
        # broken-harness code wins over both judges.
        if proc.returncode != 0:
            return _broken(pal, f"the rewrite command exited {proc.returncode}")

        if preservation_failures:
            verdict, code = "FAIL (preservation)", EXIT_PRESERVATION
        elif efficacy_failures:
            verdict, code = "FAIL (efficacy)", EXIT_EFFICACY
        else:
            verdict, code = "PASS", EXIT_PASS
        detail = "; ".join(efficacy_failures + preservation_failures) or (
            f"0 error(s), {result.warnings} warning(s) < baseline {baseline.warnings}"
        )
        if code == EXIT_PASS:
            ui.log_success(pal, f"eval {verdict}: {detail}", stream=sys.stderr)
        else:
            ui.log_error(pal, f"eval {verdict}: {detail}")
        return code
    finally:
        if keep:
            ui.log_info(pal, f"sandbox kept at {sandbox}", stream=sys.stderr)
        else:
            shutil.rmtree(sandbox, ignore_errors=True)
