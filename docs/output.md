# Output formats

`deslopper lint` and `deslopper check` write findings in one of three formats. Choose one
with `--format text|github|json`. The default is `text`.

## `text`

On a terminal with [gum](https://github.com/charmbracelet/gum) installed, deslopper draws
its output with gum, a tool from Charm that draws styled output in a terminal. It gives
each file a section. Inside it, each tell appears once with its fix, then every place it
fired: the line and column, the line itself with the caught words highlighted, and a caret
under them. A `--jev` run adds a spinner while Jev reads each file. The view ends with the
totals.

On a narrow terminal, the line is cut around the caught words, so nothing wraps.

Without gum, and whenever the output is piped, deslopper prints one line per finding, for
editors and scripts:

```text
path:line:col [tier] tell: message
```

The help screens, the eval report, and the status lines also go through gum. `NO_COLOR`
turns the gum output off. `CLICOLOR_FORCE=1` turns it on without a terminal. These are the
two variables that gum itself reads.

## `github`

The `github` format writes each finding as a GitHub Actions annotation, so the finding
shows on the pull request. It never calls gum.

## `json`

The `json` format is for tools and for models. It prints one JSON object to stdout and
nothing to stderr, so the payload is the whole output. Only a usage error, such as a
missing gateway key, prints one line to stderr and exits 2.

```json
{
  "findings": [
    {
      "path": "docs/guide.md",
      "line": 6,
      "col": 27,
      "tier": "warn",
      "name": "semicolon",
      "message": "semicolon in prose, prefer a full stop"
    }
  ],
  "unreadable": [],
  "summary": { "errors": 0, "warnings": 1, "unreadable": 0 }
}
```

With `--jev`, each judged finding also has `verdict` and `probability`, and the object has
a `jev` key with the totals of the run. Its `errors` list has one line for each Jev request
that failed:

```json
"jev": { "keep": 2, "rewrite": 1, "cached": 0, "saved_tokens": 0, "saved_cost": "0",
         "tokens": 872, "cost": "0.000032844", "errors": [] }
```

The package ships a JSON Schema for each side of the contract:
[output.schema.json](../src/deslopper/schema/output.schema.json) for this object, and
[config.schema.json](../src/deslopper/schema/config.schema.json) for the config file.
