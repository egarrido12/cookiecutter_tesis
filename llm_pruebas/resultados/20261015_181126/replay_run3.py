"""
cookiecutter.replay.

Persistencia del contexto de generación (*replay*) en ficheros JSON.
-------------------
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from cookiecutter.utils import make_sure_path_exists

if TYPE_CHECKING:
    from pathlib import Path

_REPLAY_FILE_EXTENSION = '.json'
_REQUIRED_CONTEXT_KEY = 'cookiecutter'


def _ensure_context_has_cookiecutter_key(context: dict[str, Any]) -> None:
    """Raise ``ValueError`` if ``context`` lacks the mandatory cookiecutter key."""
    if _REQUIRED_CONTEXT_KEY not in context:
        msg = f'Context is required to contain a {_REQUIRED_CONTEXT_KEY} key'
        raise ValueError(msg)


def get_file_name(replay_dir: Path | str, template_name: str) -> str:
    """Get the name of file."""
    has_extension = template_name.endswith(_REPLAY_FILE_EXTENSION)
    suffix = '' if has_extension else _REPLAY_FILE_EXTENSION
    file_name = f'{template_name}{suffix}'
    return os.path.join(replay_dir, file_name)


def dump(replay_dir: Path | str, template_name: str, context: dict[str, Any]) -> None:
    """Write json data to file."""
    make_sure_path_exists(replay_dir)
    _ensure_context_has_cookiecutter_key(context)

    replay_file = get_file_name(replay_dir, template_name)

    with open(replay_file, 'w', encoding="utf-8") as outfile:
        json.dump(context, outfile, indent=2)


def load(replay_dir: Path | str, template_name: str) -> dict[str, Any]:
    """Read json data from file."""
    replay_file = get_file_name(replay_dir, template_name)

    with open(replay_file, encoding="utf-8") as infile:
        context: dict[str, Any] = json.load(infile)

    _ensure_context_has_cookiecutter_key(context)
    return context
