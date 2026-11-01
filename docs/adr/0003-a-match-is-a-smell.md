# A match is a smell

deslopper reports one place where a tell matched, at a path, line, and column. Until 2.0.0
the code, the output, and the docs called that a finding. The glossary in `CONTEXT.md`
now calls it a smell, and the code and output follow.

We chose smell for three reasons:

- A finding is a word for any result of any check. It says nothing about what deslopper
  checks for. A smell names the thing itself: prose that suggests machine writing and
  invites a closer look, the way a code smell does. It does not claim the prose is wrong.
  That fits triage, where Jev can judge a smell worth keeping and it is still a smell.
- Warning was the other candidate. It collides with the `warn` tier. A warn smell and an
  error smell are both smells, and "an error warning" would be nonsense. The summary
  already counts `warning(s)` for the warn tier.
- Match names what a regex does, not what deslopper reports. A smell is the report: a
  tell, a tier, a place, and a message.

The `json` format's `findings` key becomes `smells`. That breaks every script and model
that reads the payload, so the rename ships as a major release, 2.0.0, with a migration
note in `CHANGELOG.md`. We accept the break because the payload is the contract that
models read, and a key that uses a word the glossary tells us to avoid would keep the old
word alive in every prompt and script built on it. Keeping `findings` as an alias beside
`smells` would double the payload and leave readers to guess which key is canonical.

Two things stay as they were:

- Jev's prompt still says finding. The prompt text is part of the verdict cache key, so a
  change to it would drop every cached verdict and could shift the verdicts. Only the
  Python names around it changed.
- The comment syntax `deslop-lint-disable`, `deslop-lint-disable-line`, and
  `deslop-lint-enable` is unchanged. The prose now calls the lines it covers an exempt
  region and an exempt line, because disable now means removing a tell from the config.
