# Releasing deslopper

A release tags a version and lets CI publish it. The version lives in three files, kept in
sync by the bump script.

Bump with `scripts/bump.py` (or `pnpm bump:*`), never with a generic Node version tool. This
repo has a `package.json` for its scripts, but the package is Python: a tool that bumps only
`package.json` leaves `pyproject.toml` behind, and the tag then fails the version check in
`release.yml` once it is already public. `scripts/release.sh` checks the three files agree
before it tags anything.

## One-time setup

PyPI Trusted Publishing lets the release workflow publish without a stored token:

1. Create the `deslopper` project on PyPI (a first manual upload, or reserve the name).
2. Under the project's publishing settings, add a GitHub publisher: owner `jv-k`, repo
   `deslopper`, workflow `release.yml`, environment `pypi`.

For Homebrew, create the tap repo `jv-k/homebrew-tap` once. Each release, a maintainer
copies `packaging/homebrew/deslopper.rb` into it, as described under After publishing.

## Cut a release

Make sure `CHANGELOG.md` has an `(unreleased)` section listing the changes, then run, on
`main`:

    pnpm bump-release [patch|minor|major]    # default: patch

It bumps the version (`pyproject.toml`, `src/deslopper/__init__.py`, and `package.json`,
kept in sync by `scripts/bump.py`), retitles the changelog heading to the new version,
commits `chore(release): vX.Y.Z`, and hands off to `scripts/release.sh`, which runs the
pre-tag gates (a clean tree, the version check, the tests, the lint, and a build), then
pushes `main` and the tag `vX.Y.Z` in one atomic push. The tag triggers `release.yml`,
which repeats the gates and publishes to PyPI.

The pieces run individually too: `pnpm bump:patch|minor|major`, then a manual changelog
retitle and `chore(release)` commit, then `pnpm release`. Any runner works in place of
`pnpm`: `npm run <script>`, or the scripts directly.

If `release.yml` fails before the upload to PyPI, delete the tag with `git tag -d vX.Y.Z`
and `git push origin :refs/tags/vX.Y.Z`, fix the problem, commit, and run `pnpm release`
again. If it fails during or after the upload, PyPI will not accept the same version a
second time: bump a new patch version and release that instead.

## After publishing

- Update the Homebrew formula: set the new `url` and `sha256` from the published sdist in
  `packaging/homebrew/deslopper.rb` (the source of truth), then copy it into the tap as
  `Formula/deslopper.rb`, by hand or with `brew bump-formula-pr`.
- Move consumers off the git ref. In a repo that pins `uvx --from git+...@main`, change it to
  `uvx deslopper@X.Y.Z`.
