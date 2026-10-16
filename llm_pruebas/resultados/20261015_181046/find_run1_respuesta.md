```python
"""Functions for finding Cookiecutter templates and other components."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from cookiecutter.exceptions import NonTemplatedInputDirException

if TYPE_CHECKING:
    from jinja2 import Environment

logger = logging.getLogger(__name__)


def _is_project_template_name(entry_name: str, env: Environment) -> bool:
    """Check whether ``entry_name`` looks like a project template name.

    A project template name contains the word ``cookiecutter`` and both the
    variable start and end delimiters of the Jinja2 environment, e.g.
    ``{{cookiecutter.project_slug}}``.

    :param entry_name: Name of an entry in the repository directory.
    :param env: Jinja2 environment whose delimiters are used for the check.
    :return: True if the name matches a project template name, else False.
    """
    return (
        'cookiecutter' in entry_name
        and env.variable_start_string in entry_name
        and env.variable_end_string in entry_name
    )


def find_template(repo_dir: Path | str, env: Environment) -> Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    :param repo_dir: Local directory of newly cloned repo.
    :param env: Jinja2 environment used to recognise templated names.
    :return: Path to project template, built from ``repo_dir``.
    :raises NonTemplatedInputDirException: If no project template is found.
    """
    logger.debug('Searching %s for the project template.', repo_dir)

    for entry_name in os.listdir(repo_dir):
        if _is_project_template_name(entry_name, env):
            project_template = Path(repo_dir, entry_name)
            logger.debug('The project template appears to be %s', project_template)
            return project_template

    raise NonTemplatedInputDirException
```

## Refactorizaciones aplicadas

- **Extract Function** (`_is_project_template_name`, a partir de la condición compuesta del `if` en `find_template`): la triple condición expresaba una regla del dominio ("cómo reconocer el nombre de una plantilla de proyecto") sin darle nombre. Ahora esa regla tiene nombre y docstring propios y se puede leer y probar por separado. La función es privada, así que la API pública no cambia.

- **Replace Control Flag / Simplificar el flujo de control** (el `for ... else` y la variable intermedia de `find_template`): se sustituyó el patrón `for/break/else` por un *early return* dentro del bucle y un `raise` al final. El `for ... else` es una construcción poco conocida y fácil de malinterpretar.
  - El comportamiento se mantiene idéntico: se devuelve la primera coincidencia en el orden de `os.listdir`.
  - El segundo `logger.debug` se sigue emitiendo solo cuando hay coincidencia.
  - Si no hay ninguna, se lanza la misma excepción, `NonTemplatedInputDirException`.

- **Rename Variable** (`str_path` → `entry_name`): `str_path` sugería una ruta, pero `os.listdir` devuelve solo nombres de entradas, que pueden ser archivos o directorios, y no rutas. El nuevo nombre describe con exactitud su contenido.

- **Mejora de documentación** (docstring de `find_template`): se añadieron `:param env:` y `:raises NonTemplatedInputDirException:`, que faltaban. También se corrigió `:return:`: el valor se construye a partir de `repo_dir` y no es necesariamente relativo. Es un cambio solo de documentación, sin efecto en el comportamiento.