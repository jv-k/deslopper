"""Shell completion scripts for bash, zsh, and fish.

Every script renders from the help screen's command table, so a flag lands in
help and completions from one edit. The script is the only thing written, plain
and never styled: stdout here is a machine contract, like the json format.
"""

import os

from . import help as help_screen
from .errors import UsageError

SUPPORTED = ("bash", "zsh", "fish")

_HELP_ROW = ("--help", "Show this help message.")
_VERSION_ROW = ("--version", "Print the tool version and exit.")


def _supported() -> str:
    return ", ".join(SUPPORTED)


def detect() -> str:
    """The shell named by $SHELL's basename, or a usage error."""
    shell = os.path.basename(os.environ.get("SHELL", ""))
    if not shell:
        raise UsageError(
            f"cannot tell the shell from $SHELL; pass one of: {_supported()}"
        )
    if shell not in SUPPORTED:
        raise UsageError(f"unsupported shell '{shell}'; pass one of: {_supported()}")
    return shell


def script(shell: str) -> str:
    if shell not in SUPPORTED:
        raise UsageError(f"unsupported shell '{shell}'; pass one of: {_supported()}")
    return {"bash": _bash, "zsh": _zsh, "fish": _fish}[shell](_facts())


def _facts() -> dict:
    """The command table flattened to what the script templates need.

    A flag whose arg is <file> completes as a path; a flag in "choices"
    completes to its values; "paths" marks the file-path positional.
    """
    facts = {}
    for name, spec in help_screen.COMMANDS.items():
        flags, file_flags = [], []
        for _short, long, arg, desc in spec["options"]:
            flags.append((long, desc))
            if arg == "<file>":
                file_flags.append(long)
        flags.append(_HELP_ROW)
        facts[name] = {
            "description": spec["description"],
            "flags": flags,
            "file_flags": file_flags,
            "choices": spec.get("choices", {}),
            "paths": spec.get("paths", False),
            "positional": spec.get("positional_choices", ()),
        }
    return facts


# ── bash ──────────────────────────────────────────────────────────────────────


def _bash(facts) -> str:
    names = " ".join(facts)
    lines = [
        "# bash completions for deslopper. Regenerate with 'deslopper completions bash'.",
        "_deslopper() {",
        "    local cur prev cmd word",
        '    cur="${COMP_WORDS[COMP_CWORD]}"',
        '    prev="${COMP_WORDS[COMP_CWORD-1]}"',
        '    cmd=""',
        '    for word in "${COMP_WORDS[@]:1:COMP_CWORD-1}"; do',
        '        case "$word" in',
        f'            {"|".join(facts)}) cmd="$word"; break ;;',
        "        esac",
        "    done",
        '    if [ -z "$cmd" ]; then',
        f'        COMPREPLY=($(compgen -W "{names} --help --version" -- "$cur"))',
        "        return",
        "    fi",
        '    case "$cmd" in',
    ]
    for name, cmd in facts.items():
        lines.append(f"        {name})")
        valued = [
            (flag, f'compgen -W "{" ".join(values)}"')
            for flag, values in cmd["choices"].items()
        ] + [(flag, "compgen -f") for flag in cmd["file_flags"]]
        if valued:
            lines.append('            case "$prev" in')
            for flag, generator in valued:
                lines.append(
                    f'                {flag}) COMPREPLY=($({generator} -- "$cur")); return ;;'
                )
            lines.append("            esac")
        flag_words = " ".join(flag for flag, _desc in cmd["flags"])
        lines.append('            case "$cur" in')
        lines.append(
            f'                -*) COMPREPLY=($(compgen -W "{flag_words}" -- "$cur")) ;;'
        )
        if cmd["paths"]:
            lines.append('                *) COMPREPLY=($(compgen -f -- "$cur")) ;;')
        elif cmd["positional"]:
            lines.append(
                f'                *) COMPREPLY=($(compgen -W "{" ".join(cmd["positional"])}" -- "$cur")) ;;'
            )
        lines.append("            esac")
        lines.append("            ;;")
    lines += [
        "    esac",
        "}",
        "complete -o filenames -F _deslopper deslopper",
    ]
    return "\n".join(lines) + "\n"


# ── zsh ───────────────────────────────────────────────────────────────────────


def _zspec(spec: str) -> str:
    """A single-quoted zsh word, safe against quotes in descriptions."""
    return "'" + spec.replace("'", "'\\''") + "'"


def _zdesc(text: str) -> str:
    """Square brackets delimit _arguments descriptions, so none may nest."""
    return text.replace("[", "(").replace("]", ")")


def _zsh(facts) -> str:
    lines = [
        "#compdef deslopper",
        "# zsh completions for deslopper. Regenerate with 'deslopper completions zsh'.",
        "",
        "_deslopper() {",
        "    local context state state_descr line",
        "    typeset -A opt_args",
        "",
        "    _arguments -C \\",
        f"        {_zspec(f'{_HELP_ROW[0]}[{_HELP_ROW[1]}]')} \\",
        f"        {_zspec(f'{_VERSION_ROW[0]}[{_VERSION_ROW[1]}]')} \\",
        "        '1:command:->command' \\",
        "        '*::argument:->argument'",
        "",
        '    case "$state" in',
        "        command)",
        "            local -a commands",
        "            commands=(",
    ]
    for name, cmd in facts.items():
        entry = name + ":" + cmd["description"]
        lines.append(f"                {_zspec(entry)}")
    lines += [
        "            )",
        "            _describe -t commands 'deslopper command' commands",
        "            ;;",
        "        argument)",
        '            case "$words[1]" in',
    ]
    for name, cmd in facts.items():
        specs = []
        for flag, desc in cmd["flags"]:
            spec = f"{flag}[{_zdesc(desc)}]"
            if flag in cmd["choices"]:
                spec += f":value:({' '.join(cmd['choices'][flag])})"
            elif flag in cmd["file_flags"]:
                spec += ":file:_files"
            specs.append(spec)
        if cmd["paths"]:
            specs.append("*:path:_files")
        elif cmd["positional"]:
            specs.append(f"1:shell:({' '.join(cmd['positional'])})")
        lines.append(f"                {name})")
        lines.append("                    _arguments \\")
        for spec in specs[:-1]:
            lines.append(f"                        {_zspec(spec)} \\")
        lines.append(f"                        {_zspec(specs[-1])}")
        lines.append("                    ;;")
    lines += [
        "            esac",
        "            ;;",
        "    esac",
        "}",
        "",
        '_deslopper "$@"',
    ]
    return "\n".join(lines) + "\n"


# ── fish ──────────────────────────────────────────────────────────────────────


def _fquote(text: str) -> str:
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _fish(facts) -> str:
    lines = [
        "# fish completions for deslopper. Regenerate with 'deslopper completions fish'.",
        "complete -c deslopper -f",
        f"complete -c deslopper -n __fish_use_subcommand -l help -d {_fquote(_HELP_ROW[1])}",
        f"complete -c deslopper -n __fish_use_subcommand -l version -d {_fquote(_VERSION_ROW[1])}",
    ]
    for name, cmd in facts.items():
        lines.append(
            f"complete -c deslopper -n __fish_use_subcommand -a {name}"
            f" -d {_fquote(cmd['description'])}"
        )
    for name, cmd in facts.items():
        seen = _fquote(f"__fish_seen_subcommand_from {name}")
        for flag, desc in cmd["flags"]:
            entry = f"complete -c deslopper -n {seen} -l {flag[2:]}"
            if flag in cmd["choices"]:
                entry += f" -x -a {_fquote(' '.join(cmd['choices'][flag]))}"
            elif flag in cmd["file_flags"]:
                entry += " -r -F"
            lines.append(f"{entry} -d {_fquote(desc)}")
        if cmd["paths"]:
            lines.append(f"complete -c deslopper -n {seen} -F")
        elif cmd["positional"]:
            lines.append(
                f"complete -c deslopper -n {seen} -a {_fquote(' '.join(cmd['positional']))}"
            )
    return "\n".join(lines) + "\n"
