```python
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
```

## Refactorizaciones aplicadas

- **Rename Variable** — `work_in`: `curdir` → `previous_dir`.
  - Motivo: el nombre original sugiere "directorio actual". En realidad la variable guarda el directorio al que hay que volver al salir del contexto. El nuevo nombre expresa esa intención.

- **Inline Variable + Rename Variable** — `make_executable`: `status` → `current_mode`.
  - Antes se guardaba el resultado completo de `os.stat` en una variable y solo se usaba su atributo `st_mode`.
  - Motivo: ahora la variable contiene directamente el modo de permisos, que es lo único que interesa. La línea de `os.chmod` se lee como "modo actual + bit de ejecución".

- **Extract Variable** — `simple_filter`: `filter_function.__name__` → `filter_name`.
  - Motivo: la expresión aparecía dos veces, como clave del filtro y como nombre de la clase generada. Extraerla hace explícito que ambos usos deben coincidir y elimina la duplicación.
  - El comportamiento no cambia: el nombre se lee una sola vez, en el momento de decorar, igual que antes.

- **Split Variable / Remove Assignments to Parameters** — `create_tmp_repo_dir`:
  - El parámetro `repo_dir` ya no se reasigna; se introduce `source_repo_dir` para la ruta resuelta.
  - `base_dir` se renombra a `tmp_base_dir` y `new_dir` a `tmp_repo_dir`.
  - Motivo: reasignar el parámetro con otro tipo (`Path | str` → `Path`) dificulta razonar sobre el código. Los nuevos nombres distinguen claramente el origen de la copia del destino temporal.
  - La construcción de la ruta con `f"{...}/{...}"` se mantiene tal cual, para que la ruta y el mensaje de log sean idénticos en todas las plataformas.

- **Sustituir f-string en logging por argumentos diferidos** — `create_tmp_repo_dir`, llamada a `logger.debug`.
  - Motivo: es el estilo que usa el resto del módulo y del paquete (`'... %s', path`). Evita formatear el mensaje cuando el nivel DEBUG está desactivado.
  - El texto final (`record.getMessage()`) es idéntico al original.

- **Replace Magic Literal (con constante privada) + Extract Variable + Rename Variable** — `create_env_with_context`:
  - Se introduce `_JINJA2_ENV_VARS_KEY` con un comentario que explica su significado.
  - Se separa la obtención del sub-diccionario `cookiecutter_context`.
  - `envvars` se renombra a `jinja2_env_vars`.
  - Motivo: la cadena `'_jinja2_env_vars'` es una clave del contexto con significado propio. Nombrarla documenta el contrato. Dividir el encadenamiento de `.get()` y usar un nombre descriptivo aclara que son argumentos para el entorno Jinja2 y no variables de entorno del sistema.
  - La constante es privada (prefijo `_`), así que no amplía la API pública.

**Cambios descartados a propósito, para preservar el comportamiento y la compatibilidad:**

- No he sustituido `onerror` por `onexc` en `rmtree`. `onexc` solo existe desde Python 3.12 y además cambia la firma del manejador `force_delete`.
- No he tocado las firmas públicas, incluidos los nombres de parámetros como `_exc_info` y `filter_function`.
- No he modificado los mensajes de error ni de log, salvo la forma de pasar los argumentos indicada arriba.