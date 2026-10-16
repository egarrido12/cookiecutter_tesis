"""Helper functions used throughout Cookiecutter."""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import stat
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2.ext import Extension

from cookiecutter.environment import StrictEnvironment

if TYPE_CHECKING:
    from jinja2 import Environment

logger = logging.getLogger(__name__)

# Template context key holding extra keyword arguments for the Jinja2 environment.
_JINJA2_ENV_VARS_KEY = '_jinja2_env_vars'


def force_delete(func, path, _exc_info) -> None:  # type: ignore[no-untyped-def]
    """Error handler for `shutil.rmtree()` equivalent to `rm -rf`.

    Usage: `shutil.rmtree(path, onerror=force_delete)`
    From https://docs.python.org/3/library/shutil.html#rmtree-example
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


def rmtree(path: Path | str) -> None:
    """Remove a directory and all its contents. Like rm -rf on Unix.

    :param path: A directory path.
    """
    shutil.rmtree(path, onerror=force_delete)


def make_sure_path_exists(path: Path | str) -> None:
    """Ensure that a directory exists.

    :param path: A directory tree path for creation.
    """
    logger.debug('Making sure path exists (creates tree if not exist): %s', path)
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        msg = f'Unable to create directory at {path}'
        raise OSError(msg) from error


@contextlib.contextmanager
def work_in(dirname: Path | str | None = None) -> Iterator[None]:
    """Context manager version of os.chdir.

    When exited, returns to the working directory prior to entering.
    """
    previous_dir = os.getcwd()
    try:
        if dirname is not None:
            os.chdir(dirname)
        yield
    finally:
        os.chdir(previous_dir)


def make_executable(script_path: Path | str) -> None:
    """Make `script_path` executable.

    :param script_path: The file to change
    """
    current_mode = os.stat(script_path).st_mode
    os.chmod(script_path, current_mode | stat.S_IEXEC)


def simple_filter(filter_function) -> type[Extension]:  # type: ignore[no-untyped-def]
    """Decorate a function to wrap it in a simplified jinja2 extension."""
    filter_name = filter_function.__name__

    class SimpleFilterExtension(Extension):
        def __init__(self, environment: Environment) -> None:
            super().__init__(environment)
            environment.filters[filter_name] = filter_function

    SimpleFilterExtension.__name__ = filter_name
    return SimpleFilterExtension


def create_tmp_repo_dir(repo_dir: Path | str) -> Path:
    """Create a temporary dir with a copy of the contents of repo_dir."""
    source_repo_dir = Path(repo_dir).resolve()
    tmp_base_dir = tempfile.mkdtemp(prefix='cookiecutter')
    tmp_repo_dir = f"{tmp_base_dir}/{source_repo_dir.name}"
    logger.debug('Copying repo_dir from %s to %s', source_repo_dir, tmp_repo_dir)
    shutil.copytree(source_repo_dir, tmp_repo_dir)
    return Path(tmp_repo_dir)


def create_env_with_context(context: dict[str, Any]) -> StrictEnvironment:
    """Create a jinja environment using the provided context."""
    cookiecutter_context = context.get('cookiecutter', {})
    jinja2_env_vars = cookiecutter_context.get(_JINJA2_ENV_VARS_KEY, {})

    return StrictEnvironment(
        context=context, keep_trailing_newline=True, **jinja2_env_vars
    )
