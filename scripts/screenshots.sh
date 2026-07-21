#!/usr/bin/env bash
#
# scripts/screenshots.sh — regenerate img/screenshot.png and img/deslopper-demo.gif
# (plus its final-frame still img/deslopper-demo-final.png) via vhs.
#
# Usage:
#   ./scripts/screenshots.sh           # both
#   ./scripts/screenshots.sh help      # just the --help PNG
#   ./scripts/screenshots.sh demo      # just the lint-run GIF
#
# Requires: vhs (https://github.com/charmbracelet/vhs).  Install: brew install vhs

set -eo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v vhs >/dev/null 2>&1; then
  echo "screenshots: vhs not found on PATH. Install with: brew install vhs" >&2
  exit 127
fi

mkdir -p img img/tmp

# Remove stale outputs so vhs can overwrite cleanly. Notably, earlier runs
# of vhs on `Output *.png` produced a *directory* of frames at that path —
# if one is still around, vhs can't write a plain file there. Nuke both
# possible shapes (file or dir) before re-rendering.
clean() {
  local p
  for p in "$@"; do rm -rf -- "$p"; done
}

target="${1:-all}"
case "$target" in
  help)
    clean img/screenshot.png img/tmp/help.gif
    vhs scripts/help.tape
  ;;
  demo)
    clean img/deslopper-demo.gif img/deslopper-demo-final.png
    vhs scripts/demo.tape
  ;;
  all)
    clean img/screenshot.png img/deslopper-demo.gif \
          img/deslopper-demo-final.png img/tmp/help.gif
    vhs scripts/help.tape
    vhs scripts/demo.tape
  ;;
  *)
    echo "screenshots: unknown target '$target'" >&2
    echo "  expected: help | demo | all" >&2
    exit 2
  ;;
esac

# vhs' `Output` directive always produces a gif even when we only care about
# the `Screenshot` frame — for help.tape that throwaway gif lands in img/tmp/.
echo "screenshots: wrote -> img/ (discarded intermediate gifs in img/tmp/)"
