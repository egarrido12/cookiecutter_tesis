"""Helper functions for working with version control systems."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from shutil import which
from typing import TYPE_CHECKING

from cookiecutter.exceptions import (
    RepositoryCloneFailed,
    RepositoryNotFound,
    UnknownRepoType,
    VCSNotInstalled,
)
from cookiecutter.prompt import prompt_and_delete
from cookiecutter.utils import make_sure_path_exists

if TYPE_CHECKING:
    from typing import Literal

logger = logging.getLogger(__name__)


BRANCH_ERRORS = [
    'error: pathspec',
    'unknown revision',
]

_SUPPORTED_REPO_TYPES = ('git', 'hg')


def identify_repo(repo_url: str) -> tuple[Literal["git", "hg"], str]:
    """Determine if `repo_url` should be treated as a URL to a git or hg repo.

    Repos can be identified by prepending "hg+" or "git+" to the repo URL.

    :param repo_url: Repo URL of unknown type.
    :returns: ('git', repo_url) or ('hg', repo_url).
    :raises UnknownRepoType: If the repo type cannot be determined.
    """
    repo_url_values = repo_url.split('+')
    if len(repo_url_values) == 2:
        repo_type, url_without_prefix = repo_url_values
        if repo_type in _SUPPORTED_REPO_TYPES:
            return repo_type, url_without_prefix  # type: ignore[return-value]
        raise UnknownRepoType
    if 'git' in repo_url:
        return 'git', repo_url
    if 'bitbucket' in repo_url:
        return 'hg', repo_url
    raise UnknownRepoType


def is_vcs_installed(repo_type: str) -> bool:
    """
    Check if the version control system for a repo type is installed.

    :param repo_type:
    """
    return bool(which(repo_type))


def _get_repo_dir(repo_type: str, repo_url: str, clone_to_dir: Path) -> str:
    """Return the local directory where the repository will be cloned.

    :param repo_type: The VCS of the repository ('git' or 'hg').
    :param repo_url: Repo URL, without trailing slashes.
    :param clone_to_dir: The directory to clone to.
    """
    repo_name = os.path.split(repo_url)[1]
    if repo_type == 'git':
        repo_name = repo_name.split(':')[-1].rsplit('.git')[0]
    return os.path.normpath(os.path.join(clone_to_dir, repo_name))


def _build_checkout_command(repo_type: str, checkout: str) -> list[str]:
    """Return the VCS command used to checkout the given branch, tag or commit."""
    if repo_type == 'hg':
        # Avoid Mercurial "--config" and "--debugger" injection vulnerability
        return [repo_type, 'checkout', '--', checkout]
    return [repo_type, 'checkout', checkout]


def _run_vcs_command(command: list[str], cwd: Path | str) -> None:
    """Run a VCS command in `cwd`, capturing stderr together with stdout."""
    subprocess.check_output(command, cwd=cwd, stderr=subprocess.STDOUT)


def _clone_and_checkout(
    repo_type: str,
    repo_url: str,
    checkout: str | None,
    clone_to_dir: Path,
    repo_dir: str,
) -> None:
    """Clone the repository and, if requested, checkout the given reference."""
    _run_vcs_command([repo_type, 'clone', repo_url], cwd=clone_to_dir)
    if checkout is not None:
        _run_vcs_command(_build_checkout_command(repo_type, checkout), cwd=repo_dir)


def _raise_for_known_clone_error(
    output: str,
    repo_url: str,
    checkout: str | None,
    clone_error: subprocess.CalledProcessError,
) -> None:
    """Translate recognizable VCS failures into Cookiecutter exceptions.

    Returns normally if the error output does not match any known failure.
    """
    if 'not found' in output.lower():
        msg = f'The repository {repo_url} could not be found, have you made a typo?'
        raise RepositoryNotFound(msg) from clone_error
    if any(error in output for error in BRANCH_ERRORS):
        msg = (
            f'The {checkout} branch of repository '
            f'{repo_url} could not found, have you made a typo?'
        )
        raise RepositoryCloneFailed(msg) from clone_error


def clone(
    repo_url: str,
    checkout: str | None = None,
    clone_to_dir: Path | str = ".",
    no_input: bool = False,
) -> str:
    """Clone a repo to the current directory.

    :param repo_url: Repo URL of unknown type.
    :param checkout: The branch, tag or commit ID to checkout after clone.
    :param clone_to_dir: The directory to clone to.
                         Defaults to the current directory.
    :param no_input: Do not prompt for user input and eventually force a refresh of
        cached resources.
    :returns: str with path to the new directory of the repository.
    """
    # Ensure that clone_to_dir exists
    clone_to_dir = Path(clone_to_dir).expanduser()
    make_sure_path_exists(clone_to_dir)

    repo_type, repo_url = identify_repo(repo_url)
    if not is_vcs_installed(repo_type):
        msg = f"'{repo_type}' is not installed."
        raise VCSNotInstalled(msg)

    repo_url = repo_url.rstrip('/')
    repo_dir = _get_repo_dir(repo_type, repo_url, clone_to_dir)
    logger.debug('repo_dir is %s', repo_dir)

    if os.path.isdir(repo_dir):
        should_clone = prompt_and_delete(repo_dir, no_input=no_input)
    else:
        should_clone = True

    if not should_clone:
        return repo_dir

    try:
        _clone_and_checkout(repo_type, repo_url, checkout, clone_to_dir, repo_dir)
    except subprocess.CalledProcessError as clone_error:
        output = clone_error.output.decode('utf-8')
        _raise_for_known_clone_error(output, repo_url, checkout, clone_error)
        logger.exception('git clone failed with error: %s', output)
        raise

    return repo_dir
