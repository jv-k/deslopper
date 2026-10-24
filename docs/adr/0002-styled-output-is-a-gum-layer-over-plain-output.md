# Styled output is a gum layer over the plain output

deslopper's plain output is a contract. Editors and scripts read the
`path:line:col [tier] tell: message` lines, CI reads the `github` annotations, models read
the `json` payload, and golden files pin the text. The terminal view had grown its own
styling in `ui.py` and `report.py`: hand-written escapes, a colour gate, and a second
layout of the same findings.

We draw the terminal view with [gum](https://github.com/charmbracelet/gum) instead, the
same way the engineering-playbook's ship scripts do (its ADR 0006). The rules:

- The plain output is the only renderer that every run can reach. It never changes for
  gum.
- A run is attended when gum is on `PATH` and either stdout is a terminal with `NO_COLOR`
  unset, or `CLICOLOR_FORCE` is set to something other than 0. These are the variables
  gum reads. `FORCE_COLOR` does not count, because gum ignores it.
- On an attended run, deslopper builds the view as data, lines of (style, text) parts,
  and gum draws the whole of it, header to totals, in one `gum format --type template`
  call. The Jev wait goes through `gum spin`. `gum.py` makes every gum call and owns the
  palette.
- On a terminal without gum, deslopper prints the plain output and one line that names
  the install. gum is never a dependency.
- The `github` and `json` formats never call gum.
- The tests never run a real gum. A shim on `PATH` records each call.

We picked this over keeping the hand-written styling, and over a fallback that draws the
same view without gum. Either keeps two renderers of one output that drift apart.

We tried `gum table` for the findings first and dropped it. A table needs a wide
terminal, breaks in a narrow one, and has no room for the rating bar. We then compared
several list layouts as screenshots, and chose the one that groups by tell: a section per
file, each tell once with its fix, then every place it fired, with the line, the caught
words highlighted, a caret under them, and Jev's rating first. It repeats the least, and
on a narrow terminal it cuts each line around the caught words instead of wrapping.

The costs: each gum call starts a process, about 20 ms, so a view makes one call for all
its lines, never one per finding. `gum spin` wraps a command, so a
spinner around Python work wraps a command that waits, and that command must end when gum
does, or it outlives deslopper and holds the terminal or a pipe open.
