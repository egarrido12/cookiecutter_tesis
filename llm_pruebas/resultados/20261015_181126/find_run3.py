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

_PROJECT_TEMPLATE_MARKER = 'cookiecutter'


def _is_project_template_name(name: str, env: Environment) -> bool:
    """Check whether ``name`` looks like a templated project directory name.

    A project template directory name must contain the word ``cookiecutter``
    and both Jinja2 variable delimiters configured in ``env``
    (e.g. ``{{cookiecutter.project_slug}}``).

    :param name: Name of an entry inside the repository directory.
    :param env: Jinja2 environment providing the variable delimiters.
    :return: True if ``name`` matches the project template pattern.
    """
    return (
        _PROJECT_TEMPLATE_MARKER in name
        and env.variable_start_string in name
        and env.variable_end_string in name
    )


def find_template(repo_dir: Path | str, env: Environment) -> Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    The first entry of ``repo_dir`` (in ``os.listdir`` order) whose name
    matches the project template pattern is selected.

    :param repo_dir: Local directory of newly cloned repo.
    :param env: Jinja2 environment providing the variable delimiters.
    :return: Path to the project template, built by joining ``repo_dir``
        with the name of the template directory.
    :raises NonTemplatedInputDirException: If no entry matches the pattern.
    """
    logger.debug('Searching %s for the project template.', repo_dir)

    for entry_name in os.listdir(repo_dir):
        if _is_project_template_name(entry_name, env):
            project_template = Path(repo_dir, entry_name)
            logger.debug('The project template appears to be %s', project_template)
            return project_template

    raise NonTemplatedInputDirException
