#!/usr/bin/env bash
# Try every design on a real run: lint once, then draw the same findings each way.
#
#   bash docs/qa/output-designs/try.sh [lint args...]        e.g.  --jev README.md docs/
#   DESIGN=5 bash docs/qa/output-designs/try.sh [lint args...]   one design only
#
# It uses the repo's .venv build when there is one, else the deslopper on PATH.
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
deslopper="$here/../../../.venv/bin/deslopper"
[[ -x "$deslopper" ]] || deslopper=deslopper
names=([1]="Ledger" [2]="Snippet" [5]="Tell first" [8]="Tell first, with a caret")
run="$(mktemp -t deslopper-run)"
trap 'rm -f "$run"' EXIT
"$deslopper" lint --format json "$@" > "$run"
status=$?
if (( status > 1 )); then exit "$status"; fi
for n in ${DESIGN:-1 2 5 8}; do
  if [[ -z "${DESIGN:-}" ]]; then
    printf '\n\033[1;38;5;111m━━━━━━━━ design %s: %s ━━━━━━━━\033[0m\n' "$n" "${names[$n]}"
  fi
  python3 "$here/designs.py" "$n" --from "$run"
done
