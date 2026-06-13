# Changelog

## 0.1.0 (unreleased)

- The deterministic lint core, ported byte-for-byte from the engineering-playbook scripts.
- The bundled `recommended` rule set (twelve tells, error and warn tiers).
- `deslopper.config.json` with `extends`, `tells.add`, `tells.override`, `tells.disable`,
  `strict`, and `files`, keyed by (name, phase).
- Commands: `lint`, `check`, `rules`, `init`.
- Output formats: text, github, json. Exit codes 0, 1, 2.
