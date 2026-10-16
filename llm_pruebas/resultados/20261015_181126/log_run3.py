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
