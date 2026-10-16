"""Global configuration handling."""

from __future__ import annotations

import collections
import copy
import logging
import os
from typing import TYPE_CHECKING, Any

import yaml

from cookiecutter.exceptions import ConfigDoesNotExistException, InvalidConfiguration

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

USER_CONFIG_PATH = os.path.expanduser('~/.cookiecutterrc')

BUILTIN_ABBREVIATIONS = {
    'gh': 'https://github.com/{0}.git',
    'gl': 'https://gitlab.com/{0}.git',
    'bb': 'https://bitbucket.org/{0}',
}

DEFAULT_CONFIG = {
    'cookiecutters_dir': os.path.expanduser('~/.cookiecutters/'),
    'replay_dir': os.path.expanduser('~/.cookiecutter_replay/'),
    'default_context': collections.OrderedDict([]),
    'abbreviations': BUILTIN_ABBREVIATIONS,
}

# Environment variable that may point to a user configuration file.
_CONFIG_ENV_VAR = 'COOKIECUTTER_CONFIG'

# Configuration keys holding paths that must have env vars and "~" expanded.
_PATH_CONFIG_KEYS = ('replay_dir', 'cookiecutters_dir')


def _expand_path(path: str) -> str:
    """Expand both environment variables and user home in the given path."""
    path = os.path.expandvars(path)
    return os.path.expanduser(path)


def _default_config_copy() -> dict[str, Any]:
    """Return a shallow copy of the default configuration."""
    return copy.copy(DEFAULT_CONFIG)


def merge_configs(default: dict[str, Any], overwrite: dict[str, Any]) -> dict[str, Any]:
    """Recursively update a dict with the key/value pair of another.

    Dict values that are dictionaries themselves will be updated, whilst
    preserving existing keys.
    """
    new_config = copy.deepcopy(default)

    for key, value in overwrite.items():
        # Make sure to preserve existing items in
        # nested dicts, for example `abbreviations`
        if isinstance(value, dict):
            new_config[key] = merge_configs(default.get(key, {}), value)
        else:
            new_config[key] = value

    return new_config


def _load_yaml_config(config_path: Path | str) -> dict[str, Any]:
    """Read the YAML file at ``config_path`` and return its top-level mapping.

    An empty file is interpreted as an empty mapping.

    :raises InvalidConfiguration: If the file is not valid YAML or its
        top-level element is not a mapping.
    """
    with open(config_path, encoding='utf-8') as file_handle:
        try:
            yaml_dict = yaml.safe_load(file_handle) or {}
        except yaml.YAMLError as e:
            msg = f'Unable to parse YAML file {config_path}.'
            raise InvalidConfiguration(msg) from e

    if not isinstance(yaml_dict, dict):
        msg = f'Top-level element of YAML file {config_path} should be an object.'
        raise InvalidConfiguration(msg)

    return yaml_dict


def _expand_config_paths(config_dict: dict[str, Any]) -> None:
    """Expand env vars and user home in the path entries of ``config_dict``."""
    for key in _PATH_CONFIG_KEYS:
        config_dict[key] = _expand_path(config_dict[key])


def get_config(config_path: Path | str) -> dict[str, Any]:
    """Retrieve the config from the specified path, returning a config dict."""
    if not os.path.exists(config_path):
        msg = f'Config file {config_path} does not exist.'
        raise ConfigDoesNotExistException(msg)

    logger.debug('config_path is %s', config_path)
    yaml_dict = _load_yaml_config(config_path)

    config_dict = merge_configs(DEFAULT_CONFIG, yaml_dict)
    _expand_config_paths(config_dict)

    return config_dict


def get_user_config(
    config_file: str | None = None,
    default_config: bool | dict[str, Any] = False,
) -> dict[str, Any]:
    """Return the user config as a dict.

    If ``default_config`` is True, ignore ``config_file`` and return default
    values for the config parameters.

    If ``default_config`` is a dict, merge values with default values and return them
    for the config parameters.

    If a path to a ``config_file`` is given, that is different from the default
    location, load the user config from that.

    Otherwise look up the config file path in the ``COOKIECUTTER_CONFIG``
    environment variable. If set, load the config from this path. This will
    raise an error if the specified path is not valid.

    If the environment variable is not set, try the default config file path
    before falling back to the default config values.
    """
    # Do NOT load a config. Merge provided values with defaults and return them instead
    if default_config and isinstance(default_config, dict):
        return merge_configs(DEFAULT_CONFIG, default_config)

    # Do NOT load a config. Return defaults instead.
    if default_config:
        logger.debug("Force ignoring user config with default_config switch.")
        return _default_config_copy()

    # Load the given config file.
    # NOTE: identity comparison (``is not``) is intentional and preserved from
    # the original implementation; do not replace it with ``!=``.
    if config_file and config_file is not USER_CONFIG_PATH:
        logger.debug("Loading custom config from %s.", config_file)
        return get_config(config_file)

    # There is a config environment variable. Try to load it.
    # Do not check for existence, so invalid file paths raise an error.
    env_config_file = os.environ.get(_CONFIG_ENV_VAR)
    if env_config_file is not None:
        logger.debug("User config not found or not specified. Loading default config.")
        return get_config(env_config_file)

    # Load an optional user config if it exists, otherwise return the defaults.
    if os.path.exists(USER_CONFIG_PATH):
        logger.debug("Loading config from %s.", USER_CONFIG_PATH)
        return get_config(USER_CONFIG_PATH)

    logger.debug("User config not found. Loading default config.")
    return _default_config_copy()
