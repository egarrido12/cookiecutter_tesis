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


def valid_hook(hook_file: str, hook_name: str) -> bool:
    """Determine if a hook file is valid.

    :param hook_file: The hook file to consider for validity
    :param hook_name: The hook to find
    :return: The hook file validity
    """
    filename = os.path.basename(hook_file)
    script_name = os.path.splitext(filename)[0]
    matching_hook = script_name == hook_name
    supported_hook = script_name in _HOOKS
    backup_file = filename.endswith('~')

    return matching_hook and supported_hook and not backup_file


def find_hook(hook_name: str, hooks_dir: str = 'hooks') -> list[str] | None:
    """Return the absolute paths of all scripts provided for the given hook.

    Must be called with the project template as the current working directory.
    Backup files and scripts for other hooks are not included in the result.

    :param hook_name: The hook to find
    :param hooks_dir: The hook directory in the template
    :return: A list with the absolute paths to the hook scripts, or None if
        there are no matching scripts.
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

    Python scripts are run with the current interpreter; any other script
    is executed directly.
    """
    if script_path.endswith('.py'):
        return [sys.executable, script_path]
    return [script_path]


def _os_error_message(err: OSError) -> str:
    """Return a user-friendly message for an OS error raised running a hook."""
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
        except (
            FailedHookException,
            UndefinedError,
        ):
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

    If the template provides a pre_prompt hook, the repository is copied to a
    temporary directory and the hook scripts are executed there.

    :param repo_dir: Project template input directory.
    :return: The temporary directory where the hook was executed, or the
        original ``repo_dir`` if there is no pre_prompt hook.
    """
    with work_in(repo_dir):
        if not find_hook(_PRE_PROMPT_HOOK):
            return repo_dir

    tmp_repo_dir = create_tmp_repo_dir(repo_dir)
    with work_in(tmp_repo_dir):
        scripts = find_hook(_PRE_PROMPT_HOOK) or []
        for script in scripts:
            try:
                run_script(script, str(tmp_repo_dir))
            except FailedHookException as e:  # noqa: PERF203
                msg = 'Pre-Prompt Hook script failed'
                raise FailedHookException(msg) from e
    return tmp_repo_dir
```

## Refactorizaciones aplicadas

- **Replace Magic Literal** (`'pre_prompt'` → `_PRE_PROMPT_HOOK`) en `_HOOKS` y `run_pre_prompt_hook`.
  - **Motivo:** el nombre del hook aparecía repetido como literal en varios puntos. Una constante privada centraliza el valor, evita errores tipográficos y no amplía la API pública.

- **Rename Variable** (`basename` → `script_name` en `valid_hook`).
  - **Motivo:** `basename` describía cómo se calcula el valor, no qué representa, y se confundía con `os.path.basename`. `script_name` expresa que es el nombre del script sin extensión, el que se compara con el nombre del hook.

- **Substitute Algorithm** (`if len(scripts) == 0: return None / return scripts` → `return scripts or None` en `find_hook`).
  - **Motivo:** es equivalente para listas: la lista vacía es falsy y se devuelve `None`. Resulta más conciso e idiomático.

- **Corrección de docstring** de `find_hook`.
  - **Motivo:** la documentación afirmaba que se devolvía un *dict*, cuando la función devuelve una lista de rutas absolutas o `None`. Una documentación incorrecta perjudica la mantenibilidad.

- **Extract Function** (`_build_script_command`, desde `run_script`).
  - **Motivo:** aísla la decisión de cómo invocar el script: con el intérprete actual si es `.py`, o directamente en otro caso. `run_script` queda centrado en ejecutar y gestionar errores.

- **Extract Function** (`_os_error_message`, desde `run_script`).
  - **Motivo:** separa la traducción de `OSError` a un mensaje legible (`ENOEXEC` frente al resto) del flujo principal. El bloque `except` queda en una sola línea.

- **Slide Statements / Split Phase** (comprobación del código de salida en `run_script`).
  - **Cambio:** la comprobación de `exit_status` sale del bloque `try`, que ahora envuelve solo `Popen` y `wait`, las llamadas que pueden lanzar `OSError`.
  - **Motivo:** queda explícito qué se protege con el `except`.
  - **Comportamiento:** no cambia, porque `FailedHookException` no es subclase de `OSError` y nunca era capturada por ese `except`.

- **Extract Function** (`_render_script`, desde `run_script_with_context`).
  - **Motivo:** encapsula la creación del entorno Jinja y el renderizado del contenido del script.
  - **Comportamiento:** el helper se invoca dentro del `with` del fichero temporal, igual que antes. Así se preserva el orden exacto de efectos secundarios: lectura del script, creación del temporal y renderizado.

- **Split Variable / Rename Variable** (en `run_pre_prompt_hook`, `repo_dir` deja de reasignarse y se introduce `tmp_repo_dir`).
  - **Motivo:** el parámetro se reutilizaba para dos conceptos distintos (el directorio original y la copia temporal), lo que dificultaba la lectura.

- **Inline Variable** (variable `scripts` del primer bloque de `run_pre_prompt_hook`).
  - **Motivo:** solo se usaba para comprobar si existía el hook. La condición `if not find_hook(...)` expresa la intención directamente. El `return` dentro de `work_in` restaura el directorio igual que antes, gracias al `finally` del context manager.

- **Ampliación de docstring** de `run_pre_prompt_hook`.
  - **Motivo:** se documentan el uso del directorio temporal y el valor de retorno, que no se mencionaban y son relevantes para quien llama, ya que `main.py` lo usa para decidir la limpieza.

Se mantienen sin cambios:
- Todas las firmas públicas.
- Las constantes `_HOOKS` y `EXIT_SUCCESS`.
- Los nombres importados a nivel de módulo (`subprocess`, `utils`, `rmtree`, `work_in`, `create_tmp_repo_dir`, `create_env_with_context`), para que los tests que los parchean sigan funcionando.
- Los mensajes de log y de error.