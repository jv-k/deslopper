# vhs tape — records a real deslopper lint over a sloppy file: findings,
# then the ✖ summary, then the clean ✔ run after a rewrite.
# Run with: vhs scripts/demo.tape   (or: pnpm screenshots:demo)
#
# The sandbox is a throwaway temp dir seeded off-camera; the recording shows
# only clean `deslopper …` commands. The finished ✔ frame is also saved as a
# still (img/deslopper-demo-final.png) via the Screenshot directive.

Output img/deslopper-demo.gif

Set Shell "zsh"
Set FontFamily "JetBrains Mono"
Set FontSize 15
Set Width 1000
# Snug around the findings frame (command + five findings, some wrapped, +
# summary): re-render and trim/grow after changing the demo content.
Set Height 420
# Monokai Pro palette with a Carbon (#191816) background for the terminal itself.
Set Theme { "background": "#191816", "foreground": "#FCFCFA", "cursor": "#FCFCFA", "black": "#2D2A2E", "red": "#FF6188", "green": "#A9DC76", "yellow": "#FFD866", "blue": "#FC9867", "magenta": "#AB9DF2", "cyan": "#78DCE8", "white": "#FCFCFA", "brightBlack": "#727072", "brightRed": "#FF6188", "brightGreen": "#A9DC76", "brightYellow": "#FFD866", "brightBlue": "#FC9867", "brightMagenta": "#AB9DF2", "brightCyan": "#78DCE8", "brightWhite": "#FCFCFA", "selection": "#5B595C" }
Set Padding 24
Set Margin 20
Set MarginFill ""
Set BorderRadius 10
Set WindowBar Colorful
Set WindowBarSize 40
Set TypingSpeed 45ms
Set PlaybackSpeed 1.0

# Seed the sandbox off-camera: a notes file thick with tells.
Hide
Type 'command -v deslopper >/dev/null || source .venv/bin/activate' Enter
Type 'SBX=$(mktemp -d) && cd "$SBX"' Enter
# >| beats a NO_CLOBBER interactive zsh; double quotes survive the apostrophe.
Type `printf "# Notes\n\nIn today's fast-paced world, our cutting-edge platform delivers value — seamlessly.\n\nIt is not just a linter; it is a game-changer.\n" >| notes.md` Enter
Type "clear" Enter
Show

# The demo: lint the sloppy file, read the findings, fix it, lint clean.
Type "deslopper lint notes.md"
Sleep 600ms
Enter
Sleep 5s

Hide
Type `printf "# Notes\n\nThe platform handles slop detection quickly.\n\nIt lints prose for machine-generated tics.\n" >| notes.md` Enter
Type "clear" Enter
Show

Type "deslopper lint notes.md"
Sleep 600ms
Enter
# Hold the ✔ frame so it reads comfortably, then save it as a still. The
# trailing Sleep keeps the clean frame on screen while the Screenshot flushes.
Sleep 5s
Screenshot img/deslopper-demo-final.png
Sleep 1s

# Tear down the throwaway dir off-camera.
Hide
Sleep 500ms
# `command rm`: interactive zsh may alias rm to trash.
Type 'cd - >/dev/null && command rm -rf "$SBX"' Enter
