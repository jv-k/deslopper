# vhs tape — records a real deslopper run in three scenes: the lint view of a
# sloppy file, a live `lint --jev` run with Jev's rating on each place, then the
# clean run after a rewrite. Needs gum and AI_GATEWAY_API_KEY.
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
# Snug around the tallest scene, the --jev view: re-render and trim or grow
# after changing the demo content.
Set Height 800
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
# The scenes are mostly still frames; 12 fps keeps the typing smooth and the GIF
# small. vhs records at 50 fps by default.
Set Framerate 12

# Seed the sandbox off-camera: a notes file with four tells. The repo's .venv
# build wins over any older deslopper on PATH.
Hide
# PATH, not `activate`, which would change the prompt on camera.
Type '[ -x .venv/bin/deslopper ] && export PATH="$PWD/.venv/bin:$PATH"' Enter
# One prompt everywhere, so a local recording matches CI's.
Type "PROMPT='%F{#AB9DF2}>%f '" Enter
Type 'SBX=$(mktemp -d) && cd "$SBX"' Enter
# >| beats a NO_CLOBBER interactive zsh.
Type `printf "# Notes\n\nOur seamless platform ships fast — really.\n\nIt leverages a cache; builds fly.\n" >| notes.md` Enter
Type "clear" Enter
Show

# Scene 1: the lint view, each tell once with a caret under the caught words.
Type "deslopper lint notes.md"
Sleep 600ms
Enter
Sleep 6s

# Scene 2: ask Jev which places to rewrite. The spinner shows while it reads.
Hide
Type "clear" Enter
Show
Type "deslopper lint --jev notes.md"
Sleep 600ms
Enter
# Wait for Jev's totals line, which closes the view, then hold it. The gateway can
# take up to 10 seconds, so a fixed sleep could hide the scene before the ratings.
Wait+Screen@20s /Jev \d+ rewrite/
Sleep 5s

# Scene 3: rewrite the file off-camera, then lint it clean.
Hide
Type `printf "# Notes\n\nOur platform ships in under a minute.\n\nIt reuses a cache, so builds take 20 seconds.\n" >| notes.md` Enter
Type "clear" Enter
Show

Type "deslopper lint notes.md"
Sleep 600ms
Enter
# Hold the ✔ frame so it reads comfortably, then save it as a still. The
# trailing Sleep keeps the clean frame on screen while the Screenshot flushes.
Sleep 4s
Screenshot img/deslopper-demo-final.png
Sleep 1s

# Tear down the throwaway dir off-camera.
Hide
Sleep 500ms
# `command rm`: interactive zsh may alias rm to trash.
Type 'cd - >/dev/null && command rm -rf "$SBX"' Enter
