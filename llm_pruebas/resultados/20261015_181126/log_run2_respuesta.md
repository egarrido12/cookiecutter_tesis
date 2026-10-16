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


def _add_handler(
    logger: logging.Logger, handler: logging.Handler, level_name: str
) -> None:
    """Configure ``handler`` with the level and format for ``level_name``.

    Then attach it to ``logger``.

    :param logger: Logger that will receive the handler.
    :param handler: Handler to configure and attach.
    :param level_name: Key in ``LOG_LEVELS`` and ``LOG_FORMATS``.
    """
    handler.setLevel(LOG_LEVELS[level_name])
    handler.setFormatter(logging.Formatter(LOG_FORMATS[level_name]))
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
    logger.handlers.clear()

    if debug_file is not None:
        _add_handler(logger, logging.FileHandler(debug_file), 'DEBUG')

    _add_handler(logger, logging.StreamHandler(stream=sys.stdout), stream_level)

    return logger
```

## Refactorizaciones aplicadas

- **Extract Function**
  - Elementos afectados: se crea `_add_handler(logger, handler, level_name)` a partir de los dos bloques casi idénticos de `configure_logger`, el del `FileHandler` y el del `StreamHandler`.
  - Motivo: elimina la duplicación de los pasos «fijar nivel, fijar formateador y añadir al logger». `configure_logger` queda reducida a su intención: crear el logger, limpiarlo y añadir un handler de fichero (opcional) y otro de consola.
  - Comportamiento: se conserva el orden de las llamadas (`setLevel`, luego `setFormatter`, luego `addHandler`) y el orden de los handlers (primero el de fichero, después el de consola). Con un `stream_level` sin formato definido (por ejemplo `'WARNING'`) se sigue lanzando `KeyError` antes de añadir el handler de consola. El handler de fichero, si existe, ya estaba añadido, igual que en el original.

- **Inline Variable**
  - Elementos afectados: `debug_formatter`, `file_handler`, `log_formatter`, `log_level` y `stream_handler`.
  - Motivo: eran variables temporales de un solo uso. Con la función extraída ya no aportan claridad.

- **Replace Magic Literal (Extract Constant)**
  - Elementos afectados: el literal `'cookiecutter'` pasa a la constante privada `_LOGGER_NAME`.
  - Motivo: da nombre explícito al logger raíz del paquete. Es privada, así que no altera la API pública.

- **Substitute Algorithm**
  - Elementos afectados: `del logger.handlers[:]` se sustituye por `logger.handlers.clear()`.
  - Motivo: expresa la intención de vaciar la lista de forma más legible. Ambas formas modifican la misma lista en sitio, así que el efecto es idéntico.

- **Remove Dead Comments**
  - Elementos afectados: los comentarios `# Set up 'cookiecutter' logger`, `# Create a file handler...`, `# Get settings...` y `# Create a stream handler`.
  - Motivo: tras la refactorización, los nombres de las funciones y variables ya describen lo que hace cada paso. Se mantiene el comentario que explica *por qué* se eliminan los handlers previos.

Las constantes públicas `LOG_LEVELS` y `LOG_FORMATS` y la firma de `configure_logger` no cambian. Tampoco cambia el valor de retorno: sigue siendo el mismo `logging.Logger`.