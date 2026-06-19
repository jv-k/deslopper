# Changelog

## 0.1.0 (unreleased)

- The deterministic lint core, ported byte-for-byte from the engineering-playbook scripts.
- The bundled `recommended` rule set (twelve tells, error and warn tiers).
- `deslopper.config.json` with `extends`, `tells.add`, `tells.override`, `tells.disable`,
  `strict`, and `files`, keyed by (name, phase).
- Commands: `lint`, `check`, `rules`, `init`.
- Output formats: text, github, json. Exit codes 0, 1, 2.
- Built-in presets are flat `<name>.json` files in `src/deslopper/presets/`. `extends`
  accepts multiple built-in presets, resolved left to right.
- Community infra: a contributing guide, issue and PR templates, a labeler, and commit and
  PR title linting.
- File discovery and the scanner now cover `.mdx`. Top-level ESM `import` and `export` lines
  are skipped. JSX that wraps prose is still linted.
