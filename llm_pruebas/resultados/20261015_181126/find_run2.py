"""Functions for finding Cookiecutter templates and other components."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from cookiecutter.exceptions import NonTemplatedInputDirException

if TYPE_CHECKING:
    from jinja2 import Environment

logger = logging.getLogger(__name__)


def _is_project_template_name(entry_name: str, env: Environment) -> bool:
    """Check whether ``entry_name`` looks like a templated project directory.

    A project template directory name must contain the word ``cookiecutter``
    and must be wrapped in the Jinja2 variable delimiters configured in
    ``env``, e.g. ``{{cookiecutter.project_slug}}``.

    :param entry_name: Name of a child entry of the repository directory.
    :param env: Jinja2 environment providing the variable delimiters.
    :return: True if ``entry_name`` is a templated project directory name.
    """
    return (
        'cookiecutter' in entry_name
        and env.variable_start_string in entry_name
        and env.variable_end_string in entry_name
    )


def find_template(repo_dir: Path | str, env: Environment) -> Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    :param repo_dir: Local directory of newly cloned repo.
    :param env: Jinja2 environment providing the variable delimiters.
    :return: Path to project template (relative if ``repo_dir`` is relative).
    :raises NonTemplatedInputDirException: If no child entry of ``repo_dir``
        is a templated project directory.
    """
    logger.debug('Searching %s for the project template.', repo_dir)

    for entry_name in os.listdir(repo_dir):
        if _is_project_template_name(entry_name, env):
            project_template = Path(repo_dir, entry_name)
            logger.debug('The project template appears to be %s', project_template)
            return project_template

    raise NonTemplatedInputDirException
