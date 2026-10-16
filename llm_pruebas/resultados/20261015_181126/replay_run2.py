"""
cookiecutter.replay.

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


def _validate_context(context: dict[str, Any]) -> None:
    """Raise ``ValueError`` if ``context`` lacks the required ``cookiecutter`` key.

    :param context: Context to be stored in, or read from, a replay file.
    """
    if _REQUIRED_CONTEXT_KEY not in context:
        msg = 'Context is required to contain a cookiecutter key'
        raise ValueError(msg)


def get_file_name(replay_dir: Path | str, template_name: str) -> str:
    """Return the path of the replay file for ``template_name`` in ``replay_dir``.

    The ``.json`` extension is appended only if ``template_name`` lacks it.

    :param replay_dir: Directory where replay files are stored.
    :param template_name: Name of the template, with or without ``.json``.
    """
    if template_name.endswith(_REPLAY_FILE_EXTENSION):
        file_name = template_name
    else:
        file_name = f'{template_name}{_REPLAY_FILE_EXTENSION}'
    return os.path.join(replay_dir, file_name)


def dump(replay_dir: Path | str, template_name: str, context: dict[str, Any]) -> None:
    """Write the context to the replay file of the template as JSON.

    :param replay_dir: Directory where replay files are stored. It is created
        if it does not exist.
    :param template_name: Name of the template.
    :param context: Context to save; must contain a ``cookiecutter`` key.
    """
    make_sure_path_exists(replay_dir)
    _validate_context(context)

    replay_file = get_file_name(replay_dir, template_name)
    with open(replay_file, 'w', encoding="utf-8") as outfile:
        json.dump(context, outfile, indent=2)


def load(replay_dir: Path | str, template_name: str) -> dict[str, Any]:
    """Read the context from the replay file of the template.

    :param replay_dir: Directory where replay files are stored.
    :param template_name: Name of the template.
    :return: The stored context, which is guaranteed to contain a
        ``cookiecutter`` key.
    """
    replay_file = get_file_name(replay_dir, template_name)
    with open(replay_file, encoding="utf-8") as infile:
        context: dict[str, Any] = json.load(infile)

    _validate_context(context)
    return context
