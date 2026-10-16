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

_TEMPLATE_DIR_KEYWORD = 'cookiecutter'


def _is_project_template_dir_name(name: str, env: Environment) -> bool:
    """Check whether ``name`` looks like a templated project directory.

    A project template directory name must contain the word ``cookiecutter``
    and the Jinja2 variable delimiters configured in ``env`` (by default
    ``{{`` and ``}}``).

    :param name: Name of an entry inside the repository directory.
    :param env: Jinja2 environment that provides the variable delimiters.
    :return: True if ``name`` matches a project template directory name.
    """
    return (
        _TEMPLATE_DIR_KEYWORD in name
        and env.variable_start_string in name
        and env.variable_end_string in name
    )


def find_template(repo_dir: Path | str, env: Environment) -> Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    :param repo_dir: Local directory of newly cloned repo.
    :param env: Jinja2 environment used to know the variable delimiters.
    :return: Path to the project template, built from ``repo_dir`` and the
        name of the matching child entry.
    :raises NonTemplatedInputDirException: If no child entry of ``repo_dir``
        looks like a project template.
    """
    logger.debug('Searching %s for the project template.', repo_dir)

    for entry_name in os.listdir(repo_dir):
        if _is_project_template_dir_name(entry_name, env):
            project_template = Path(repo_dir, entry_name)
            logger.debug('The project template appears to be %s', project_template)
            return project_template

    raise NonTemplatedInputDirException
