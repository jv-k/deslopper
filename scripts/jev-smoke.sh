#!/usr/bin/env bash
# A live Jev run over the slop fixture, which must come back with a verdict on every
# finding. The suite fakes the gateway, so this is where the real integration is proved:
# before a release (preflight.sh) and before the demo GIF records Jev (screenshots.yml).
#
#   bash scripts/jev-smoke.sh [python]      default: python3
#
# A gateway failure keeps lint's exit code by design, so the exit code proves nothing
# here. The check that matters is that every finding came back judged.
set -euo pipefail
py="${1:-python3}"
cd "$(dirname "$0")/.."
if [ -z "${AI_GATEWAY_API_KEY:-}" ]; then
  echo "jev smoke run: AI_GATEWAY_API_KEY is not set" >&2
  exit 1
fi
judged="$(mktemp)"
trap 'rm -f "$judged"' EXIT
# Exit 1 means findings, which is the point; anything else is a usage or key error.
"$py" -m deslopper lint --jev --format json tests/fixtures/ai_slop.md >"$judged" || [ $? -eq 1 ]
"$py" - "$judged" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
findings = payload["findings"]
unjudged = [f for f in findings if "verdict" not in f]
if not findings or unjudged:
    errors = payload.get("jev", {}).get("errors", [])
    sys.exit(f"jev smoke run: {len(unjudged)} of {len(findings)} findings came back unjudged"
             + "".join(f"\n  {e}" for e in errors))
print(f"jev smoke run: {len(findings)} findings judged")
PY
