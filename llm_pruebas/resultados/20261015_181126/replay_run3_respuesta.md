```python
"""
cookiecutter.replay.

Persistencia del contexto de generación (*replay*) en ficheros JSON.
-------------------
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from cookiecutter.utils import make_sure_path_exists

if TYPE_CHECKING:
    from pathlib import Path

_REPLAY_FILE_EXTENSION = '.json'
_REQUIRED_CONTEXT_KEY = 'cookiecutter'


def _ensure_context_has_cookiecutter_key(context: dict[str, Any]) -> None:
    """Raise ``ValueError`` if ``context`` lacks the mandatory cookiecutter key."""
    if _REQUIRED_CONTEXT_KEY not in context:
        msg = f'Context is required to contain a {_REQUIRED_CONTEXT_KEY} key'
        raise ValueError(msg)


def get_file_name(replay_dir: Path | str, template_name: str) -> str:
    """Get the name of file."""
    has_extension = template_name.endswith(_REPLAY_FILE_EXTENSION)
    suffix = '' if has_extension else _REPLAY_FILE_EXTENSION
    file_name = f'{template_name}{suffix}'
    return os.path.join(replay_dir, file_name)


def dump(replay_dir: Path | str, template_name: str, context: dict[str, Any]) -> None:
    """Write json data to file."""
    make_sure_path_exists(replay_dir)
    _ensure_context_has_cookiecutter_key(context)

    replay_file = get_file_name(replay_dir, template_name)

    with open(replay_file, 'w', encoding="utf-8") as outfile:
        json.dump(context, outfile, indent=2)


def load(replay_dir: Path | str, template_name: str) -> dict[str, Any]:
    """Read json data from file."""
    replay_file = get_file_name(replay_dir, template_name)

    with open(replay_file, encoding="utf-8") as infile:
        context: dict[str, Any] = json.load(infile)

    _ensure_context_has_cookiecutter_key(context)
    return context
```

## Refactorizaciones aplicadas

- **Extract Function**: `_ensure_context_has_cookiecutter_key` (nueva función privada).
  - **Elementos afectados**: `dump` y `load`.
  - **Motivo**: ambas funciones repetían la misma comprobación de la clave `'cookiecutter'` y el mismo mensaje de error. Ahora la regla vive en un solo lugar y las dos funciones la reutilizan.
  - **Compatibilidad**: se respeta el orden original de las operaciones. En `dump`, el directorio se sigue creando antes de validar. En `load`, la validación se sigue haciendo después de leer el fichero. El mensaje de `ValueError` es idéntico carácter a carácter.

- **Replace Magic Literal**: constantes privadas `_REPLAY_FILE_EXTENSION` y `_REQUIRED_CONTEXT_KEY`.
  - **Elementos afectados**: `get_file_name` y la nueva función de validación.
  - **Motivo**: el literal `'.json'` aparecía dos veces en `get_file_name`, y `'cookiecutter'` se repetía en dos validaciones. Con nombres explícitos queda clara su intención y se evitan inconsistencias si cambian.

- **Decompose Conditional / Introduce Explaining Variable**: variable `has_extension` en `get_file_name`, con la condición expresada en forma positiva.
  - **Motivo**: la versión original usaba una condición negada (`'.json' if not ... else ''`), que obliga a leerla "al revés". Ahora se lee de forma directa: si ya tiene la extensión no se añade sufijo, y si no, se añade `.json`. El resultado es el mismo en todos los casos.

- **Docstring del módulo**: se ha añadido una línea que describe su propósito.
  - **Motivo**: el docstring original solo repetía el nombre del módulo.

Las firmas públicas (`get_file_name`, `dump`, `load`) no cambian, y no se han añadido dependencias.