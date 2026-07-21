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

PyPI Trusted Publishing lets the release workflow publish without a stored token:

1. Create the `deslopper` project on PyPI (a first manual upload, or reserve the name).
2. Under the project's publishing settings, add a GitHub publisher: owner `jv-k`, repo
   `deslopper`, workflow `release.yml`, environment `pypi`.

For Homebrew, create the tap repo `jv-k/homebrew-tap` once. Each release, a maintainer
copies `packaging/homebrew/deslopper.rb` into it, as described under After publishing.

## Cut a release

Write the `CHANGELOG.md` section for the version you are about to cut, under the
`# Changelog` title, headed `## X.Y.Z`. VerBump runs with `-c` and leaves the changelog
alone: its generated entries are raw commit subjects, which land above the title and carry
em dashes that deslopper's own lint rejects. The commit subjects still reach the GitHub
release, which `--generate-notes` writes.

Then, on `main`, with the venv installed (`pip install -e . pytest build`) and the node
dev tools installed (`pnpm install` provides the `verbump` command):

    pnpm bump-release

The task runs in four steps, and nothing leaves the machine until the third one passes:

1. `scripts/preflight.sh` checks a clean tree on `main`, then runs the tests, the lint, and
   a build.
2. VerBump prompts for the version, bumps the three files, commits, and tags `vX.Y.Z`.
   Enter the same version the changelog section names. It runs with `-c` and does not push.
3. `scripts/postflight.sh` checks what the bump produced: a clean tree, `HEAD` tagged to
   match `package.json`, the three version files in agreement, a lint that still passes,
   and the tests.
4. The tag and commit are pushed, then `gh release create --generate-notes` writes the
   GitHub release. The tag triggers `release.yml`, which repeats the gates and publishes to
   PyPI.

Any runner works in place of `pnpm`: `npm run bump-release`, or the command itself.

If step 3 fails, nothing is public. Undo the bump locally with `git reset --hard HEAD~1`
and `git tag -d vX.Y.Z`, fix the cause, and start again.

If `release.yml` fails before the upload to PyPI, delete the tag with `git tag -d vX.Y.Z`
and `git push origin :refs/tags/vX.Y.Z`, fix the problem, commit, and re-cut the same
version with `verbump -c -v X.Y.Z`. If it fails during or after the upload, PyPI will not
accept the same version a second time: bump a new patch version and release that instead.

## After publishing

- Update the Homebrew formula: set the new `url` and `sha256` from the published sdist in
  `packaging/homebrew/deslopper.rb` (the source of truth), then copy it into the tap as
  `Formula/deslopper.rb`, by hand or with `brew bump-formula-pr`.
- Move consumers off the git ref. In a repo that pins `uvx --from git+...@main`, change it to
  `uvx deslopper@X.Y.Z`.
