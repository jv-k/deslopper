#!/usr/bin/env bash
#
# scripts/screenshots.sh — regenerate img/screenshot.png and img/deslopper-demo.gif
# (plus its final-frame still img/deslopper-demo-final.png) via vhs, and the README's
# wordmark, img/wordmark-dark.png and img/wordmark-light.png, via rsvg-convert.
#
# Usage:
#   ./scripts/screenshots.sh            # all of them
#   ./scripts/screenshots.sh help       # just the --help PNG
#   ./scripts/screenshots.sh demo       # just the lint-run GIF
#   ./scripts/screenshots.sh wordmark   # just the README's wordmark PNGs
#
# Requires: vhs (https://github.com/charmbracelet/vhs) and rsvg-convert (librsvg).
# Install: brew install vhs librsvg

set -eo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

target="${1:-all}"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "screenshots: $1 not found on PATH. Install with: brew install $2" >&2
    exit 127
  fi
}
[ "$target" = wordmark ] || need vhs vhs
case "$target" in wordmark|all) need rsvg-convert librsvg ;; esac

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

# render_wordmark — the README's wordmark, from the CLI's rows, in the CLI's gradient:
# one picture for a dark page and one, in darker stops, for a light page.
render_wordmark() {
  local py="python3"
  [ -x .venv/bin/python ] && py=".venv/bin/python"
  local variant
  for variant in dark light; do
    "$py" scripts/wordmark.py "$variant" | rsvg-convert -o "img/wordmark-$variant.png"
  done
}

case "$target" in
  wordmark)
    render_wordmark
  ;;
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
    render_wordmark
    render_help
    vhs scripts/demo.tape
  ;;
  *)
    echo "screenshots: unknown target '$target'" >&2
    echo "  expected: help | demo | wordmark | all" >&2
    exit 2
  ;;
esac

# vhs' `Output` directive always produces a gif even when we only care about
# the `Screenshot` frame — for help.tape that throwaway gif lands in img/tmp/.
echo "screenshots: wrote -> img/ (discarded intermediate gifs in img/tmp/)"
