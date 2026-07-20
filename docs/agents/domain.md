# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring
the codebase.

deslopper is **single-context**: one `CONTEXT.md` and one `docs/adr/`, both at the repo
root.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists. It points at one `CONTEXT.md` per
  context. Read each one relevant to the topic.
- **`docs/adr/`** for the ADRs that touch the area you are about to work in. In
  multi-context repos, also check `src/<context>/docs/adr/` for context-scoped decisions.

If any of these files do not exist, **proceed silently**. Do not flag their absence, and do
not suggest creating them upfront. The `/domain-modeling` skill (reached via
`/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily, when terms or
decisions actually get resolved.

## File structure

Single-context repo, which is most repos and this one:

```
/
├── CONTEXT.md
├── docs/adr/
│   └── 0001-words-are-regex.md
└── src/
```

Multi-context repo, marked by a `CONTEXT-MAP.md` at the root:

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          system-wide decisions
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  context-specific decisions
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## Use the glossary's vocabulary

When your output names a domain concept (an issue title, a refactor proposal, a hypothesis,
a test name), use the term as defined in `CONTEXT.md`. Do not drift to the synonyms the
glossary marks as ones to avoid.

If the concept you need is not in the glossary yet, that is a signal. Either you are
inventing language the project does not use, in which case reconsider, or there is a real
gap, in which case note it for `/domain-modeling`.

## Flag ADR conflicts

If your output contradicts an existing ADR, say so explicitly rather than overriding it
quietly:

> _Contradicts ADR-0001 (a tell's words are regex), but worth reopening because..._
