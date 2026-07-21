# vhs tape — renders deslopper --help as a single PNG (macOS-window look).
# Run with: vhs scripts/help.tape   (or: pnpm screenshots:help)
#
# vhs emits a full animated GIF for any tape — we don't use it here, so it
# lands in img/tmp/help.gif (gitignored). The single PNG we care about comes
# from the `Screenshot` directive at the bottom.

Output img/tmp/help.gif

Set Shell "zsh"
Set FontFamily "JetBrains Mono"
Set FontSize 15
Set Width 1000
# Tall enough to hold the whole --help — wordmark through EXAMPLES — in one
# frame, and no taller. vhs' Screenshot captures the viewport, so a short
# height scrolls the typed command + wordmark off the top, and extra rows
# render as blank background at the bottom. After editing the help text,
# re-render and trim/grow this until the frame is snug.
Set Height 850
# Monokai Pro palette with a Carbon (#191816) background for the terminal itself.
Set Theme { "background": "#191816", "foreground": "#FCFCFA", "cursor": "#FCFCFA", "black": "#2D2A2E", "red": "#FF6188", "green": "#A9DC76", "yellow": "#FFD866", "blue": "#FC9867", "magenta": "#AB9DF2", "cyan": "#78DCE8", "white": "#FCFCFA", "brightBlack": "#727072", "brightRed": "#FF6188", "brightGreen": "#A9DC76", "brightYellow": "#FFD866", "brightBlue": "#FC9867", "brightMagenta": "#AB9DF2", "brightCyan": "#78DCE8", "brightWhite": "#FCFCFA", "selection": "#5B595C" }
Set Padding 12
Set Margin 8
Set MarginFill ""
Set BorderRadius 10
Set WindowBar Colorful
Set WindowBarSize 40
Set TypingSpeed 40ms

Hide
# Put the installed command on PATH so the screenshot shows plain
# `deslopper`, not a repo path. Clear AFTER so the setup line never
# lingers on screen when we Show.
Type 'command -v deslopper >/dev/null || source .venv/bin/activate' Enter
Type "clear" Enter
Show

Type "deslopper --help"
Sleep 400ms
Enter
Sleep 2s

Screenshot img/screenshot.png
# The trailing Sleep keeps the frame on screen while the Screenshot flushes —
# without it vhs sometimes exits before writing the PNG.
Sleep 1s
