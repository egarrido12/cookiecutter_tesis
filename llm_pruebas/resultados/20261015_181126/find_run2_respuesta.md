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
    """Check whether ``entry_name`` looks like a templated project directory.

    A project template directory name must contain the word ``cookiecutter``
    and must be wrapped in the Jinja2 variable delimiters configured in
    ``env``, e.g. ``{{cookiecutter.project_slug}}``.

    :param entry_name: Name of a child entry of the repository directory.
    :param env: Jinja2 environment providing the variable delimiters.
    :return: True if ``entry_name`` is a templated project directory name.
    """
    return (
        'cookiecutter' in entry_name
        and env.variable_start_string in entry_name
        and env.variable_end_string in entry_name
    )


def find_template(repo_dir: Path | str, env: Environment) -> Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    :param repo_dir: Local directory of newly cloned repo.
    :param env: Jinja2 environment providing the variable delimiters.
    :return: Path to project template (relative if ``repo_dir`` is relative).
    :raises NonTemplatedInputDirException: If no child entry of ``repo_dir``
        is a templated project directory.
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

- **Extract Function**: la condición compuesta del `if` pasa a la función privada `_is_project_template_name(entry_name, env)`.
  - **Motivo**: la condición de tres cláusulas expresaba una regla de negocio implícita: qué es un nombre de directorio de plantilla. Con un nombre propio y su docstring, la intención se lee directamente en `find_template`. Además, la regla queda aislada para modificarla o probarla por separado.
  - **Comportamiento**: se conservan el orden de evaluación y el cortocircuito de las comprobaciones.

- **Rename Variable**: `str_path` pasa a llamarse `entry_name`.
  - **Motivo**: `os.listdir` devuelve nombres de entradas, no rutas. El nombre anterior inducía a pensar en una ruta completa y además incluía el tipo (`str_`) en el identificador.

- **Replace Control Flag / for-else with Guard Clause** (retorno temprano en lugar de `for ... break ... else`).
  - **Cambio**: al encontrar la plantilla, se registra el mensaje de depuración y se retorna dentro del bucle. Si el bucle termina sin coincidencias, se lanza la excepción.
  - **Motivo**: la construcción `for/else` con `break` es poco conocida y obliga a seguir la variable `project_template` fuera del bucle. El retorno temprano hace el flujo lineal y evidente.
  - **Comportamiento**: idéntico. Se recorre `os.listdir` en el mismo orden, se elige la primera coincidencia y se emiten los mismos mensajes de log en el mismo orden. También se lanza la misma excepción, sin instanciar, igual que en el original.

- **Mejora de documentación** (sin impacto en el comportamiento): el docstring de `find_template` ahora documenta:
  - el parámetro `env`, que antes no estaba descrito;
  - la excepción que puede lanzarse;
  - que la ruta devuelta es relativa solo si `repo_dir` lo es.

  La firma pública de `find_template` no cambia.