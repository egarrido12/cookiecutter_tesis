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
    from collections.abc import Callable

    from jinja2 import Environment

logger = logging.getLogger(__name__)


def force_delete(func: Callable[..., Any], path: str, _exc_info: Any) -> None:
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


def simple_filter(filter_function: Callable[..., Any]) -> type[Extension]:
    """Decorate a function to wrap it in a simplified jinja2 extension."""

    class SimpleFilterExtension(Extension):
        def __init__(self, environment: Environment) -> None:
            super().__init__(environment)
            environment.filters[filter_function.__name__] = filter_function

    SimpleFilterExtension.__name__ = filter_function.__name__
    return SimpleFilterExtension


def create_tmp_repo_dir(repo_dir: Path | str) -> Path:
    """Create a temporary dir with a copy of the contents of repo_dir."""
    resolved_repo_dir = Path(repo_dir).resolve()
    tmp_base_dir = tempfile.mkdtemp(prefix='cookiecutter')
    new_dir = f"{tmp_base_dir}/{resolved_repo_dir.name}"
    logger.debug('Copying repo_dir from %s to %s', resolved_repo_dir, new_dir)
    shutil.copytree(resolved_repo_dir, new_dir)
    return Path(new_dir)


def create_env_with_context(context: dict[str, Any]) -> StrictEnvironment:
    """Create a jinja environment using the provided context."""
    jinja2_env_vars = context.get('cookiecutter', {}).get('_jinja2_env_vars', {})

    return StrictEnvironment(
        context=context, keep_trailing_newline=True, **jinja2_env_vars
    )
```

## Refactorizaciones aplicadas

- **Rename Variable** — `work_in`: `curdir` → `previous_dir`.
  - Motivo: el nombre original sugería "directorio actual", pero la variable guarda el directorio al que se vuelve al salir del contexto. El nuevo nombre expresa ese propósito.

- **Replace Derived Variable with Query / Rename Variable** — `make_executable`: `status` → `current_mode`.
  - Antes se guardaba el objeto `stat_result` completo y solo se usaba `.st_mode`. Ahora se extrae directamente el modo.
  - Motivo: el nombre refleja exactamente el dato que se combina con `stat.S_IEXEC`.

- **Split Variable** — `create_tmp_repo_dir`: el parámetro `repo_dir` ya no se reasigna. El valor resuelto se guarda en `resolved_repo_dir`.
  - Motivo: antes `repo_dir` cambiaba de tipo (`Path | str` → `Path`) y de significado (ruta original → ruta absoluta resuelta). Separarlas evita confusión.
  - El cálculo de `new_dir` se mantiene con la misma f-string a propósito. Cambiarlo a `Path(...) / ...` alteraría el texto del log en Windows por los separadores.

- **Rename Variable** — `create_tmp_repo_dir`: `base_dir` → `tmp_base_dir`.
  - Motivo: deja claro que es el directorio temporal creado por `tempfile.mkdtemp`.

- **Substitute Algorithm (formato de log perezoso)** — `create_tmp_repo_dir`: `logger.debug(f'...')` → `logger.debug('... %s ... %s', ...)`.
  - Motivo: es el estilo que usa el resto del paquete y evita formatear la cadena cuando el nivel DEBUG está desactivado.
  - El mensaje resultante (`record.getMessage()`) es idéntico, porque ambos formatos usan `str()` sobre los argumentos.

- **Rename Variable** — `create_env_with_context`: `envvars` → `jinja2_env_vars`.
  - Motivo: hace coincidir el nombre con la clave `_jinja2_env_vars` del contexto y deja claro que son opciones del entorno Jinja2, no variables de entorno del sistema operativo.

- **Anotaciones de tipo explícitas** (mejora de mantenibilidad complementaria) — `force_delete` y `simple_filter`.
  - Se añaden tipos a los parámetros y se eliminan los comentarios `# type: ignore[no-untyped-def]`.
  - `Callable` se importa solo bajo `TYPE_CHECKING`, así que no hay coste en tiempo de ejecución.
  - Los nombres de los parámetros (`func`, `path`, `_exc_info`, `filter_function`) no cambian, así que las firmas públicas son las mismas.

**Cambios descartados deliberadamente para preservar el comportamiento:**
- No se reemplaza `onerror=` por `onexc=` en `rmtree`. Exigiría bifurcar por versión de Python y cambiaría qué advertencias se emiten.
- En `simple_filter` no se captura `filter_function.__name__` en una variable en el momento de decorar. Hoy el filtro se registra con el nombre leído al instanciar la extensión, y capturarlo antes cambiaría ese momento.