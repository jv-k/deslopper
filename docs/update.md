# Update deslopper

Read the [changelog](../CHANGELOG.md) before you update. A new release can add a tell or
change a tier, so prose that passed before can fail after the update.

Check the version you have with `deslopper --version`. Then run:

```sh
deslopper update
```

The command finds the tool that installed deslopper and runs its upgrade. It knows
Homebrew, pipx, and uv. For any other install, it prints the command to run yourself and
changes nothing. Add `--dry-run` to see the command without running it.

You can also run the upgrade yourself, with the tool that installed deslopper:

| Tool | Command |
| --- | --- |
| Homebrew | `brew update && brew upgrade jv-k/tap/deslopper` |
| pipx | `pipx upgrade deslopper` |
| uv | `uv tool upgrade deslopper` |
| pip | `pip install --upgrade git+https://github.com/jv-k/deslopper` |

Run `deslopper --version` again to confirm the new version. If you are not sure which tool
installed deslopper, run `which -a deslopper`. A path under the Homebrew prefix, such as
`/opt/homebrew/bin`, is the Homebrew install.

## Setups without their own install

Some setups do not keep their own install, so they update in other ways:

- `uvx` caches the package it builds. Add `--refresh` to fetch the latest `main`:
  `uvx --refresh --from git+https://github.com/jv-k/deslopper deslopper lint`.
- A CI job that pins a release tag stays on that release. To update it, change the tag in
  the workflow to the new release. See [Use it in CI](../README.md#use-it-in-ci).
- The pre-commit hook runs the deslopper on your `PATH`, so it updates when you update the
  install.
- To update the [agent skill](../README.md#agent-skill), run `npx skills update
  deslopper`. If you copied the skill by hand, copy `skills/deslopper/` again.
