```python
"""Main `cookiecutter` CLI."""

from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Literal

    from click import Context, Parameter


_TEMPLATE_CONFIG_FILENAME = 'cookiecutter.json'
_REPO_PASSWORD_ENV_VAR = 'COOKIECUTTER_REPO_PASSWORD'

# Errors whose message is shown as-is to the user before exiting with status 1.
_USER_FACING_ERRORS: tuple[type[Exception], ...] = (
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


def _check_key_value_format(item: str) -> None:
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
        _check_key_value_format(item)

    # Convert tuple -- e.g.: ('program_name=foobar', 'startsecs=66')
    # to dict -- e.g.: {'program_name': 'foobar', 'startsecs': '66'}
    return OrderedDict(item.split('=', 1) for item in value) or None


def _is_installed_template(cookiecutters_folder: str, folder: str) -> bool:
    """Return True if ``folder`` inside ``cookiecutters_folder`` is a template."""
    return os.path.exists(
        os.path.join(cookiecutters_folder, folder, _TEMPLATE_CONFIG_FILENAME)
    )


def _find_installed_templates(cookiecutters_folder: str) -> list[str]:
    """Return the names of the templates cloned into ``cookiecutters_folder``."""
    return [
        folder
        for folder in os.listdir(cookiecutters_folder)
        if _is_installed_template(cookiecutters_folder, folder)
    ]


def list_installed_templates(
    default_config: bool | dict[str, Any], passed_config_file: str | None
) -> None:
    """List installed (locally cloned) templates. Use cookiecutter --list-installed."""
    config = get_user_config(passed_config_file, default_config)
    cookiecutters_folder: str = config['cookiecutters_dir']
    if not os.path.exists(cookiecutters_folder):
        click.echo(
            f"Error: Cannot list installed templates. "
            f"Folder does not exist: {cookiecutters_folder}"
        )
        sys.exit(-1)

    template_names = _find_installed_templates(cookiecutters_folder)
    click.echo(f'{len(template_names)} installed templates: ')
    for name in template_names:
        click.echo(f' * {name}')


def _is_help_request(template: str) -> bool:
    """Return True if no template was given or the user explicitly asked for help."""
    return not template or template.lower() == 'help'


def _should_accept_hooks(accept_hooks: Literal['yes', 'ask', 'no']) -> bool:
    """Resolve the --accept-hooks option, prompting the user if it is 'ask'."""
    if accept_hooks == "ask":
        return click.confirm("Do you want to execute hooks?")
    return accept_hooks == "yes"


def _echo_undefined_variable_error(undefined_err: UndefinedVariableInTemplate) -> None:
    """Print the details of an undefined variable error, including its context."""
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
    if _is_help_request(template):
        click.echo(click.get_current_context().get_help())
        sys.exit(0)

    configure_logger(stream_level='DEBUG' if verbose else 'INFO', debug_file=debug_file)

    hooks_accepted = _should_accept_hooks(accept_hooks)

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
    except _USER_FACING_ERRORS as error:
        click.echo(error)
        sys.exit(1)
    except UndefinedVariableInTemplate as undefined_err:
        _echo_undefined_variable_error(undefined_err)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

## Refactorizaciones aplicadas

- **Extract Variable (constante de módulo)**: `_USER_FACING_ERRORS`.
  - Elementos afectados: la tupla de nueve excepciones que estaba en línea dentro del `except` de `main`.
  - Motivo: el bloque `try/except` queda más corto. Además, el nombre explica la intención: son errores cuyo mensaje se muestra tal cual al usuario. El orden y el conjunto de excepciones no cambian.

- **Replace Magic Literal**: `_TEMPLATE_CONFIG_FILENAME` (`'cookiecutter.json'`) y `_REPO_PASSWORD_ENV_VAR` (`'COOKIECUTTER_REPO_PASSWORD'`).
  - Motivo: dar nombre a cadenas con significado de dominio y evitar errores tipográficos.

- **Extract Function**: `_check_key_value_format(item)`.
  - Elementos afectados: `validate_extra_context`.
  - Motivo: separar la regla de validación de un elemento del recorrido y de la conversión a `OrderedDict`. Se conserva el orden original: primero se validan todos los elementos y después se convierten. El mensaje de `click.BadParameter` es idéntico.

- **Rename Variable**: `string` → `item` y `s` → `item`.
  - Elementos afectados: `validate_extra_context`.
  - Motivo: `string` coincidía con el nombre de un módulo estándar y `s` no era descriptivo.

- **Extract Function**: `_is_installed_template(...)` y `_find_installed_templates(...)`.
  - Elementos afectados: `list_installed_templates`.
  - Motivo: la función pública queda centrada en su flujo: obtener la configuración, comprobar que la carpeta existe y listar. La lógica de detección de plantillas queda aislada. El orden de `os.listdir` se mantiene.

- **Rename Variable**: `cookiecutter_folder` → `cookiecutters_folder`.
  - Elementos afectados: `list_installed_templates`.
  - Motivo: coherencia con la clave de configuración `cookiecutters_dir`, que contiene varias plantillas.

- **Extract Function**: `_is_help_request(template)`.
  - Elementos afectados: la condición `not template or template.lower() == 'help'` de `main`.
  - Motivo: la condición pasa a expresarse por su intención.

- **Extract Function**: `_should_accept_hooks(accept_hooks)`.
  - Elementos afectados: el bloque `if/else` que resolvía `--accept-hooks` en `main`.
  - Motivo: aislar la traducción de la opción `'yes' | 'ask' | 'no'` a un booleano, incluida la confirmación interactiva. Se sigue llamando a `click.confirm` con el mismo texto y solo cuando el valor es `"ask"`.

- **Rename Variable**: `_accept_hooks` → `hooks_accepted`.
  - Elementos afectados: variable local de `main`.
  - Motivo: el guion bajo inicial sugería un elemento privado de módulo, y el nombre casi coincidía con el parámetro `accept_hooks`, lo que inducía a confusión.

- **Inline Variable / Remove Assignment to Parameter**: `if replay_file: replay = replay_file` → `replay=replay_file or replay`.
  - Elementos afectados: la reasignación del parámetro `replay` en `main`.
  - Motivo: se evita reasignar un parámetro. La expresión es semánticamente equivalente: si `replay_file` es truthy se usa ese valor, y si no, el de `replay`.

- **Extract Function**: `_echo_undefined_variable_error(undefined_err)`.
  - Elementos afectados: el cuerpo del `except UndefinedVariableInTemplate` en `main`.
  - Motivo: separar el formateo del informe de error (mensaje, detalle de Jinja y contexto en JSON) del control de flujo. `sys.exit(1)` se mantiene dentro del bloque `except`, así que la salida y el encadenamiento de excepciones no cambian.

- **Rename Variable**: `e` → `error`.
  - Elementos afectados: variable de captura en `main`.
  - Motivo: un nombre más descriptivo.

- **Reorganizar imports (Slide Statements)**: el bloque `if TYPE_CHECKING:` pasa detrás de todos los imports de ejecución.
  - Motivo: antes estaba intercalado entre los imports de la biblioteca estándar y `import click`. Ahora sigue la convención habitual y la del resto del paquete.

Se mantienen sin cambios:
- Las firmas públicas de `version_msg`, `validate_extra_context`, `list_installed_templates` y `main`.
- Todos los decoradores y textos de ayuda de Click, incluido el docstring de `main`, que Click muestra como ayuda.
- Los mensajes de salida y los códigos de `sys.exit`.
- Los nombres importados a nivel de módulo (`cookiecutter`, `get_user_config`, `configure_logger`, `click`), para que sigan funcionando los parches que hagan los tests sobre `cookiecutter.cli.*`.