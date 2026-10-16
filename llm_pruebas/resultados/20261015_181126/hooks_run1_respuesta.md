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

_HOOKS = [
    'pre_prompt',
    'pre_gen_project',
    'post_gen_project',
]
_PRE_PROMPT_HOOK = 'pre_prompt'
EXIT_SUCCESS = 0


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
    Only files inside ``hooks_dir`` whose name (without extension) matches
    ``hook_name`` are considered; backup files are ignored.

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
    """Return the command needed to execute the given script.

    Python scripts are run with the current interpreter; any other script is
    executed directly.
    """
    if script_path.endswith('.py'):
        return [sys.executable, script_path]
    return [script_path]


def _describe_os_error(err: OSError) -> str:
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
        raise FailedHookException(_describe_os_error(err)) from err

    if exit_status != EXIT_SUCCESS:
        msg = f'Hook script failed (exit status: {exit_status})'
        raise FailedHookException(msg)


def _render_script(contents: str, context: dict[str, Any]) -> str:
    """Render the contents of a hook script as a Jinja template."""
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
        except (FailedHookException, UndefinedError):
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

    The hook scripts are run inside a temporary copy of the repository, whose
    path is returned. If the repository has no pre_prompt hook, ``repo_dir``
    is returned unchanged.

    :param repo_dir: Project template input directory.
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

- **Extract Function** – `_build_script_command` (desde `run_script`).
  Saca de `run_script` la decisión de cómo invocar el script: con el intérprete actual si es `.py`, directamente en otro caso. Así `run_script` solo orquesta la ejecución.

- **Extract Function** – `_describe_os_error` (desde el `except OSError` de `run_script`).
  Aísla cómo se traduce un `OSError` a un mensaje legible. El manejador de la excepción queda en una sola línea, y los dos mensajes posibles (`ENOEXEC` y genérico) se mantienen idénticos.

- **Split Phase / Slide Statements** – comprobación del código de salida en `run_script`.
  Antes, `raise FailedHookException` por código de salida distinto de cero estaba dentro del `try` que captura `OSError`. Ahora queda fuera, de modo que el `try` cubre solo lo que realmente puede lanzar `OSError` (`Popen` y `wait`).
  El comportamiento es el mismo porque `FailedHookException` no hereda de `OSError`, así que nunca fue capturada por ese `except`.

- **Extract Function** – `_render_script` (desde `run_script_with_context`).
  Encapsula la creación del entorno Jinja y el renderizado del contenido del hook. Se sigue invocando dentro del `with NamedTemporaryFile(...)`, con el mismo orden de operaciones que el original: si el renderizado falla, el fichero temporal ya se ha creado, igual que antes.

- **Rename Variable** – en `run_pre_prompt_hook`, el `repo_dir` reasignado pasa a ser `tmp_repo_dir`.
  El parámetro `repo_dir` se reutilizaba para guardar un valor distinto: la copia temporal, de tipo `Path`. Con un nombre propio queda claro qué directorio se usa en cada momento. El valor devuelto es el mismo.

- **Inline Variable** – `scripts` en la primera comprobación de `run_pre_prompt_hook`.
  Esa variable solo se usaba para comprobar si existía el hook. Se evalúa `find_hook(...)` directamente en el `if`.

- **Replace Magic Literal** – nueva constante privada `_PRE_PROMPT_HOOK` para el literal `'pre_prompt'`, que se repetía en `run_pre_prompt_hook`.
  Evita duplicar la cadena. La lista pública `_HOOKS` no cambia.

- **Slide Statements** – el `try/except FailedHookException` de `run_pre_prompt_hook` pasa a envolver el bucle en lugar de estar dentro de él.
  El resultado es equivalente: el primer fallo interrumpe la ejecución y relanza el mismo `FailedHookException('Pre-Prompt Hook script failed')` encadenado. Además desaparece la necesidad del `# noqa: PERF203`.

- **Substitute Algorithm** – `if len(scripts) == 0: return None; return scripts` se sustituye por `return scripts or None` en `find_hook`.
  Es más idiomático y devuelve exactamente lo mismo: `None` para la lista vacía y la lista en otro caso.

- **Corrección de documentación** – docstrings de `find_hook` y `run_pre_prompt_hook`.
  El docstring de `find_hook` decía que devolvía un diccionario, pero devuelve una lista de rutas absolutas o `None`. El de `run_pre_prompt_hook` ahora explica qué ruta devuelve.

- **Reformat** – la tupla de excepciones en `run_hook_from_repo_dir` pasa a una sola línea para mejorar la legibilidad, sin cambio funcional.

Lo que no cambia:
- **Interfaz pública:** se conservan todas las firmas y nombres públicos (`valid_hook`, `find_hook`, `run_script`, `run_script_with_context`, `run_hook`, `run_hook_from_repo_dir`, `run_pre_prompt_hook`, `EXIT_SUCCESS`, `logger`) y el nombre privado `_HOOKS`.
- **Imports:** se mantienen los nombres importados a nivel de módulo (`utils`, `rmtree`, `work_in`, `create_env_with_context`, `create_tmp_repo_dir`, `subprocess`, etc.), para que los `mock.patch` existentes en los tests sigan funcionando.