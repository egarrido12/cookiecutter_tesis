```python
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

_NESTED_TEMPLATE_KEYS = ("template", "templates")


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
    _ensure_replay_mode_is_valid(replay, no_input, extra_context)

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
    repo_dir = _run_pre_prompt_hook_if_accepted(base_repo_dir, accept_hooks)
    # The pre_prompt hook works on a temporary copy of the repository:
    # if such a copy was created, it must always be removed.
    cleanup = repo_dir != base_repo_dir

    import_patch = _patch_import_path_for_repo(repo_dir)
    template_name = os.path.basename(os.path.abspath(repo_dir))
    if replay:
        with import_patch:
            context_from_replayfile, template_name = _load_replay_context(
                replay, config_dict['replay_dir'], template_name
            )

    context_file = os.path.join(repo_dir, 'cookiecutter.json')
    logger.debug('context_file is %s', context_file)

    # In replay mode ``extra_context`` is always None (enforced by
    # ``_ensure_replay_mode_is_valid``), so it is safe to pass it through.
    generated_context = generate_context(
        context_file=context_file,
        default_context=config_dict['default_context'],
        extra_context=extra_context,
    )
    if replay:
        logger.debug('replayfile context: %s', context_from_replayfile)
        context_for_prompting = _context_missing_from_replay(
            generated_context, context_from_replayfile
        )
        context = context_from_replayfile
        logger.debug('prompting context: %s', context_for_prompting)
    else:
        context = context_for_prompting = generated_context

    # Preserve the original cookiecutter options
    context['_cookiecutter'] = _public_options(context['cookiecutter'])

    # Prompt the user to manually configure at the command line,
    # except when the 'no-input' flag is set.
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

    _add_generation_details(
        context['cookiecutter'],
        template=template,
        output_dir=output_dir,
        repo_dir=repo_dir,
        checkout=checkout,
    )

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

    # Cleanup (if required)
    if cleanup:
        rmtree(repo_dir)
    if cleanup_base_repo_dir:
        rmtree(base_repo_dir)
    return result


def _ensure_replay_mode_is_valid(
    replay: bool | str | None,
    no_input: bool,
    extra_context: dict[str, Any] | None,
) -> None:
    """Raise if replay mode is combined with ``no_input`` or ``extra_context``."""
    if replay and ((no_input is not False) or (extra_context is not None)):
        err_msg = (
            "You can not use both replay and no_input or extra_context "
            "at the same time."
        )
        raise InvalidModeException(err_msg)


def _run_pre_prompt_hook_if_accepted(repo_dir: str, accept_hooks: bool) -> str:
    """Run the pre_prompt hook when hooks are accepted.

    Return the directory to work with from now on: either the original
    ``repo_dir`` or the temporary copy created by the hook.
    """
    if not accept_hooks:
        return repo_dir
    return str(run_pre_prompt_hook(repo_dir))


def _load_replay_context(
    replay: bool | str, replay_dir: str, template_name: str
) -> tuple[dict[str, Any], str]:
    """Load the replay context and return it with the effective template name.

    If ``replay`` is ``True`` the context is read from ``replay_dir`` using
    ``template_name``. Otherwise ``replay`` is a path to a replay file, whose
    directory and stem replace ``replay_dir`` and ``template_name``.
    """
    if isinstance(replay, bool):
        return load(replay_dir, template_name), template_name

    replay_file_dir, replay_template_name = os.path.split(os.path.splitext(replay)[0])
    return load(replay_file_dir, replay_template_name), replay_template_name


def _context_missing_from_replay(
    generated_context: dict[str, Any], replay_context: dict[str, Any]
) -> dict[str, Any]:
    """Return a context with the variables not present in the replay context."""
    missing_items = {
        key: value
        for key, value in generated_context['cookiecutter'].items()
        if key not in replay_context['cookiecutter']
    }
    return {'cookiecutter': missing_items}


def _public_options(options: dict[str, Any]) -> dict[str, Any]:
    """Return the options whose key does not start with an underscore."""
    return {key: value for key, value in options.items() if not key.startswith("_")}


def _has_nested_templates(context: dict[str, Any]) -> bool:
    """Return True if the context declares nested templates."""
    return any(key in context['cookiecutter'] for key in _NESTED_TEMPLATE_KEYS)


def _add_generation_details(
    cookiecutter_options: dict[str, Any],
    *,
    template: str,
    output_dir: str,
    repo_dir: str,
    checkout: str | None,
) -> None:
    """Store template, output dir, repo dir and checkout in the options."""
    cookiecutter_options['_template'] = template
    cookiecutter_options['_output_dir'] = os.path.abspath(output_dir)
    cookiecutter_options['_repo_dir'] = f"{repo_dir}"
    cookiecutter_options['_checkout'] = checkout


class _patch_import_path_for_repo:  # noqa: N801
    """Context manager that temporarily appends ``repo_dir`` to ``sys.path``."""

    def __init__(self, repo_dir: Path | str) -> None:
        self._repo_dir = f"{repo_dir}" if isinstance(repo_dir, Path) else repo_dir

    def __enter__(self) -> None:
        self._path = copy(sys.path)
        sys.path.append(self._repo_dir)

    def __exit__(self, _type, _value, _traceback):  # type: ignore[no-untyped-def]
        sys.path = self._path
```

## Refactorizaciones aplicadas

- **Extract Function** → `_ensure_replay_mode_is_valid`.
  - **Afecta a:** la validación inicial de modos incompatibles (`replay` con `no_input`/`extra_context`).
  - **Motivo:** dar nombre a una cláusula de guarda y descargar a `cookiecutter()` de un detalle de validación. La condición y el mensaje se mantienen idénticos.

- **Extract Function** + **Remove Dead Code** → `_run_pre_prompt_hook_if_accepted`.
  - **Afecta a:** el bloque `repo_dir, cleanup = base_repo_dir, cleanup_base_repo_dir` seguido del ternario del hook.
  - **Motivo:** la asignación inicial de `cleanup` se sobrescribía siempre en la línea siguiente, así que era código muerto. Ahora la intención es explícita: se ejecuta el hook solo si se aceptan hooks y se devuelve el directorio con el que trabajar. Se conserva la conversión con `str()`, por lo que `cleanup = repo_dir != base_repo_dir` sigue dando el mismo resultado.

- **Extract Function** + **Split Variable** → `_load_replay_context`.
  - **Afecta a:** la carga del contexto de replay y la reasignación oculta de `template_name` dentro de un `if`.
  - **Motivo:** el efecto secundario (al usar un fichero de replay, `template_name` cambia y luego se usa en `dump`) quedaba escondido. Ahora la función devuelve explícitamente `(contexto, template_name)` y se usan variables distintas para la ruta y el nombre del fichero. Las llamadas a `load` siguen siendo posicionales y con los mismos argumentos, y se siguen ejecutando dentro de `import_patch`.

- **Consolidate Duplicate Conditional Fragments** sobre la llamada a `generate_context`.
  - **Afecta a:** las dos ramas `if replay / else`, que repetían la llamada.
  - **Motivo:** eliminar la duplicación. En la rama replay se pasaba `extra_context=None` de forma literal. Gracias a la validación previa, en modo replay `extra_context` es siempre `None`, así que el argumento es equivalente. Lo documenta un comentario. El orden de las trazas de log se conserva.

- **Extract Function** → `_context_missing_from_replay`.
  - **Afecta a:** la construcción de `context_for_prompting` en modo replay (antes, `dict` vacío más asignación posterior).
  - **Motivo:** nombrar la operación: obtener las variables que faltan en el replay y que hay que preguntar.

- **Extract Function** → `_public_options`.
  - **Afecta a:** la comprensión que genera `context['_cookiecutter']`.
  - **Motivo:** expresar la intención (filtrar las opciones privadas) en lugar del mecanismo.

- **Remove Dead Code**.
  - **Afecta a:** el comentario `# print(context['cookiecutter'])`.
  - **Motivo:** era código comentado sin valor.

- **Extract Function** + **Replace Magic Literal** → `_has_nested_templates` y `_NESTED_TEMPLATE_KEYS`.
  - **Afecta a:** la expresión `{"template", "templates"} & set(context["cookiecutter"].keys())`.
  - **Motivo:** hacer legible la condición de plantillas anidadas. La comprobación de pertenencia es equivalente a la intersección de conjuntos.

- **Extract Function** → `_add_generation_details`.
  - **Afecta a:** las cuatro asignaciones `_template`, `_output_dir`, `_repo_dir` y `_checkout`.
  - **Motivo:** agrupar en un paso con nombre propio los metadatos que se añaden al contexto. Se mantiene el orden de inserción, que es relevante para el JSON del replay.

- **Add Docstring** en `_patch_import_path_for_repo`.
  - **Motivo:** documentar su propósito. No cambia su nombre ni su comportamiento: puede reutilizarse en varios `with` como antes.

En todos los casos se ha mantenido la firma pública de `cookiecutter()`. También se conserva la forma exacta de las llamadas a `get_user_config`, `determine_repo_dir`, `run_pre_prompt_hook`, `load`, `dump`, `generate_context`, `choose_nested_template`, `prompt_for_config` y `generate_files`: los mismos argumentos posicionales o con nombre, en el mismo orden. Así, los tests que las sustituyen mediante mocks en `cookiecutter.main` siguen funcionando.

Se ha preservado expresamente un detalle de comportamiento: la llamada recursiva de las plantillas anidadas retorna sin ejecutar la limpieza final, igual que en el código original.