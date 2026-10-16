"""
Main entry point for the `cookiecutter` command.

The code in this module is also a good example of how to use Cookiecutter as a
library rather than a script.
"""

from __future__ import annotations

import logging
import os
import sys
from copy import copy
from pathlib import Path
from typing import Any

from cookiecutter.config import get_user_config
from cookiecutter.exceptions import InvalidModeException
from cookiecutter.generate import generate_context, generate_files
from cookiecutter.hooks import run_pre_prompt_hook
from cookiecutter.prompt import choose_nested_template, prompt_for_config
from cookiecutter.replay import dump, load
from cookiecutter.repository import determine_repo_dir
from cookiecutter.utils import rmtree

logger = logging.getLogger(__name__)

_NESTED_TEMPLATE_KEYS = frozenset({"template", "templates"})


def cookiecutter(
    template: str,
    checkout: str | None = None,
    no_input: bool = False,
    extra_context: dict[str, Any] | None = None,
    replay: bool | str | None = None,
    overwrite_if_exists: bool = False,
    output_dir: str = '.',
    config_file: str | None = None,
    default_config: bool = False,
    password: str | None = None,
    directory: str | None = None,
    skip_if_file_exists: bool = False,
    accept_hooks: bool = True,
    keep_project_on_failure: bool = False,
) -> str:
    """
    Run Cookiecutter just as if using it from the command line.

    :param template: A directory containing a project template directory,
        or a URL to a git repository.
    :param checkout: The branch, tag or commit ID to checkout after clone.
    :param no_input: Do not prompt for user input.
        Use default values for template parameters taken from `cookiecutter.json`, user
        config and `extra_dict`. Force a refresh of cached resources.
    :param extra_context: A dictionary of context that overrides default
        and user configuration.
    :param replay: Do not prompt for input, instead read from saved json. If
        ``True`` read from the ``replay_dir``.
        if it exists
    :param overwrite_if_exists: Overwrite the contents of the output directory
        if it exists.
    :param output_dir: Where to output the generated project dir into.
    :param config_file: User configuration file path.
    :param default_config: Use default values rather than a config file.
    :param password: The password to use when extracting the repository.
    :param directory: Relative path to a cookiecutter template in a repository.
    :param skip_if_file_exists: Skip the files in the corresponding directories
        if they already exist.
    :param accept_hooks: Accept pre and post hooks if set to `True`.
    :param keep_project_on_failure: If `True` keep generated project directory even when
        generation fails
    """
    _check_replay_mode_compatibility(replay, no_input, extra_context)

    config_dict = get_user_config(
        config_file=config_file,
        default_config=default_config,
    )
    base_repo_dir, cleanup_base_repo_dir = determine_repo_dir(
        template=template,
        abbreviations=config_dict['abbreviations'],
        clone_to_dir=config_dict['cookiecutters_dir'],
        checkout=checkout,
        no_input=no_input,
        password=password,
        directory=directory,
    )
    # The pre_prompt hook may copy the repository into a temporary directory.
    repo_dir = str(run_pre_prompt_hook(base_repo_dir)) if accept_hooks else base_repo_dir
    # Always remove the temporary dir if it was created.
    cleanup_repo_dir = repo_dir != base_repo_dir

    import_patch = _patch_import_path_for_repo(repo_dir)
    template_name = os.path.basename(os.path.abspath(repo_dir))
    if replay:
        with import_patch:
            context_from_replayfile, template_name = _load_replay_context(
                replay, config_dict, template_name
            )

    context_file = os.path.join(repo_dir, 'cookiecutter.json')
    logger.debug('context_file is %s', context_file)

    # In replay mode ``extra_context`` is always None (see the mode check above).
    context = generate_context(
        context_file=context_file,
        default_context=config_dict['default_context'],
        extra_context=None if replay else extra_context,
    )

    if replay:
        logger.debug('replayfile context: %s', context_from_replayfile)
        context_for_prompting = _variables_missing_from_replay(
            context, context_from_replayfile
        )
        context = context_from_replayfile
        logger.debug('prompting context: %s', context_for_prompting)
    else:
        context_for_prompting = context

    # Preserve the original cookiecutter options.
    context['_cookiecutter'] = _public_variables(context['cookiecutter'])

    # Prompt the user to manually configure at the command line,
    # except when 'no-input' flag is set.
    with import_patch:
        if _has_nested_templates(context):
            nested_template = choose_nested_template(context, repo_dir, no_input)
            return cookiecutter(
                template=nested_template,
                checkout=checkout,
                no_input=no_input,
                extra_context=extra_context,
                replay=replay,
                overwrite_if_exists=overwrite_if_exists,
                output_dir=output_dir,
                config_file=config_file,
                default_config=default_config,
                password=password,
                directory=directory,
                skip_if_file_exists=skip_if_file_exists,
                accept_hooks=accept_hooks,
                keep_project_on_failure=keep_project_on_failure,
            )
        if context_for_prompting['cookiecutter']:
            context['cookiecutter'].update(
                prompt_for_config(context_for_prompting, no_input)
            )

    logger.debug('context is %s', context)

    _add_generation_metadata(context, template, output_dir, repo_dir, checkout)

    dump(config_dict['replay_dir'], template_name, context)

    # Create project from local context and project template.
    with import_patch:
        result = generate_files(
            repo_dir=repo_dir,
            context=context,
            overwrite_if_exists=overwrite_if_exists,
            skip_if_file_exists=skip_if_file_exists,
            output_dir=output_dir,
            accept_hooks=accept_hooks,
            keep_project_on_failure=keep_project_on_failure,
        )

    if cleanup_repo_dir:
        rmtree(repo_dir)
    if cleanup_base_repo_dir:
        rmtree(base_repo_dir)
    return result


def _check_replay_mode_compatibility(
    replay: bool | str | None,
    no_input: bool,
    extra_context: dict[str, Any] | None,
) -> None:
    """Raise if replay is combined with ``no_input`` or ``extra_context``."""
    if replay and ((no_input is not False) or (extra_context is not None)):
        err_msg = (
            "You can not use both replay and no_input or extra_context "
            "at the same time."
        )
        raise InvalidModeException(err_msg)


def _load_replay_context(
    replay: bool | str,
    config_dict: dict[str, Any],
    template_name: str,
) -> tuple[dict[str, Any], str]:
    """Load the replay context and return it with the template name it belongs to.

    If ``replay`` is a boolean, the replay file is looked up in the configured
    ``replay_dir`` using ``template_name``. Otherwise ``replay`` is a path to a
    replay file, from which both the directory and the template name are derived.
    """
    if isinstance(replay, bool):
        return load(config_dict['replay_dir'], template_name), template_name

    replay_dir, replay_template_name = os.path.split(os.path.splitext(replay)[0])
    return load(replay_dir, replay_template_name), replay_template_name


def _variables_missing_from_replay(
    context: dict[str, Any], context_from_replayfile: dict[str, Any]
) -> dict[str, Any]:
    """Return a prompting context with the variables not stored in the replay file."""
    replayed_variables = context_from_replayfile['cookiecutter']
    return {
        'cookiecutter': {
            key: value
            for key, value in context['cookiecutter'].items()
            if key not in replayed_variables
        }
    }


def _public_variables(cookiecutter_dict: dict[str, Any]) -> dict[str, Any]:
    """Return the variables whose names do not start with an underscore."""
    return {
        key: value
        for key, value in cookiecutter_dict.items()
        if not key.startswith("_")
    }


def _has_nested_templates(context: dict[str, Any]) -> bool:
    """Return True if the context defines nested templates to choose from."""
    return not _NESTED_TEMPLATE_KEYS.isdisjoint(context["cookiecutter"].keys())


def _add_generation_metadata(
    context: dict[str, Any],
    template: str,
    output_dir: str,
    repo_dir: Path | str,
    checkout: str | None,
) -> None:
    """Store template, output dir, repo dir and checkout details in the context."""
    cookiecutter_dict = context['cookiecutter']
    cookiecutter_dict['_template'] = template
    cookiecutter_dict['_output_dir'] = os.path.abspath(output_dir)
    cookiecutter_dict['_repo_dir'] = f"{repo_dir}"
    cookiecutter_dict['_checkout'] = checkout


class _patch_import_path_for_repo:  # noqa: N801
    """Context manager that temporarily appends the repo dir to ``sys.path``."""

    def __init__(self, repo_dir: Path | str) -> None:
        self._repo_dir = f"{repo_dir}" if isinstance(repo_dir, Path) else repo_dir

    def __enter__(self) -> None:
        self._path = copy(sys.path)
        sys.path.append(self._repo_dir)

    def __exit__(self, _type, _value, _traceback):  # type: ignore[no-untyped-def]
        sys.path = self._path
