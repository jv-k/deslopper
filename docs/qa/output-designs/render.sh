#!/usr/bin/env bash
# Render each design to a PNG with vhs: a real terminal, so the colours are true.
# The designs read the terminal's own width, so a line never wraps by accident.
#   bash render.sh [design...]     default: 1 2 5 8
set -uo pipefail
cd "$(dirname "$0")"
mkdir -p png
shot() { # <design> <flags> <width px> <name>
  local tape
  tape="$(mktemp -t design).tape"
  cat > "$tape" <<TAPE
Output png/.scratch.gif
Set Shell bash
Set FontSize 14
Set Width $3
Set Height ${HEIGHT:-1500}
Set Padding 20
Set Theme "Catppuccin Mocha"
Hide
Type "export PS1='' COLUMNS=\$(tput cols) && clear"
Enter
Show
Type "python3 designs.py $1 $2"
Enter
Sleep 2s
Screenshot png/$4.png
TAPE
  # vhs sometimes exits without writing the screenshot, so retry a few times.
  local try
  for try in 1 2 3; do
    [[ -f "png/$4.png" ]] && break
    vhs "$tape" > /dev/null 2>&1 || true
  done
  [[ -f "png/$4.png" ]] || echo "vhs gave no screenshot for $4" >&2
  rm -f "$tape"
}
for n in "${@:-1 2 5 8}"; do
  for d in $n; do
    shot "$d" --jev 1000 "design-$d-jev"
    shot "$d" ""    1000 "design-$d"
    shot "$d" --jev 600  "design-$d-jev-narrow"
  done
done
ls png
