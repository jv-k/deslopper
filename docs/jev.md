# Triage findings with Jev

A regex cannot tell a decorative em dash from one inside a quoted title. It also cannot
tell `delve` the filler verb from Delve the debugger. So on a repo with real prose, the
warn tier fills up with findings that a careful editor would keep.

`deslopper lint --jev` runs the normal scan first. Then it sends each flagged line, with
the line above and below it, to [Jev](https://vercel.com/ai-gateway/models/jev)
(`typesafe-ai/jev`) through the [Vercel AI Gateway](https://vercel.com/docs/ai-gateway).
Jev is a decision model, not a text generator. For each finding it answers one question:
is this a machine-writing habit to rewrite, or a deliberate use to keep? Each finding comes
back with a `keep` or `rewrite` verdict and a calibrated probability.

## Set up

Export your gateway key, then add `--jev`:

```sh
export AI_GATEWAY_API_KEY=...
deslopper lint --jev
```

Without the key, `--jev` exits 2 with a one-line hint and prints no findings.

## Read the output

On a terminal with [gum](https://github.com/charmbracelet/gum), a tool from Charm that
draws styled output in a terminal, a spinner names each file while Jev reads it, and each place then
starts with Jev's rating:

```text
  ✖ em-dash
    em dash in prose, use a colon, comma, parentheses, or two sentences
      ❚❚❚❚❚ 0.76 keep     3:20  The fix was simple — restart the server.
                                                   ^

  ! filler-verb
    filler verb, use a plain verb or cut
      ❚❚❚❚❚ 0.87 rewrite   5:6  This leverages the cache; it is fast.
                                     ^

  ──────────────────────────────────────────────────────────────────────────────────
  ✖ 1 error   ! 2 warnings

  ╭──────────┬─────────────────────────────────────────────────────────────────────╮
  │ summary  │                                                                     │
  ├──────────┼─────────────────────────────────────────────────────────────────────┤
  │ findings │ 3 in 1 file                                                         │
  │ errors   │ 1                                                                   │
  │ warnings │ 2                                                                   │
  │ rewrite  │ 1                                                                   │
  │ keep     │ 2                                                                   │
  ╰──────────┴─────────────────────────────────────────────────────────────────────╯
  ╭─────────────┬─────────────────────┬─────────────────────┬──────────────────────╮
  │ Jev         │ verdicts            │ tokens              │ cost                 │
  ├─────────────┼─────────────────────┼─────────────────────┼──────────────────────┤
  │ this run    │ 3                   │ 872                 │ $0.000033            │
  │ cache saved │ 0                   │ 0                   │ $0                   │
  ╰─────────────┴─────────────────────┴─────────────────────┴──────────────────────╯
```

The bar fills in proportion to the probability. Its filled slots are green from 0.9,
yellow from 0.7, and red below that. On a narrow terminal the rating drops the number and
keeps the bar and the verdict.

Two tables close the view, as wide as the rules above them. The summary table counts the
findings and Jev's verdicts. The Jev table has one row for the verdicts asked for on this
run, with their tokens and cost, and one row for the verdicts the cache answered, with what
they cost when Jev first gave them. The tables round each cost to two significant figures.
The `json` format keeps the exact cost.

The other formats carry the verdict too:

- Piped output adds the verdict to the end of each line, such as `[rewrite 0.87]`. The
  plain summary line counts the `keep` and `rewrite` verdicts, and reports the tokens and
  the gateway cost of the run.
- The `json` format adds `verdict` and `probability` to each judged finding, and a `jev`
  key with the totals. See [Output formats](output.md#json).
- The `github` format puts the verdict in the annotation message.

## The cache

deslopper keeps each verdict in a cache on disk, in `$XDG_CACHE_HOME/deslopper/jev`, or
`~/.cache/deslopper/jev` when that variable is not set. A later run uses the cached verdict
while the tell, its column, and the lines around the finding stay the same. A finding that
only moved down the file is not sent again. A file whose findings are all cached sends no
request.

Each cached verdict also keeps its share of the tokens and the cost of the request that
answered it. The `cache saved` row of the Jev table counts the cached verdicts and adds up
those tokens and that cost. The plain summary line ends with the same saving, and the
`json` format reports `cached`, `saved_tokens`, and `saved_cost`.

Add `--no-cache` to ask Jev about every finding again, for example after Jev changes. To
clear the cache, delete the folder.

## Limits

Triage only adds notes. It never changes the exit code, so a `keep` verdict cannot make a
lint pass, and the gate holds in CI. Some other limits apply:

- deslopper never sends findings on a disabled line.
- A file with no findings sends no request. A file with findings sends one request at
  most.
- `--jev` is a command-line flag only, never a config key. So no repo can turn on network
  calls for everyone who lints it.
- `check` does not accept `--jev`.

If a request fails, deslopper prints one error line to stderr, leaves the findings of that
file without verdicts, and exits with the code of the scan. With `--format json`, the error
goes into the payload instead.

## Send only the findings that need a rewrite

On a large backlog, ask Jev first, so that an LLM rewrites only the findings that need it.
This command keeps the findings that Jev did not mark `keep`:

```sh
deslopper lint --jev --format json docs/ | jq '[.findings[] | select(.verdict != "keep")]'
```
