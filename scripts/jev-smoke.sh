#!/usr/bin/env bash
# A live Jev run over the slop fixture, which must come back with a verdict on every
# smell. The suite fakes the gateway, so this is where the real integration is proved:
# before a release (preflight.sh) and before the demo GIF records Jev (screenshots.yml).
#
#   bash scripts/jev-smoke.sh [python]      default: python3
#
# A gateway failure keeps lint's exit code by design, so the exit code proves nothing
# here. The check that matters is that every smell came back judged.
set -euo pipefail
py="${1:-python3}"
cd "$(dirname "$0")/.."
if [ -z "${AI_GATEWAY_API_KEY:-}" ]; then
  echo "jev smoke run: AI_GATEWAY_API_KEY is not set" >&2
  exit 1
fi
judged="$(mktemp)"
trap 'rm -f "$judged"' EXIT
# Exit 1 means smells, which is the point; anything else is a usage or key error.
# --no-cache: cached verdicts would let the check pass without reaching the gateway.
"$py" -m deslopper lint --jev --no-cache --format json tests/fixtures/ai_slop.md >"$judged" || [ $? -eq 1 ]
"$py" - "$judged" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
smells = payload["smells"]
unjudged = [f for f in smells if "verdict" not in f]
if not smells or unjudged:
    errors = payload.get("jev", {}).get("errors", [])
    sys.exit(f"jev smoke run: {len(unjudged)} of {len(smells)} smells came back unjudged"
             + "".join(f"\n  {e}" for e in errors))
print(f"jev smoke run: {len(smells)} smells judged")
PY
