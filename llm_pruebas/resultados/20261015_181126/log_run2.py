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
