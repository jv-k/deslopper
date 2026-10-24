# Releasing deslopper

A release tags a version and lets CI publish it.
[VerBump](https://github.com/jv-k/VerBump) cuts it, the same way the engineering-playbook
cuts its own.

The version lives in three files. `package.json` is the source VerBump reads and bumps.
`.verbumprc` names the other two as `BUMP_FILES`, so `pyproject.toml` and
`src/deslopper/__init__.py` move in lock-step. Bumping any of them by hand, or with a tool
that only knows `package.json`, leaves the tag pointing at the wrong version, and
`release.yml` only catches that once the tag is public. That is what happened to v0.1.2.
`tests/test_version.py` fails on any drift, in CI and in the release gates.

Whether a given VerBump actually moved all three is a fact about the result, not about the
tool's help text, so `scripts/postflight.sh` asserts it after the bump and before the push.
A VerBump that only knows `package.json` fails there, while the tag is still local.

## One-time setup

PyPI Trusted Publishing lets the release workflow publish without a stored token. The
`publish-pypi` job in `release.yml` is off (`if: false`) until these two steps are done, so
a release publishes to Homebrew only:

1. Create the `deslopper` project on PyPI (a first manual upload, or reserve the name).
2. Under the project's publishing settings, add a GitHub publisher: owner `jv-k`, repo
   `deslopper`, workflow `release.yml`, environment `pypi`.

For Homebrew, create the tap repo `jv-k/homebrew-tap` with `Formula/deslopper.rb` once.
Then add a fine-grained token with Contents read and write on that repo alone as the
`HOMEBREW_TAP_TOKEN` repository secret. Each release, `release.yml` rewrites the formula's
`url` and `sha256` for the new tag and pushes it to the tap.

## Cut a release

Write the `CHANGELOG.md` section for the version you are about to cut, under the
`# Changelog` title, headed `## X.Y.Z`. VerBump runs with `-c` and leaves the changelog
alone: its generated entries are raw commit subjects, which land above the title and carry
em dashes that deslopper's own lint rejects. The commit subjects still reach the GitHub
release, which `--generate-notes` writes.

Then, on `main`, with the venv installed (`pip install -e . pytest build`) and the node
dev tools installed (`pnpm install` provides the `verbump` command):

    pnpm bump-release

The task runs in four steps, and nothing leaves the machine until the third one passes.
The gates in steps 1 and 3 are VerBump's own hooks, `PRE_BUMP_CMD` and `POST_TAG_CMD` in
`.verbumprc`, so they run on any `verbump` invocation, not only through this task:

1. `scripts/preflight.sh` checks a clean tree on `main`, then runs the tests, the lint, a
   build, and a live `--jev` run over `tests/fixtures/ai_slop.md` that must judge every
   finding. The suite fakes the gateway, so this is where the real integration is proved
   before a release, and it needs `AI_GATEWAY_API_KEY` in your shell. A failure here
   changes nothing.
2. VerBump prompts for the version, bumps the three files, commits, and tags `vX.Y.Z`.
   Enter the same version the changelog section names. It runs with `-c`, so the changelog
   is left alone. The commit goes through the repo's pre-commit hooks, so the suite runs
   once more there.
3. `scripts/postflight.sh` checks what the bump produced: a clean tree, `HEAD` tagged to
   match `package.json`, the three version files in agreement, a lint that still passes,
   and the tests.
4. VerBump pushes the commit and tag to `origin` (`-p origin`, so there is no prompt to
   decline) and writes the GitHub release with `gh release create --generate-notes`
   (`--release`). The tag triggers `release.yml`, which repeats the gates, publishes to
   PyPI when that job is on, and bumps the Homebrew tap.

Any runner works in place of `pnpm`: `npm run bump-release`, or the command itself.

If step 3 fails, nothing is public. VerBump keeps the commit and tag for inspection. Undo
the tag with `verbump --undo X.Y.Z`. The bump commit stays, and while it is unpushed you can
drop it too with `git reset --hard HEAD~1`. Fix the cause and start again. `--no-hooks`
skips both gates for a single run, for the rare case where the gate itself is what is
broken.

If `release.yml` fails before the upload to PyPI, delete the tag with `git tag -d vX.Y.Z`
and `git push origin :refs/tags/vX.Y.Z`, fix the problem, commit, and re-cut the same
version with `verbump -c -v X.Y.Z`. If it fails during or after the upload, PyPI will not
accept the same version a second time: bump a new patch version and release that instead.

If only a publish job failed, for example because a secret was missing, fix the cause and
run the release again for the same tag. Within 30 days of the run, re-run its failed jobs
from the Actions tab. After that, GitHub refuses the re-run, so dispatch the workflow by
hand: `gh workflow run release.yml -f tag=vX.Y.Z`. A dispatched run checks out the tag,
skips a version PyPI already holds, and leaves a tap that is already current alone.

## After publishing

- Check that the tap moved: `Formula/deslopper.rb` in `jv-k/homebrew-tap` names the new tag.
- Move consumers off the git ref. In a repo that pins `uvx --from git+...@main`, change it to
  `uvx deslopper@X.Y.Z`.
