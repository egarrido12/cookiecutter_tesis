"""Main `cookiecutter` CLI."""

from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Literal

    from click import Context, Parameter


import click

from cookiecutter import __version__
from cookiecutter.config import get_user_config
from cookiecutter.exceptions import (
    ContextDecodingException,
    EmptyDirNameException,
    FailedHookException,
    InvalidModeException,
    InvalidZipRepository,
    OutputDirExistsException,
    RepositoryCloneFailed,
    RepositoryNotFound,
    UndefinedVariableInTemplate,
    UnknownExtension,
)
from cookiecutter.log import configure_logger
from cookiecutter.main import cookiecutter

# Errores de Cookiecutter que se reportan al usuario mostrando solo su mensaje.
_ERRORS_REPORTED_AS_MESSAGE = (
    ContextDecodingException,
    OutputDirExistsException,
    EmptyDirNameException,
    InvalidModeException,
    FailedHookException,
    UnknownExtension,
    InvalidZipRepository,
    RepositoryNotFound,
    RepositoryCloneFailed,
)


def version_msg() -> str:
    """Return the Cookiecutter version, location and Python powering it."""
    python_version = sys.version
    location = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return f"Cookiecutter {__version__} from {location} (Python {python_version})"


def _ensure_key_value_form(item: str) -> None:
    """Raise ``click.BadParameter`` if ``item`` is not of the form key=value."""
    if '=' not in item:
        msg = (
            f"EXTRA_CONTEXT should contain items of the form key=value; "
            f"'{item}' doesn't match that form"
        )
        raise click.BadParameter(msg)


def validate_extra_context(
    _ctx: Context, _param: Parameter, value: Iterable[str]
) -> OrderedDict[str, str] | None:
    """Validate extra context."""
    for item in value:
        _ensure_key_value_form(item)

    # Convert tuple -- e.g.: ('program_name=foobar', 'startsecs=66')
    # to dict -- e.g.: {'program_name': 'foobar', 'startsecs': '66'}
    return OrderedDict(item.split('=', 1) for item in value) or None


def _find_installed_template_names(cookiecutter_folder: str) -> list[str]:
    """Return the names of the sub-folders that contain a cookiecutter.json file."""
    return [
        folder
        for folder in os.listdir(cookiecutter_folder)
        if os.path.exists(
            os.path.join(cookiecutter_folder, folder, 'cookiecutter.json')
        )
    ]


def list_installed_templates(
    default_config: bool | dict[str, Any], passed_config_file: str | None
) -> None:
    """List installed (locally cloned) templates. Use cookiecutter --list-installed."""
    config = get_user_config(passed_config_file, default_config)
    cookiecutter_folder: str = config['cookiecutters_dir']
    if not os.path.exists(cookiecutter_folder):
        click.echo(
            f"Error: Cannot list installed templates. "
            f"Folder does not exist: {cookiecutter_folder}"
        )
        sys.exit(-1)

    template_names = _find_installed_template_names(cookiecutter_folder)
    click.echo(f'{len(template_names)} installed templates: ')
    for name in template_names:
        click.echo(f' * {name}')


def _is_help_requested(template: str | None) -> bool:
    """Return True if no template was given or the user explicitly asked for help."""
    return not template or template.lower() == 'help'


def _resolve_accept_hooks(accept_hooks: Literal['yes', 'ask', 'no']) -> bool:
    """Translate the ``--accept-hooks`` choice into a boolean.

    When the choice is ``ask``, the user is prompted to decide whether the
    pre/post hooks should be executed.
    """
    if accept_hooks == "ask":
        return click.confirm("Do you want to execute hooks?")
    return accept_hooks == "yes"


def _report_undefined_variable(error: UndefinedVariableInTemplate) -> None:
    """Print the details of an undefined variable error, including its context."""
    click.echo(f'{error.message}')
    click.echo(f'Error message: {error.error.message}')

    context_str = json.dumps(error.context, indent=4, sort_keys=True)
    click.echo(f'Context: {context_str}')


@click.command(context_settings={"help_option_names": ['-h', '--help']})
@click.version_option(__version__, '-V', '--version', message=version_msg())
@click.argument('template', required=False)
@click.argument('extra_context', nargs=-1, callback=validate_extra_context)
@click.option(
    '--no-input',
    is_flag=True,
    help='Do not prompt for parameters and only use cookiecutter.json file content. '
    'Defaults to deleting any cached resources and redownloading them. '
    'Cannot be combined with the --replay flag.',
)
@click.option(
    '-c',
    '--checkout',
    help='branch, tag or commit to checkout after git clone',
)
@click.option(
    '--directory',
    help='Directory within repo that holds cookiecutter.json file '
    'for advanced repositories with multi templates in it',
)
@click.option(
    '-v', '--verbose', is_flag=True, help='Print debug information', default=False
)
@click.option(
    '--replay',
    is_flag=True,
    help='Do not prompt for parameters and only use information entered previously. '
    'Cannot be combined with the --no-input flag or with extra configuration passed.',
)
@click.option(
    '--replay-file',
    type=click.Path(),
    default=None,
    help='Use this file for replay instead of the default.',
)
@click.option(
    '-f',
    '--overwrite-if-exists',
    is_flag=True,
    help='Overwrite the contents of the output directory if it already exists',
)
@click.option(
    '-s',
    '--skip-if-file-exists',
    is_flag=True,
    help='Skip the files in the corresponding directories if they already exist',
    default=False,
)
@click.option(
    '-o',
    '--output-dir',
    default='.',
    type=click.Path(),
    help='Where to output the generated project dir into',
)
@click.option(
    '--config-file', type=click.Path(), default=None, help='User configuration file'
)
@click.option(
    '--default-config',
    is_flag=True,
    help='Do not load a config file. Use the defaults instead',
)
@click.option(
    '--debug-file',
    type=click.Path(),
    default=None,
    help='File to be used as a stream for DEBUG logging',
)
@click.option(
    '--accept-hooks',
    type=click.Choice(['yes', 'ask', 'no']),
    default='yes',
    help='Accept pre/post hooks',
)
@click.option(
    '-l', '--list-installed', is_flag=True, help='List currently installed templates.'
)
@click.option(
    '--keep-project-on-failure',
    is_flag=True,
    help='Do not delete project folder on failure',
)
def main(
    template: str,
    extra_context: dict[str, Any],
    no_input: bool,
    checkout: str,
    verbose: bool,
    replay: bool | str,
    overwrite_if_exists: bool,
    output_dir: str,
    config_file: str | None,
    default_config: bool,
    debug_file: str | None,
    directory: str,
    skip_if_file_exists: bool,
    accept_hooks: Literal['yes', 'ask', 'no'],
    replay_file: str | None,
    list_installed: bool,
    keep_project_on_failure: bool,
) -> None:
    """Create a project from a Cookiecutter project template (TEMPLATE).

    Cookiecutter is free and open source software, developed and managed by
    volunteers. If you would like to help out or fund the project, please get
    in touch at https://github.com/cookiecutter/cookiecutter.
    """
    # Commands that should work without arguments
    if list_installed:
        list_installed_templates(default_config, config_file)
        sys.exit(0)

    # Raising usage, after all commands that should work without args.
    if _is_help_requested(template):
        click.echo(click.get_current_context().get_help())
        sys.exit(0)

    configure_logger(stream_level='DEBUG' if verbose else 'INFO', debug_file=debug_file)

    should_run_hooks = _resolve_accept_hooks(accept_hooks)

    # An explicit replay file takes precedence over the --replay flag.
    effective_replay = replay_file or replay

    try:
        cookiecutter(
            template,
            checkout,
            no_input,
            extra_context=extra_context,
            replay=effective_replay,
            overwrite_if_exists=overwrite_if_exists,
            output_dir=output_dir,
            config_file=config_file,
            default_config=default_config,
            password=os.environ.get('COOKIECUTTER_REPO_PASSWORD'),
            directory=directory,
            skip_if_file_exists=skip_if_file_exists,
            accept_hooks=should_run_hooks,
            keep_project_on_failure=keep_project_on_failure,
        )
    except _ERRORS_REPORTED_AS_MESSAGE as error:
        click.echo(error)
        sys.exit(1)
    except UndefinedVariableInTemplate as undefined_err:
        _report_undefined_variable(undefined_err)
        sys.exit(1)


if __name__ == "__main__":
    main()
