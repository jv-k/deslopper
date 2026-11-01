# Triage smells with Jev

A regex cannot tell a decorative em dash from one inside a quoted title. It also cannot
tell `delve` the filler verb from Delve the debugger. So on a repo with real prose, the
warn tier fills up with smells that a careful editor would keep.

`deslopper lint --jev` runs the normal scan first. Then it sends each flagged line, with
the line above and below it, to [Jev](https://vercel.com/ai-gateway/models/jev)
(`typesafe-ai/jev`) through the [Vercel AI Gateway](https://vercel.com/docs/ai-gateway).
Jev is a decision model, not a text generator. For each smell it answers one question:
is this a machine-writing habit to rewrite, or a deliberate use to keep? Each smell comes
back with a `keep` or `rewrite` verdict and a calibrated probability.

## Set up

Export your gateway key, then add `--jev`:

```sh
export AI_GATEWAY_API_KEY=...
deslopper lint --jev
```

Without the key, `--jev` exits 2 with a one-line hint and prints no smells.

## Read the output

On a terminal with [gum](https://github.com/charmbracelet/gum), a tool from Charm that
draws styled output in a terminal, a spinner shows each request while Jev reads it, and each place
then starts with Jev's rating:

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
  │ smells   │ 3 in 1 file                                                         │
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
smells and Jev's verdicts. The Jev table has one row for the verdicts asked for on this
run, with their tokens and cost, and one row for the verdicts the cache answered, with what
they cost when Jev first gave them. The tables round each cost to two significant figures.
The `json` format keeps the exact cost.

The other formats carry the verdict too:

- Piped output adds the verdict to the end of each line, such as `[rewrite 0.87]`. The
  plain summary line counts the `keep` and `rewrite` verdicts, and reports the tokens and
  the gateway cost of the run.
- The `json` format adds `verdict` and `probability` to each judged smell, and a `jev`
  key with the totals. See [Output formats](output.md#json).
- The `github` format puts the verdict in the annotation message.

## The cache

deslopper keeps each verdict in a cache on disk, in `$XDG_CACHE_HOME/deslopper/jev`, or
`~/.cache/deslopper/jev` when that variable is not set. A later run uses the cached verdict
while the tell, its column, and the lines around the smell stay the same. A smell that
only moved down the file is not sent again. A run whose smells are all cached sends no
request.

Each cached verdict also keeps its share of the tokens and the cost of the request that
answered it. The `cache saved` row of the Jev table counts the cached verdicts and adds up
those tokens and that cost. The plain summary line ends with the same saving, and the
`json` format reports `cached`, `saved_tokens`, and `saved_cost`.

Add `--no-cache` to ask Jev about every smell again, for example after Jev changes. To
clear the cache, delete the folder.

## Limits

Triage only adds notes. It never changes the exit code, so a `keep` verdict cannot make a
lint pass, and the gate holds in CI. Some other limits apply:

- deslopper never sends smells on an exempt line or in an exempt region.
- A clean run sends no request. deslopper packs the smells, in file order, into as few
  requests as fit in Jev's window. One request can hold smells from many files, and a
  file with many smells can span more than one request. See [Request limits](#request-limits).
- `--jev` is a command-line flag only, never a config key. So no repo can turn on network
  calls for everyone who lints it.
- `check` does not accept `--jev`.

If a request fails, deslopper prints one error line to stderr that names the first three
files in that request and counts the rest. It leaves the smells in that request without verdicts, still sends the requests
after it, and exits with the code of the scan. With `--format json`, the error
goes into the payload instead.

## Request limits

Each request carries two parts: the state, which holds each smell's lines, and one
question for each smell. deslopper closes a request before either part passes its limit.
Both limits are in characters, because the client does not count tokens:

- The state stops at 64,000 characters (`jev.STATE_CHAR_BUDGET`).
- The questions, as the JSON the client sends, stop at 110,000 characters
  (`jev.QUESTION_CHAR_BUDGET`). One triage question is about 430 characters, so a
  request holds at most about 255 smells.

These numbers come from real requests to the gateway on 2026-11-01. The probe that sent
them is `docs/qa/jev-question-budget-87/probe.py`, and its results are in `results.json`
beside it.

| What the probe measured | Result |
| --- | --- |
| Largest input Jev accepts, state and questions together | 65,536 tokens: 415 short smells passed at 65,533, 418 failed |
| Largest state Jev accepts with one question | about 32,500 tokens: 142,183 characters of prose passed, 142,964 failed |
| Characters per token, triage questions | 3.66 |
| Characters per token, short smell blocks | 2.83 |
| Characters per token, plain prose | 4.4 |
| Output tokens per question | about 31, not counted toward either limit |

A refused request fails with `max_tokens_exceeded`. Under the state limit alone, 600 short
smells packed 478 questions into the first request, past the 415 that fit.

The question limit is about 30,000 tokens. That fits beside any state Jev accepts on its
own, with about 2,500 tokens spare. In the same probe, two requests filled both limits
together:

| Request | Smells | State | Questions | Input tokens |
| --- | --- | --- | --- | --- |
| 600 short smells, first request | 256 | 43,193 | 109,756 | 51,334 |
| Lines of prose that fill the state | 247 | 63,863 | 105,886 | 52,476 |
| Lines of one repeated letter that fill the state | 247 | 63,863 | 105,886 | 60,616 |

The repeated letter is the densest state the probe found, and it still leaves about 4,900
tokens spare. A full request came back in about 1.2 seconds, well inside the 10-second
deadline.

## Send only the smells that need a rewrite

On a large backlog, ask Jev first, so that an LLM rewrites only the smells that need it.
This command keeps the smells that Jev did not mark `keep`:

```sh
deslopper lint --jev --format json docs/ | jq '[.smells[] | select(.verdict != "keep")]'
```
