# Configure deslopper

`deslopper init` writes a `deslopper.config.json`. Edit it to tune the tells and the files
to lint:

```json
{
  "extends": ["deslopper:recommended"],
  "files": {
    "include": ["**/*.md", "**/*.markdown", "**/*.mdx"],
    "exclude": ["CHANGELOG.md"]
  },
  "tells": {
    "disable": ["semicolon"],
    "override": { "filler-verb": { "tier": "error" } },
    "add": [
      { "name": "no-foo", "tier": "warn", "kind": "regex", "pattern": "foo", "message": "no foo" }
    ]
  }
}
```

| Key | What it does |
| --- | --- |
| `extends` | The presets to build on, written as `deslopper:<name>`. `recommended` is the default. |
| `files.include` | The globs to lint when you give no paths. |
| `files.exclude` | The globs to skip when you give no paths. |
| `tells.disable` | The tells to turn off. |
| `tells.override` | Changes to the fields of existing tells. |
| `tells.add` | New tells. |

The [config schema](../src/deslopper/schema/config.schema.json) describes the whole file.
Run `deslopper rules` to list the tells that your config makes active.

## Which files a run lints

With no paths, deslopper lints the Markdown and MDX files that match `files.include` and
not `files.exclude`. In a git work tree it finds them with `git ls-files`. Outside a work
tree it walks the file system.

A folder path, such as `docs/`, lints the same files that a bare run would lint inside
that folder. A file path lints that file as given, even when the config excludes it.

## The fields of a tell

| Field | Values | What it does |
| --- | --- | --- |
| `tier` | `error`, `warn` | An `error` fails the run. A `warn` fails only with `--strict`. |
| `phase` | `pre-entity`, `post-entity` | When the tell scans, relative to HTML-entity masking. Only a `pre-entity` tell can catch a tell written as an entity. |
| `scope` | `all`, `first` | `all` reports every match on a line. `first` stops after one. |
| `kind` | `regex`, `bold-bullet`, `id-label` | The matcher. `regex` is the default. The other two kinds read the capture groups of their pattern. |
| `pattern` | a regex | The match, as one regex. |
| `words` | a list of regex fragments | The match, as fragments joined into one alternation with word boundaries. |

A `words` entry is regex, not literal text. For example, `utili[sz]es?` matches
`utilise`, `utilizes`, and the other spellings.

A tell is keyed by its name and its phase. Two tells can share a name in different phases,
as the entity and literal forms of `em-dash` do. To target one of them, write
`name@phase`, for example `em-dash@pre-entity`.

## What the tells skip

Before the tells scan a file, deslopper masks fenced code, inline code, front matter, and
HTML entities. No tell fires inside them.

To keep an intentional example in prose, exempt it with an HTML comment. Put this on the
line to skip:

```markdown
<!-- deslop-lint-disable-line -->
```

To skip a block, wrap it:

```markdown
<!-- deslop-lint-disable -->
...
<!-- deslop-lint-enable -->
```

## Write a preset

A preset is a `<name>.json` file in `src/deslopper/presets/`, and a config opts into it as
`deslopper:<name>`. See [CONTRIBUTING.md](../CONTRIBUTING.md).
