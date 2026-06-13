"""Errors that the CLI maps to exit code 2."""


class ConfigError(Exception):
    """A malformed config, preset, plugin, or tell."""


class UsageError(Exception):
    """A bad command-line invocation."""
