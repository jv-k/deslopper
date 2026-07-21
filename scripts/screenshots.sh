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

# render_help — the help screenshot's height depends on how many lines the
# help renders, which changes as commands and options are added. Measure the
# real output and rewrite the tape's fallback Height so the window always
# wraps the content snugly: rows (help + typed command + trailing prompt) x
# 21px cells at FontSize 15, plus window bar (40) + padding (24) + slack.
# COLUMNS=108 matches the tape's 1000px width at FontSize 15, so wrapping in
# the measurement matches wrapping in the frame.
render_help() {
  local dsl="deslopper"
  [ -x .venv/bin/deslopper ] && dsl=".venv/bin/deslopper"
  local rows height
  rows=$(( $(COLUMNS=108 "$dsl" --help | wc -l | tr -d ' ') + 2 ))
  height=$(( rows * 21 + 70 ))
  sed "s/^Set Height .*/Set Height ${height}/" scripts/help.tape > img/tmp/help.tape
  vhs img/tmp/help.tape
}

target="${1:-all}"
case "$target" in
  help)
    clean img/screenshot.png img/tmp/help.gif
    render_help
  ;;
  demo)
    clean img/deslopper-demo.gif img/deslopper-demo-final.png
    vhs scripts/demo.tape
  ;;
  all)
    clean img/screenshot.png img/deslopper-demo.gif \
          img/deslopper-demo-final.png img/tmp/help.gif
    render_help
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
