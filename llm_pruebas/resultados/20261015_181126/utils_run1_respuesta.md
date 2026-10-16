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

_TMP_REPO_DIR_PREFIX = 'cookiecutter'


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
    resolved_repo_dir = Path(repo_dir).resolve()
    base_dir = tempfile.mkdtemp(prefix=_TMP_REPO_DIR_PREFIX)
    tmp_repo_dir = f"{base_dir}/{resolved_repo_dir.name}"
    logger.debug('Copying repo_dir from %s to %s', resolved_repo_dir, tmp_repo_dir)
    shutil.copytree(resolved_repo_dir, tmp_repo_dir)
    return Path(tmp_repo_dir)


def create_env_with_context(context: dict[str, Any]) -> StrictEnvironment:
    """Create a jinja environment using the provided context."""
    jinja2_env_vars = context.get('cookiecutter', {}).get('_jinja2_env_vars', {})

    return StrictEnvironment(
        context=context, keep_trailing_newline=True, **jinja2_env_vars
    )
```

## Refactorizaciones aplicadas

- **Split Variable** — `create_tmp_repo_dir`: el parámetro `repo_dir` se reasignaba a un valor de otro tipo (`Path | str` → `Path` resuelto). Ahora el valor resuelto se guarda en una variable nueva, `resolved_repo_dir`, y el parámetro no se modifica. Motivo: evitar que una misma variable tenga dos significados y dos tipos distintos según la línea, lo que confunde al lector y a los type checkers.

- **Rename Variable** — `create_tmp_repo_dir`: `new_dir` → `tmp_repo_dir`. Motivo: el nombre indica que se trata de la copia temporal del repositorio, y no de un directorio "nuevo" genérico.

- **Replace Magic Literal (Extract Constant)** — `create_tmp_repo_dir`: el literal `'cookiecutter'` pasado como `prefix` a `tempfile.mkdtemp` pasa a ser la constante privada `_TMP_REPO_DIR_PREFIX`. Motivo: documenta la intención del valor y lo deja en un único punto si hubiera que cambiarlo.

- **Logging diferido** (sustitución de f-string por argumentos `%s`) — `create_tmp_repo_dir`, en la llamada a `logger.debug`. Motivo: hace el código coherente con el resto del módulo (`make_sure_path_exists` ya usaba este estilo) y evita formatear el mensaje cuando el nivel DEBUG está desactivado. El mensaje final (`record.getMessage()`) es idéntico al original.

- **Rename Variable** — `work_in`: `curdir` → `previous_dir`. Motivo: `curdir` puede confundirse con `os.curdir` (que vale `'.'`). El nuevo nombre explica que es el directorio al que se vuelve al salir del contexto.

- **Inline Variable + Rename Variable** — `make_executable`: `status` (el resultado completo de `os.stat`) se sustituye por `current_mode = os.stat(script_path).st_mode`. Motivo: solo se usa el modo, y el nombre ahora describe exactamente lo que se combina con `stat.S_IEXEC`.

- **Extract Variable** — `simple_filter`: `filter_function.__name__` se calculaba dos veces y ahora se guarda en `filter_name`. Motivo: elimina la duplicación y deja claro que el nombre del filtro y el nombre de la clase generada son el mismo valor.

- **Rename Variable** — `create_env_with_context`: `envvars` → `jinja2_env_vars`. Motivo: `envvars` sugiere variables de entorno del sistema operativo. En realidad son opciones del `Environment` de Jinja2, leídas de la clave `_jinja2_env_vars`.

No se ha modificado ningún nombre, firma ni parámetro de las funciones públicas (`force_delete`, `rmtree`, `make_sure_path_exists`, `work_in`, `make_executable`, `simple_filter`, `create_tmp_repo_dir`, `create_env_with_context`). Tampoco se han añadido dependencias.

En dos puntos se ha mantenido el código original a propósito para no alterar el comportamiento:
- `onerror=force_delete` en `rmtree`: no se ha migrado a `onexc`, para conservar la compatibilidad con versiones de Python anteriores a la 3.12.
- La ruta temporal se sigue construyendo con `f"{base_dir}/{...}"`: no se ha cambiado a `Path(base_dir) / ...`, para que el mensaje de log y la cadena pasada a `copytree` sean exactamente los mismos en todas las plataformas.