```python
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

_KEY_VALUE_SEPARATOR = '='
_TEMPLATE_CONFIG_FILENAME = 'cookiecutter.json'
_REPO_PASSWORD_ENV_VAR = 'COOKIECUTTER_REPO_PASSWORD'

# Errors raised while generating a project that are reported to the user
# by simply printing the exception message.
_SIMPLE_REPORTED_ERRORS = (
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
    if _KEY_VALUE_SEPARATOR not in item:
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
    return OrderedDict(item.split(_KEY_VALUE_SEPARATOR, 1) for item in value) or None


def _find_installed_templates(cookiecutter_folder: str) -> list[str]:
    """Return the names of the folders that contain a cookiecutter template."""
    return [
        folder
        for folder in os.listdir(cookiecutter_folder)
        if os.path.exists(
            os.path.join(cookiecutter_folder, folder, _TEMPLATE_CONFIG_FILENAME)
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

    template_names = _find_installed_templates(cookiecutter_folder)
    click.echo(f'{len(template_names)} installed templates: ')
    for name in template_names:
        click.echo(f' * {name}')


def _is_help_requested(template: str | None) -> bool:
    """Return True if no template was given or the user explicitly asked for help."""
    return not template or template.lower() == 'help'


def _stream_log_level(verbose: bool) -> str:
    """Return the console logging level for the given verbosity."""
    return 'DEBUG' if verbose else 'INFO'


def _resolve_accept_hooks(accept_hooks: Literal['yes', 'ask', 'no']) -> bool:
    """Decide whether pre/post hooks must run, asking the user if needed."""
    if accept_hooks == "ask":
        return click.confirm("Do you want to execute hooks?")
    return accept_hooks == "yes"


def _report_undefined_variable(undefined_err: UndefinedVariableInTemplate) -> None:
    """Print a detailed report of an undefined variable found in a template."""
    click.echo(f'{undefined_err.message}')
    click.echo(f'Error message: {undefined_err.error.message}')

    context_str = json.dumps(undefined_err.context, indent=4, sort_keys=True)
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

    configure_logger(stream_level=_stream_log_level(verbose), debug_file=debug_file)

    hooks_accepted = _resolve_accept_hooks(accept_hooks)

    try:
        cookiecutter(
            template,
            checkout,
            no_input,
            extra_context=extra_context,
            replay=replay_file or replay,
            overwrite_if_exists=overwrite_if_exists,
            output_dir=output_dir,
            config_file=config_file,
            default_config=default_config,
            password=os.environ.get(_REPO_PASSWORD_ENV_VAR),
            directory=directory,
            skip_if_file_exists=skip_if_file_exists,
            accept_hooks=hooks_accepted,
            keep_project_on_failure=keep_project_on_failure,
        )
    except _SIMPLE_REPORTED_ERRORS as e:
        click.echo(e)
        sys.exit(1)
    except UndefinedVariableInTemplate as undefined_err:
        _report_undefined_variable(undefined_err)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

## Refactorizaciones aplicadas

- **Extract Variable (constante de módulo)**: creé `_SIMPLE_REPORTED_ERRORS` a partir de la tupla de excepciones que estaba escrita dentro del `except` de `main`.
  - **Motivo**: la cláusula `except` queda corta y legible. El nombre y el comentario explican por qué esas excepciones se agrupan: todas se informan imprimiendo solo su mensaje. Además, la lista se puede mantener en un único lugar. El orden de los bloques `except` no cambia.

- **Replace Magic Literal**: extraje `_KEY_VALUE_SEPARATOR`, `_TEMPLATE_CONFIG_FILENAME` y `_REPO_PASSWORD_ENV_VAR`, que se usan en `validate_extra_context`, en la búsqueda de plantillas instaladas y en `main`.
  - **Motivo**: estos literales tienen significado de dominio y conviene que tengan nombre.
  - En los mensajes de error y de ayuda el texto `key=value` se mantiene literal, para que la salida sea idéntica.

- **Extract Function → `_ensure_key_value_form`**: sale de `validate_extra_context`.
  - **Motivo**: separa la validación de cada elemento de la conversión a `OrderedDict`. La función pública queda reducida a dos pasos claros.
  - **Rename Variable**: dentro de esa lógica, `string` pasa a llamarse `item`, porque `string` coincide con el nombre de un módulo de la biblioteca estándar y no describe el rol del valor.

- **Extract Function → `_find_installed_templates`**: sale de `list_installed_templates`.
  - **Motivo**: aísla el criterio "una carpeta es una plantilla si contiene `cookiecutter.json`" de la parte de presentación (mensajes y `sys.exit(-1)`).

- **Extract Function / Decompose Conditional → `_is_help_requested`**: sale de la condición `not template or template.lower() == 'help'` en `main`.
  - **Motivo**: el nombre expresa la intención de la condición. El orden de los chequeos se mantiene: primero `--list-installed`, después la ayuda.

- **Extract Function → `_stream_log_level`**: sale de la expresión condicional que se pasaba a `configure_logger`.
  - **Motivo**: da nombre a la regla de verbosidad y simplifica la llamada.

- **Extract Function → `_resolve_accept_hooks`**: sale del bloque `if/else` de `main` que traducía `'yes'/'ask'/'no'` a booleano.
  - **Motivo**: encapsula la decisión, incluida la pregunta interactiva con `click.confirm`. Se sigue invocando en el mismo punto, después de configurar el logger.

- **Rename Variable**: la variable local `_accept_hooks` pasa a llamarse `hooks_accepted`, en `main`.
  - **Motivo**: el guion bajo inicial sugería algo "privado" y se confundía con el parámetro `accept_hooks`. El nuevo nombre indica que es el resultado ya resuelto.

- **Remove Assignments to Parameters / Inline Variable**: elimino la reasignación `replay = replay_file` y paso `replay=replay_file or replay` directamente en la llamada a `cookiecutter`.
  - **Motivo**: evita mutar un parámetro. La semántica es idéntica: si `replay_file` es verdadero se usa; si no, se usa `replay`.

- **Extract Function → `_report_undefined_variable`**: sale del bloque `except UndefinedVariableInTemplate` de `main`.
  - **Motivo**: separa el formateo del informe de error del flujo de control.
  - `sys.exit(1)` se queda en `main`, de modo que ambos `except` muestran explícitamente cómo termina el programa. La salida impresa y el código de salida son los mismos.

Los nombres y firmas públicas (`version_msg`, `validate_extra_context`, `list_installed_templates`, `main`), los decoradores de `click` y los imports a nivel de módulo no cambian. Por eso los parches que usan los tests (por ejemplo `cookiecutter.cli.cookiecutter`) siguen funcionando.