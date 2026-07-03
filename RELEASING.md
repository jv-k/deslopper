# Releasing deslopper

A release tags a version and lets CI publish it. The version lives in three files, kept in
sync by the bump script.

## One-time setup

PyPI Trusted Publishing lets the release workflow publish without a stored token:

1. Create the `deslopper` project on PyPI (a first manual upload, or reserve the name).
2. Under the project's publishing settings, add a GitHub publisher: owner `jv-k`, repo
   `deslopper`, workflow `release.yml`, environment `pypi`.

For Homebrew, create the tap repo `jv-k/homebrew-tap` once. Each release copies
`packaging/homebrew/deslopper.rb` into it, as described under After publishing.

## Cut a release

The steps use `pnpm`, but any runner works: `npm run <script>`, or the scripts directly
(`python3 scripts/bump.py patch`, `bash scripts/release.sh`).

1. Bump the version with `pnpm bump:patch`, `pnpm bump:minor`, or `pnpm bump:major`. The
   script edits `pyproject.toml`, `src/deslopper/__init__.py`, and `package.json` together
   and prints the new version.
2. In `CHANGELOG.md`, retitle the `(unreleased)` heading to the new version, so the
   entries sit under a heading that matches the tag.
3. Commit as `chore(release): vX.Y.Z`.
4. Run `pnpm release`. It checks the tree is clean, runs the tests, the lint, and the
   version check that `release.yml` will repeat, pushes the branch, then tags `vX.Y.Z` and
   pushes the tag. The tag triggers `release.yml`, which builds the package and publishes it
   to PyPI.

If `release.yml` fails after the tag is pushed, delete the tag with `git tag -d vX.Y.Z` and
`git push origin :refs/tags/vX.Y.Z`, fix the problem, commit, and run `pnpm release` again.

## After publishing

- Update the Homebrew formula: set the new `url` and `sha256` from the published sdist in
  `packaging/homebrew/deslopper.rb` (the source of truth), then copy it into the tap as
  `Formula/deslopper.rb`, by hand or with `brew bump-formula-pr`.
- Move consumers off the git ref. In a repo that pins `uvx --from git+...@main`, change it to
  `uvx deslopper@X.Y.Z`.
