#!/usr/bin/env bash
# Assert the skills CLI discovers exactly one skill here, named deslopper, so the repo
# always ships exactly what `npx skills add jv-k/deslopper` expects to find. The listing
# output belongs to a third party, so the assertion stays loose: strip the ANSI decoration,
# then require the count line and a listing line that is exactly the skill name, nothing
# about formatting. The name must match a whole line, not the blob, because the listing
# echoes the source path and on CI that path itself contains "deslopper". Takes the repo
# root as $1 (used by the red-case checks), defaulting to the checkout this script lives
# in, resolved absolute because the CLI reads `scripts/..` as a GitHub owner/repo slug.
set -euo pipefail
root="$(cd "${1:-$(dirname "$0")/..}" && pwd)"

out="$(npx -y skills add "$root" -l 2>&1 || true)"
clean="$(printf '%s' "$out" | LC_ALL=C sed -e $'s/\x1b\\[[0-9;?]*[a-zA-Z]//g' -e $'s/[^[:print:]\t]//g')"

fail() {
  echo "$clean"
  echo "skill discovery check failed: $1" >&2
  exit 1
}

printf '%s' "$clean" | grep -Eq '^[[:space:]]*Found[[:space:]]+1[[:space:]]+skills?\b' || fail "expected exactly one discovered skill"
printf '%s' "$clean" | grep -Eq '^[[:space:]]*deslopper[[:space:]]*$' || fail "expected the discovered skill to be deslopper"
echo "skill discovery ok: found 1 skill, deslopper"
