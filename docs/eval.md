# Eval a rewrite pass

The linter finds slop. To clear a backlog, you need a rewrite, which is a model pass. An
LLM rewrite can remove the tells and still damage the document. `deslopper eval` tests
whether your rewrite works before you run it on real files:

1. It puts sample files that trip every tell in the `recommended` and `aggressive` presets
   into a temporary folder.
2. It runs your rewrite command over the folder.
3. It judges the result.

Give the command with `{dir}` where the folder path goes. If you leave out `{dir}`,
deslopper adds the path at the end:

```sh
deslopper eval 'my-rewrite {dir}'
deslopper eval ./scripts/deslop.sh
```

## The judges

Two judges decide the result:

- Efficacy lints the rewritten files. It needs zero error-tier findings. The warn count
  must also fall below the count before the rewrite. This gives the model some room, but it
  cannot leave the warnings as they were.
- Preservation compares the protected content before and after the rewrite. That is
  fenced code and front matter, exactly, plus the heading outline, the table rows, and the
  link targets. Any difference fails the run.

Before the rewrite, deslopper also lints the raw sample files as a self-check. If they give
no errors, the harness is broken, and the run stops before it spends tokens.

| Exit code | Meaning |
| --- | --- |
| 0 | Pass |
| 1 | Efficacy failure |
| 2 | A usage or configuration error |
| 3 | Preservation failure |
| 4 | A broken harness, or a rewrite command that exited nonzero |

A failure names the remaining findings by file and line. To keep the temporary folder for
inspection, add `--keep`.

## Score plainness with Jev

`--plainness` adds a third judge. It asks [Jev](jev.md) to score how plainly each sample
file reads. It scores the files once before the rewrite and once after, and prints one
`before -> after` line per file plus the mean.

The score is only a report. It never changes the verdict or the exit code. So you can
compare two eval runs on more than pass or fail, and a probabilistic judge cannot fail a
run that the deterministic judges passed.

`--plainness` needs `AI_GATEWAY_API_KEY`. Without it, the eval exits 2 before the rewrite
command runs. The two requests send the sample files whole. A run costs about a thousand
input tokens and a fraction of a cent, and the mean line reports the cost. If the gateway
fails, deslopper prints one error line and finishes with the two deterministic judges.

## When to run it

An eval runs your rewrite command for real, so it spends real minutes and tokens. Run it
when you change the rewrite prompt or model. Do not run it as a gate on each commit or pull
request.
