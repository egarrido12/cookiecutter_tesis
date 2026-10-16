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
