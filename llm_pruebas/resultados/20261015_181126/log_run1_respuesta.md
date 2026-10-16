```python
"""Module for setting up logging."""

from __future__ import annotations

import logging
import sys

LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

LOG_FORMATS = {
    'DEBUG': '%(levelname)s %(name)s: %(message)s',
    'INFO': '%(levelname)s: %(message)s',
}

_LOGGER_NAME = 'cookiecutter'
_DEBUG_LEVEL_NAME = 'DEBUG'


def _attach_handler(
    logger: logging.Logger, handler: logging.Handler, level_name: str
) -> None:
    """Configure ``handler`` for ``level_name`` and attach it to ``logger``.

    The handler gets both the numeric level and the message format associated
    with ``level_name`` in ``LOG_LEVELS`` and ``LOG_FORMATS``. Raises
    ``KeyError`` if ``level_name`` has no format defined.
    """
    formatter = logging.Formatter(LOG_FORMATS[level_name])
    level = LOG_LEVELS[level_name]

    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def configure_logger(
    stream_level: str = 'DEBUG', debug_file: str | None = None
) -> logging.Logger:
    """Configure logging for cookiecutter.

    Set up logging to stdout with given level. If ``debug_file`` is given set
    up logging to file with DEBUG level.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)

    # Remove all attached handlers, in case there was
    # a logger with using the name 'cookiecutter'
    del logger.handlers[:]

    if debug_file is not None:
        _attach_handler(logger, logging.FileHandler(debug_file), _DEBUG_LEVEL_NAME)

    _attach_handler(logger, logging.StreamHandler(stream=sys.stdout), stream_level)

    return logger
```

## Refactorizaciones aplicadas

- **Extract Function** (`_attach_handler`, a partir de los dos bloques de `configure_logger` que configuraban el manejador de archivo y el de consola).
  - **Motivo:** ambos bloques repetían la misma secuencia: crear el formateador, fijar el nivel, asignar el formateador y añadir el manejador al logger.
  - Al centralizarla se elimina la duplicación y `configure_logger` queda como una descripción de alto nivel de lo que se configura.
  - El helper busca el formato en `LOG_FORMATS` antes que el nivel en `LOG_LEVELS`, igual que el código original. Así, un `stream_level` sin formato definido (por ejemplo `'WARNING'`) sigue lanzando el mismo `KeyError`.
  - En ese caso, el manejador de archivo ya habrá quedado añadido y el de consola no, como antes.

- **Replace Magic Literal** (`'cookiecutter'` pasa a ser `_LOGGER_NAME`; `'DEBUG'`, usado como clave del manejador de archivo, pasa a ser `_DEBUG_LEVEL_NAME`).
  - **Motivo:** las constantes nombradas documentan la intención y evitan que esas cadenas se escriban a mano en varios sitios.
  - Ambas son privadas para no ampliar la API pública del módulo.
  - El valor por defecto `stream_level='DEBUG'` se mantiene literal para no alterar la firma pública.

- **Inline Variable** (`debug_formatter`, `file_handler`, `log_formatter`, `log_level` y `stream_handler` en `configure_logger`).
  - **Motivo:** tras extraer `_attach_handler`, estas variables temporales ya no aportaban claridad.
  - Los manejadores se construyen directamente en la llamada al helper.

- **Remove Dead Comment** (comentarios redundantes como `# Set up 'cookiecutter' logger`, `# Create a stream handler` y `# Get settings based on the given stream_level`).
  - **Motivo:** repetían lo que el código ya expresa con los nuevos nombres.
  - Se conserva el comentario sobre la eliminación de manejadores previos, porque explica el *porqué* y no el *qué*.

Sin cambios de comportamiento:

- `LOG_LEVELS`, `LOG_FORMATS` y la firma de `configure_logger` se mantienen intactos.
- El orden de las operaciones observables también se conserva: nivel del logger, limpieza de manejadores, manejador de archivo opcional y manejador de `stdout`.