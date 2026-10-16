```python
"""Functions for discovering and executing various cookiecutter hooks."""

from __future__ import annotations

import errno
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jinja2.exceptions import UndefinedError

from cookiecutter import utils
from cookiecutter.exceptions import FailedHookException
from cookiecutter.utils import (
    create_env_with_context,
    create_tmp_repo_dir,
    rmtree,
    work_in,
)

logger = logging.getLogger(__name__)

_PRE_PROMPT_HOOK = 'pre_prompt'
_HOOKS = [
    _PRE_PROMPT_HOOK,
    'pre_gen_project',
    'post_gen_project',
]
EXIT_SUCCESS = 0

# Errors that abort project generation when raised while running a hook.
_HOOK_FAILURE_ERRORS = (
    FailedHookException,
    UndefinedError,
)


def valid_hook(hook_file: str, hook_name: str) -> bool:
    """Determine if a hook file is valid.

    :param hook_file: The hook file to consider for validity
    :param hook_name: The hook to find
    :return: The hook file validity
    """
    filename = os.path.basename(hook_file)
    basename = os.path.splitext(filename)[0]
    matching_hook = basename == hook_name
    supported_hook = basename in _HOOKS
    backup_file = filename.endswith('~')

    return matching_hook and supported_hook and not backup_file


def find_hook(hook_name: str, hooks_dir: str = 'hooks') -> list[str] | None:
    """Return the absolute paths of all scripts provided for the given hook.

    Must be called with the project template as the current working directory.
    Only files inside ``hooks_dir`` that are valid scripts for ``hook_name``
    (see :func:`valid_hook`) are included.

    :param hook_name: The hook to find
    :param hooks_dir: The hook directory in the template
    :return: A list with the absolute paths to the hook scripts, or None if
        there is no hooks directory or no matching script.
    """
    logger.debug('hooks_dir is %s', os.path.abspath(hooks_dir))

    if not os.path.isdir(hooks_dir):
        logger.debug('No hooks/dir in template_dir')
        return None

    scripts = [
        os.path.abspath(os.path.join(hooks_dir, hook_file))
        for hook_file in os.listdir(hooks_dir)
        if valid_hook(hook_file, hook_name)
    ]

    return scripts or None


def _build_script_command(script_path: str) -> list[str]:
    """Return the command line needed to execute the given script.

    Python scripts are run with the current interpreter; any other script is
    executed directly.
    """
    if script_path.endswith('.py'):
        return [sys.executable, script_path]
    return [script_path]


def _os_error_message(err: OSError) -> str:
    """Return a user friendly message for an OS error raised by a hook script."""
    if err.errno == errno.ENOEXEC:
        return 'Hook script failed, might be an empty file or missing a shebang'
    return f'Hook script failed (error: {err})'


def run_script(script_path: str, cwd: Path | str = '.') -> None:
    """Execute a script from a working directory.

    :param script_path: Absolute path to the script to run.
    :param cwd: The directory to run the script from.
    """
    run_thru_shell = sys.platform.startswith('win')
    script_command = _build_script_command(script_path)

    utils.make_executable(script_path)

    try:
        proc = subprocess.Popen(script_command, shell=run_thru_shell, cwd=cwd)  # nosec
        exit_status = proc.wait()
    except OSError as err:
        raise FailedHookException(_os_error_message(err)) from err

    if exit_status != EXIT_SUCCESS:
        msg = f'Hook script failed (exit status: {exit_status})'
        raise FailedHookException(msg)


def _render_script(contents: str, context: dict[str, Any]) -> str:
    """Render the contents of a hook script with Jinja using the given context."""
    env = create_env_with_context(context)
    template = env.from_string(contents)
    return template.render(**context)


def run_script_with_context(
    script_path: Path | str, cwd: Path | str, context: dict[str, Any]
) -> None:
    """Execute a script after rendering it with Jinja.

    :param script_path: Absolute path to the script to run.
    :param cwd: The directory to run the script from.
    :param context: Cookiecutter project template context.
    """
    _, extension = os.path.splitext(script_path)

    contents = Path(script_path).read_text(encoding='utf-8')

    with tempfile.NamedTemporaryFile(delete=False, mode='wb', suffix=extension) as temp:
        rendered_script = _render_script(contents, context)
        temp.write(rendered_script.encode('utf-8'))

    run_script(temp.name, cwd)


def run_hook(hook_name: str, project_dir: Path | str, context: dict[str, Any]) -> None:
    """
    Try to find and execute a hook from the specified project directory.

    :param hook_name: The hook to execute.
    :param project_dir: The directory to execute the script from.
    :param context: Cookiecutter project context.
    """
    scripts = find_hook(hook_name)
    if not scripts:
        logger.debug('No %s hook found', hook_name)
        return
    logger.debug('Running hook %s', hook_name)
    for script in scripts:
        run_script_with_context(script, project_dir, context)


def run_hook_from_repo_dir(
    repo_dir: Path | str,
    hook_name: str,
    project_dir: Path | str,
    context: dict[str, Any],
    delete_project_on_failure: bool,
) -> None:
    """Run hook from repo directory, clean project directory if hook fails.

    :param repo_dir: Project template input directory.
    :param hook_name: The hook to execute.
    :param project_dir: The directory to execute the script from.
    :param context: Cookiecutter project context.
    :param delete_project_on_failure: Delete the project directory on hook
        failure?
    """
    with work_in(repo_dir):
        try:
            run_hook(hook_name, project_dir, context)
        except _HOOK_FAILURE_ERRORS:
            if delete_project_on_failure:
                rmtree(project_dir)
            logger.exception(
                "Stopping generation because %s hook "
                "script didn't exit successfully",
                hook_name,
            )
            raise


def run_pre_prompt_hook(repo_dir: Path | str) -> Path | str:
    """Run pre_prompt hook from repo directory.

    The hook is executed inside a temporary copy of the repository, so the
    original template is never modified.

    :param repo_dir: Project template input directory.
    :return: The temporary copy of the repository if a pre_prompt hook was
        run, otherwise the original ``repo_dir``.
    """
    with work_in(repo_dir):
        if not find_hook(_PRE_PROMPT_HOOK):
            return repo_dir

    tmp_repo_dir = create_tmp_repo_dir(repo_dir)
    with work_in(tmp_repo_dir):
        scripts = find_hook(_PRE_PROMPT_HOOK) or []
        try:
            for script in scripts:
                run_script(script, str(tmp_repo_dir))
        except FailedHookException as e:
            msg = 'Pre-Prompt Hook script failed'
            raise FailedHookException(msg) from e
    return tmp_repo_dir
```

## Refactorizaciones aplicadas

- **Extract Function** – `_build_script_command` (extraída de `run_script`).
  - Motivo: aísla la decisión de cómo invocar el script (intérprete de Python o ejecución directa). Así `run_script` se lee como una secuencia de pasos de alto nivel.

- **Extract Function** – `_os_error_message` (extraída del `except OSError` de `run_script`).
  - Motivo: separa la traducción del `OSError` a un mensaje legible de la lógica de ejecución.
  - El handler queda en una sola línea, que siempre encadena la causa con `from err`, igual que antes.

- **Slide Statements / reducción del bloque `try`** – en `run_script`, la comprobación de `exit_status` sale del `try`.
  - Motivo: el `try` ahora solo envuelve lo que puede lanzar `OSError` (`Popen` y `wait`).
  - El comportamiento no cambia: `FailedHookException` no es subclase de `OSError`, así que nunca la capturaba ese `except`. Tampoco tenía ni tiene excepción de contexto encadenada.

- **Extract Function** – `_render_script` (extraída de `run_script_with_context`).
  - Motivo: nombra explícitamente el paso "renderizar el script con Jinja".
  - Se invoca dentro del mismo bloque `with tempfile...` que antes, para conservar el orden exacto de los efectos secundarios: el fichero temporal se crea antes de renderizar.

- **Split Variable / Rename Variable** – en `run_pre_prompt_hook`, el parámetro `repo_dir` ya no se reasigna; la copia temporal se guarda en `tmp_repo_dir`.
  - Motivo: antes la misma variable representaba primero el repositorio original y luego la copia temporal, lo que dificultaba entender qué directorio se usaba en cada punto.

- **Inline Variable** – la primera variable `scripts` de `run_pre_prompt_hook` se sustituye por `if not find_hook(...)`.
  - Motivo: solo servía para la comprobación inmediata.

- **Move Statements (try fuera del bucle)** – en `run_pre_prompt_hook`, el `try/except FailedHookException` envuelve ahora el bucle completo en lugar de cada iteración.
  - Es equivalente porque el primer fallo ya interrumpía el bucle al relanzar la excepción.
  - Se elimina la necesidad del `# noqa: PERF203`.

- **Replace Magic Literal** – `_PRE_PROMPT_HOOK` y `_HOOK_FAILURE_ERRORS`.
  - El literal `'pre_prompt'` aparecía repetido (en `_HOOKS` y dos veces en `run_pre_prompt_hook`).
  - La tupla de excepciones que abortan la generación queda nombrada.
  - Ambas constantes son privadas, así que no alteran la API pública. `_HOOKS` y `EXIT_SUCCESS` se mantienen con su nombre y valor.

- **Simplify Conditional Expression** – en `find_hook`, `if len(scripts) == 0: return None / return scripts` pasa a `return scripts or None`.
  - Es equivalente para una lista: devuelve `None` si está vacía y la propia lista en caso contrario.

- **Corrección de documentación** (no altera código):
  - El docstring de `find_hook` describía un `dict` que la función nunca devolvió. Ahora documenta la lista de rutas o `None`.
  - Se amplió el docstring de `run_pre_prompt_hook` para explicar qué valor devuelve en cada caso.

**Compatibilidad con los tests:** no se han cambiado nombres, firmas ni puntos de "parcheo" habituales en los tests. Se siguen usando `utils.make_executable`, `subprocess.Popen`, `find_hook`, `run_script`, `create_tmp_repo_dir`, `work_in` y `rmtree` a través de los mismos nombres de módulo.