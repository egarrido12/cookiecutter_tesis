```python
"""
cookiecutter.replay.

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


def _validate_context(context: dict[str, Any]) -> None:
    """Raise ``ValueError`` if ``context`` lacks the required ``cookiecutter`` key.

    :param context: Context to be stored in, or read from, a replay file.
    """
    if _REQUIRED_CONTEXT_KEY not in context:
        msg = 'Context is required to contain a cookiecutter key'
        raise ValueError(msg)


def get_file_name(replay_dir: Path | str, template_name: str) -> str:
    """Return the path of the replay file for ``template_name`` in ``replay_dir``.

    The ``.json`` extension is appended only if ``template_name`` lacks it.

    :param replay_dir: Directory where replay files are stored.
    :param template_name: Name of the template, with or without ``.json``.
    """
    if template_name.endswith(_REPLAY_FILE_EXTENSION):
        file_name = template_name
    else:
        file_name = f'{template_name}{_REPLAY_FILE_EXTENSION}'
    return os.path.join(replay_dir, file_name)


def dump(replay_dir: Path | str, template_name: str, context: dict[str, Any]) -> None:
    """Write the context to the replay file of the template as JSON.

    :param replay_dir: Directory where replay files are stored. It is created
        if it does not exist.
    :param template_name: Name of the template.
    :param context: Context to save; must contain a ``cookiecutter`` key.
    """
    make_sure_path_exists(replay_dir)
    _validate_context(context)

    replay_file = get_file_name(replay_dir, template_name)
    with open(replay_file, 'w', encoding="utf-8") as outfile:
        json.dump(context, outfile, indent=2)


def load(replay_dir: Path | str, template_name: str) -> dict[str, Any]:
    """Read the context from the replay file of the template.

    :param replay_dir: Directory where replay files are stored.
    :param template_name: Name of the template.
    :return: The stored context, which is guaranteed to contain a
        ``cookiecutter`` key.
    """
    replay_file = get_file_name(replay_dir, template_name)
    with open(replay_file, encoding="utf-8") as infile:
        context: dict[str, Any] = json.load(infile)

    _validate_context(context)
    return context
```

## Refactorizaciones aplicadas

- **Extract Function**: la validación duplicada de `dump` y `load` pasa a la función privada `_validate_context`.
  - El bloque `if 'cookiecutter' not in context: ... raise ValueError(...)` aparecía idéntico en las dos funciones.
  - Ahora existe una única fuente de verdad para la regla y su mensaje de error.
  - El mensaje y el tipo de excepción (`ValueError`) no cambian.
  - En `dump` se conserva el orden original: primero se crea el directorio con `make_sure_path_exists` y después se valida el contexto. Así el efecto secundario es el mismo cuando el contexto no es válido.

- **Replace Magic Literal** (Replace Magic Number with Symbolic Constant): se crean las constantes privadas `_REPLAY_FILE_EXTENSION` (`'.json'`) y `_REQUIRED_CONTEXT_KEY` (`'cookiecutter'`).
  - El literal `'.json'` se usaba dos veces en `get_file_name`, y la clave requerida es una regla de dominio.
  - Con un nombre propio, la intención queda explícita y se evita que los usos diverjan.

- **Decompose Conditional** (y eliminación de la negación): en `get_file_name`, la expresión `'.json' if not template_name.endswith('.json') else ''` se sustituye por un `if/else` sin negación.
  - Cada rama construye `file_name` directamente, en lugar de calcular un sufijo vacío o no vacío y concatenarlo después.
  - El resultado es idéntico en ambos casos, pero se entiende más fácilmente.

- **Docstrings más precisos** (cambio de documentación, no de comportamiento): se amplían los docstrings de `get_file_name`, `dump` y `load` con su propósito real y sus parámetros, siguiendo el estilo `:param:` del resto del paquete.
  - Por ejemplo, el anterior "Get the name of file." no reflejaba que la función devuelve una ruta completa.
  - El docstring del módulo se deja intacto.

Se mantienen sin cambios los nombres, las firmas y las anotaciones de las funciones públicas (`get_file_name`, `dump`, `load`). Tampoco cambian las dependencias ni la compatibilidad con las versiones de Python soportadas.