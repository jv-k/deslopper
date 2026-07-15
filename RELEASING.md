# Releasing deslopper

A release tags a version and lets CI publish it.
[ver-bump](https://github.com/jv-k/ver-bump) cuts it, the same way the engineering-playbook
cuts its own.

The version lives in three files. `package.json` is the source ver-bump reads and bumps.
`.ver-bumprc` names the other two as `BUMP_FILES`, so `pyproject.toml` and
`src/deslopper/__init__.py` move in lock-step. Bumping any of them by hand, or with a tool
that only knows `package.json`, leaves the tag pointing at the wrong version, and
`release.yml` only catches that once the tag is public. That is what happened to v0.1.2.
`tests/test_version.py` fails on any drift, in CI and in the release gates.

ver-bump needs the `--bump` targets feature for the two non-JSON files. Nothing older than
that can cut a release here.

## One-time setup

PyPI Trusted Publishing lets the release workflow publish without a stored token:

1. Create the `deslopper` project on PyPI (a first manual upload, or reserve the name).
2. Under the project's publishing settings, add a GitHub publisher: owner `jv-k`, repo
   `deslopper`, workflow `release.yml`, environment `pypi`.

For Homebrew, create the tap repo `jv-k/homebrew-tap` once. Each release, a maintainer
copies `packaging/homebrew/deslopper.rb` into it, as described under After publishing.

## Cut a release

Write the `CHANGELOG.md` section for the version you are about to cut, under the
`# Changelog` title, headed `## X.Y.Z`. ver-bump runs with `-c` and leaves the changelog
alone: its generated entries are raw commit subjects, which land above the title and carry
em dashes that deslopper's own lint rejects. The commit subjects still reach the GitHub
release, which `--generate-notes` writes.

Then, on `main`, with the venv installed (`pip install -e . pytest build`):

    pnpm bump-release

It runs the pre-tag gates (the tests, the lint, and a build), then hands off to ver-bump,
which prompts for the version, bumps the three files, commits, tags `vX.Y.Z`, and pushes to
`origin`. Enter the same version the changelog section names. The tag triggers `release.yml`,
which repeats the gates and publishes to PyPI. `gh release create --generate-notes` writes
the GitHub release last.

Any runner works in place of `pnpm`: `npm run bump-release`, or the command itself.

If `release.yml` fails before the upload to PyPI, delete the tag with `git tag -d vX.Y.Z`
and `git push origin :refs/tags/vX.Y.Z`, fix the problem, commit, and re-cut the same
version with `ver-bump -c -p origin -v X.Y.Z`. If it fails during or after the upload, PyPI
will not accept the same version a second time: bump a new patch version and release that
instead.

## After publishing

- Update the Homebrew formula: set the new `url` and `sha256` from the published sdist in
  `packaging/homebrew/deslopper.rb` (the source of truth), then copy it into the tap as
  `Formula/deslopper.rb`, by hand or with `brew bump-formula-pr`.
- Move consumers off the git ref. In a repo that pins `uvx --from git+...@main`, change it to
  `uvx deslopper@X.Y.Z`.
