# Releasing deslopper

A release tags a version and lets CI publish it. The version lives in three files, kept in
sync by the bump script.

## One-time setup

PyPI Trusted Publishing lets the release workflow publish without a stored token:

1. Create the `deslopper` project on PyPI (a first manual upload, or reserve the name).
2. Under the project's publishing settings, add a GitHub publisher: owner `jv-k`, repo
   `deslopper`, workflow `release.yml`, environment `pypi`.

For Homebrew, create the tap repo `jv-k/homebrew-tap` once. Its `Formula/deslopper.rb` is a
copy of `packaging/homebrew/deslopper.rb` with `url` and `sha256` filled from the published
sdist.

## Cut a release

1. Bump the version with `pnpm bump:patch`, `pnpm bump:minor`, or `pnpm bump:major`. The
   script edits `pyproject.toml`, `src/deslopper/__init__.py`, and `package.json` together
   and prints the new version.
2. Move the unreleased `CHANGELOG.md` entries under the new version heading.
3. Commit as `chore(release): vX.Y.Z`.
4. Run `pnpm release`. It checks the tree is clean, runs the tests, tags `vX.Y.Z`, and
   pushes the tag. The tag triggers `release.yml`, which builds the package and publishes it
   to PyPI.

## After publishing

- Update the Homebrew tap: set the new `url` and `sha256` in `Formula/deslopper.rb` (a plain
  edit, or `brew bump-formula-pr`).
- Move consumers off the git ref. In a repo that pins `uvx --from git+...@main`, change it to
  `uvx deslopper@X.Y.Z`.
