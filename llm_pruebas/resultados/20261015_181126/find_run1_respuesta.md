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

_TEMPLATE_DIR_KEYWORD = 'cookiecutter'


def _is_project_template_dir_name(name: str, env: Environment) -> bool:
    """Check whether ``name`` looks like a templated project directory.

    A project template directory name must contain the word ``cookiecutter``
    and the Jinja2 variable delimiters configured in ``env`` (by default
    ``{{`` and ``}}``).

    :param name: Name of an entry inside the repository directory.
    :param env: Jinja2 environment that provides the variable delimiters.
    :return: True if ``name`` matches a project template directory name.
    """
    return (
        _TEMPLATE_DIR_KEYWORD in name
        and env.variable_start_string in name
        and env.variable_end_string in name
    )


def find_template(repo_dir: Path | str, env: Environment) -> Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    :param repo_dir: Local directory of newly cloned repo.
    :param env: Jinja2 environment used to know the variable delimiters.
    :return: Path to the project template, built from ``repo_dir`` and the
        name of the matching child entry.
    :raises NonTemplatedInputDirException: If no child entry of ``repo_dir``
        looks like a project template.
    """
    logger.debug('Searching %s for the project template.', repo_dir)

    for entry_name in os.listdir(repo_dir):
        if _is_project_template_dir_name(entry_name, env):
            project_template = Path(repo_dir, entry_name)
            logger.debug('The project template appears to be %s', project_template)
            return project_template

    raise NonTemplatedInputDirException
```

## Refactorizaciones aplicadas

- **Extract Function**: la condición compuesta del `if` se ha movido a la nueva función privada `_is_project_template_dir_name(name, env)`.
  - **Motivo:** la regla para reconocer un directorio de plantilla queda nombrada y documentada, y se puede leer o modificar de forma aislada.
  - **Comportamiento:** se conserva el orden de evaluación de las tres comprobaciones y su cortocircuito.

- **Replace Magic Literal**: el literal `'cookiecutter'` de la condición ahora es la constante privada `_TEMPLATE_DIR_KEYWORD`.
  - **Motivo:** se hace explícito que es la palabra clave que debe aparecer en el nombre del directorio de plantilla.

- **Rename Variable**: `str_path` pasa a llamarse `entry_name` en `find_template`.
  - **Motivo:** `os.listdir` devuelve nombres de entradas, no rutas. El nuevo nombre describe mejor el contenido.

- **Replace Control Flag / for-else con retorno anticipado (Return Early)**: se ha eliminado la estructura `for ... break ... else: raise` de `find_template`.
  - **Cambio:** la función ahora devuelve en cuanto encuentra la plantilla y lanza la excepción después del bucle.
  - **Motivo:** el `for/else` es una construcción poco intuitiva. Con el retorno anticipado el flujo es lineal y ya no hace falta que `project_template` sobreviva fuera del bucle.
  - **Comportamiento:** el mensaje de log, el valor devuelto y la excepción lanzada son idénticos, y la excepción se sigue lanzando como clase sin argumentos.

- **Docstrings**:
  - En `find_template` se documenta el parámetro `env`, que antes no aparecía.
  - Se corrige la descripción del valor de retorno: no es necesariamente una ruta relativa, sino `repo_dir` unido al nombre de la entrada.
  - Se documenta la excepción `NonTemplatedInputDirException`.
  - **Motivo:** que la documentación refleje fielmente el comportamiento real.