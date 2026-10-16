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

_PROJECT_TEMPLATE_MARKER = 'cookiecutter'


def _is_project_template_name(name: str, env: Environment) -> bool:
    """Check whether ``name`` looks like a templated project directory name.

    A project template directory name must contain the word ``cookiecutter``
    and both Jinja2 variable delimiters configured in ``env``
    (e.g. ``{{cookiecutter.project_slug}}``).

    :param name: Name of an entry inside the repository directory.
    :param env: Jinja2 environment providing the variable delimiters.
    :return: True if ``name`` matches the project template pattern.
    """
    return (
        _PROJECT_TEMPLATE_MARKER in name
        and env.variable_start_string in name
        and env.variable_end_string in name
    )


def find_template(repo_dir: Path | str, env: Environment) -> Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    The first entry of ``repo_dir`` (in ``os.listdir`` order) whose name
    matches the project template pattern is selected.

    :param repo_dir: Local directory of newly cloned repo.
    :param env: Jinja2 environment providing the variable delimiters.
    :return: Path to the project template, built by joining ``repo_dir``
        with the name of the template directory.
    :raises NonTemplatedInputDirException: If no entry matches the pattern.
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

- **Extract Function** (`_is_project_template_name`): la condición compuesta de tres cláusulas del `if` se movió a una función privada con nombre descriptivo. Así `find_template` se lee como "recorre las entradas y devuelve la primera que sea plantilla de proyecto". Además, la regla de reconocimiento queda documentada y aislada en un solo lugar. Al ser privada (prefijo `_`), no amplía la API pública.

- **Replace Magic Literal** (`_PROJECT_TEMPLATE_MARKER`): el literal `'cookiecutter'` pasó a ser una constante privada de módulo. Su nombre explica por qué se busca esa palabra en el nombre del directorio.

- **Replace Control Flag / Simplify Loop** (sustituir `for … else` + `break` por *early return*): el original usaba la construcción `for/else` (poco intuitiva para muchos lectores) junto con una variable `project_template` que solo existía si se había ejecutado el `break`. Ahora la función retorna en cuanto encuentra la plantilla y lanza la excepción al salir del bucle. El comportamiento es idéntico:
  - se recorre `os.listdir(repo_dir)` en el mismo orden y se elige la primera coincidencia;
  - se emiten los mismos mensajes de log, en el mismo orden;
  - se devuelve el mismo `Path(repo_dir, nombre)`;
  - si no hay coincidencia, se lanza `NonTemplatedInputDirException` igual que antes (sin argumentos).

- **Rename Variable** (`str_path` → `entry_name`): la variable no contiene una ruta, sino el nombre de una entrada devuelta por `os.listdir`. El nuevo nombre refleja con precisión su contenido.

- **Docstring de `find_template`** (mejora de documentación, no catalogada en Fowler): se documentaron el parámetro `env`, la excepción que se lanza y el criterio de selección (primera coincidencia). También se corrigió la descripción del valor de retorno: decía "ruta relativa", pero en realidad es `repo_dir` unido al nombre del directorio, que es absoluta si `repo_dir` lo es.

La firma pública `find_template(repo_dir, env) -> Path` no cambia, y se mantienen los imports en tiempo de ejecución (`os`, `Path`) y el `logger` con el mismo nombre de módulo.