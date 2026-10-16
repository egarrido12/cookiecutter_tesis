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

_COOKIECUTTER_LOGGER_NAME = 'cookiecutter'
_FILE_LOG_LEVEL_NAME = 'DEBUG'


def _configure_handler(handler: logging.Handler, level_name: str) -> logging.Handler:
    """Apply the format and level associated with ``level_name`` to ``handler``.

    :param handler: Handler to configure.
    :param level_name: Key of both ``LOG_FORMATS`` and ``LOG_LEVELS``.
    :return: The same handler, already configured.
    """
    formatter = logging.Formatter(LOG_FORMATS[level_name])
    handler.setLevel(LOG_LEVELS[level_name])
    handler.setFormatter(formatter)
    return handler


def _create_file_handler(debug_file: str) -> logging.Handler:
    """Create a handler that writes DEBUG-level records into ``debug_file``."""
    return _configure_handler(logging.FileHandler(debug_file), _FILE_LOG_LEVEL_NAME)


def _create_stream_handler(stream_level: str) -> logging.Handler:
    """Create a handler that writes records of ``stream_level`` to stdout."""
    return _configure_handler(logging.StreamHandler(stream=sys.stdout), stream_level)


def configure_logger(
    stream_level: str = 'DEBUG', debug_file: str | None = None
) -> logging.Logger:
    """Configure logging for cookiecutter.

    Set up logging to stdout with given level. If ``debug_file`` is given set
    up logging to file with DEBUG level.
    """
    logger = logging.getLogger(_COOKIECUTTER_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)

    # Remove all attached handlers, in case there was
    # a logger with using the name 'cookiecutter'
    logger.handlers.clear()

    if debug_file is not None:
        logger.addHandler(_create_file_handler(debug_file))

    logger.addHandler(_create_stream_handler(stream_level))

    return logger
```

## Refactorizaciones aplicadas

- **Extract Function** – `_configure_handler(handler, level_name)`
  - **Elementos afectados:** `configure_logger`.
  - **Motivo:** el original repetía la secuencia "crear `Formatter` → `setLevel` → `setFormatter`" para el handler de fichero y para el de consola. Al extraerla, la lógica queda en un solo lugar. Además se mantiene la relación entre `LOG_FORMATS` y `LOG_LEVELS`, que comparten la misma clave.
  - **Comportamiento:** se conserva el orden de búsqueda: primero `LOG_FORMATS` y después `LOG_LEVELS`. Por eso un `stream_level` sin formato definido (p. ej. `'WARNING'`) sigue lanzando el mismo `KeyError`.

- **Extract Function** – `_create_file_handler(debug_file)` y `_create_stream_handler(stream_level)`
  - **Elementos afectados:** `configure_logger`.
  - **Motivo:** cada bloque comentado ("Create a file handler…", "Create a stream handler") pasa a ser una función con nombre que explica su intención. Así `configure_logger` se lee como una secuencia de pasos de alto nivel y sobran los comentarios explicativos.
  - **Comportamiento:**
    - `sys.stdout` se sigue evaluando en el momento de la llamada y no como argumento por defecto. Esto mantiene la compatibilidad con la captura de salida en tests.
    - El handler de fichero se sigue añadiendo antes que el de consola.

- **Replace Magic Literal** (Replace Magic Number with Symbolic Constant) – `_COOKIECUTTER_LOGGER_NAME` y `_FILE_LOG_LEVEL_NAME`
  - **Elementos afectados:** el literal `'cookiecutter'` en `logging.getLogger` y el literal `'DEBUG'` usado para el handler de fichero.
  - **Motivo:** dan nombre al significado de esos valores: el nombre del logger raíz del paquete y el nivel fijo del log a fichero. Son privadas para no ampliar la API pública.

- **Substitute Algorithm** (menor) – `del logger.handlers[:]` → `logger.handlers.clear()`
  - **Elementos afectados:** `configure_logger`.
  - **Motivo:** ambas formas vacían la misma lista *in situ*, pero `clear()` expresa la intención de forma directa y es más legible.

**Sin cambios:** `LOG_LEVELS`, `LOG_FORMATS` y la firma de `configure_logger` se mantienen intactos, porque los usan `cli.py` y los tests.