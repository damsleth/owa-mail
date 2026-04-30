"""owa-mail - mail CLI for Outlook / Microsoft 365.

Pipe-friendly: JSON on stdout, logs on stderr, --pretty for humans.
The package entry point is `main`, wired up as the `owa-mail` console
script via pyproject.toml. See `cli.py` for the dispatch layer and the
per-concern modules (config, dates, messages, folders, scheduled,
format, auth, api) for the pure-function pieces.
"""
from .cli import main

__all__ = ["main"]
