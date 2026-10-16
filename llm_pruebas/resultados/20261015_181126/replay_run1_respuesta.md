```python
"""Persist and restore the context used to generate a project (replay).

Cookiecutter stores the final context in a JSON file inside the replay
directory. That file can later be used to regenerate the project without
asking the user again.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from cookiecutter.utils import make_sure_path_exists

if TYPE_CHECKING:
    from pathlib import Path

_JSON_EXTENSION = '.json'
_REQUIRED_CONTEXT_KEY = 'cookiecutter'


def _validate_context(context: dict[str, Any]) -> None:
    """Raise ``ValueError`` if the context lacks the ``cookiecutter`` key."""
    if _REQUIRED_CONTEXT_KEY not in context:
        msg = 'Context is required to contain a cookiecutter key'
        raise ValueError(msg)


def get_file_name(replay_dir: Path | str, template_name: str) -> str:
    """Get the name of file."""
    suffix = '' if template_name.endswith(_JSON_EXTENSION) else _JSON_EXTENSION
    replay_file_name = f'{template_name}{suffix}'
    return os.path.join(replay_dir, replay_file_name)


def dump(replay_dir: Path | str, template_name: str, context: dict[str, Any]) -> None:
    """Write json data to file."""
    make_sure_path_exists(replay_dir)
    _validate_context(context)

    replay_file = get_file_name(replay_dir, template_name)

    with open(replay_file, 'w', encoding="utf-8") as outfile:
        json.dump(context, outfile, indent=2)


def load(replay_dir: Path | str, template_name: str) -> dict[str, Any]:
    """Read json data from file."""
    replay_file = get_file_name(replay_dir, template_name)

    with open(replay_file, encoding="utf-8") as infile:
        context: dict[str, Any] = json.load(infile)

    _validate_context(context)
    return context
```

## Refactorizaciones aplicadas

- **Extract Function**
  - Elementos afectados: la validación duplicada en `dump` y `load` pasa a la nueva función privada `_validate_context`.
  - Motivo:
    - Elimina el código duplicado (comprobación y mensaje de error idénticos en dos sitios).
    - Garantiza que ambos caminos validen siempre igual.
  - Se conservan el orden de las operaciones y el comportamiento:
    - En `dump`, el directorio se sigue creando antes de validar.
    - Se lanza la misma `ValueError` con el mismo mensaje.

- **Replace Magic Literal** (Replace Magic Number with Symbolic Constant)
  - Elementos afectados: los literales `'.json'` y `'cookiecutter'` pasan a las constantes privadas `_JSON_EXTENSION` y `_REQUIRED_CONTEXT_KEY`.
  - Motivo:
    - Da nombre al significado de esos valores.
    - Evita repetirlos.

- **Simplify Conditional Expression**
  - Elementos afectados: en `get_file_name`, la expresión `'.json' if not template_name.endswith('.json') else ''` pasa a ser `'' if template_name.endswith(_JSON_EXTENSION) else _JSON_EXTENSION`.
  - Motivo:
    - Elimina la negación innecesaria, lo que facilita la lectura.
    - El resultado es el mismo en todos los casos.

- **Rename Variable**
  - Elementos afectados: `file_name` pasa a `replay_file_name` en `get_file_name`.
  - Motivo: el nombre deja claro que se trata del nombre del fichero de replay, coherente con `replay_file` en `dump` y `load`.

- **Mejora de documentación del módulo** (no es una refactorización del catálogo de Fowler, pero contribuye a la legibilidad)
  - Elementos afectados: el docstring del módulo (`cookiecutter.replay.` seguido de una línea de guiones) pasa a describir qué hace el módulo.
  - Motivo: el docstring original no aportaba información.

Las firmas públicas (`get_file_name`, `dump`, `load`) no cambian, y tampoco las dependencias ni los imports usados por otros módulos.