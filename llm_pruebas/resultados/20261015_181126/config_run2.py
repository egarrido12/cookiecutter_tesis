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

# Environment variable that may point to an alternative user config file.
_CONFIG_ENV_VAR = 'COOKIECUTTER_CONFIG'

# Config settings that hold paths which may contain ``~`` or environment
# variables. They are expanded in this order.
_PATH_SETTINGS = ('replay_dir', 'cookiecutters_dir')


def _expand_path(path: str) -> str:
    """Expand both environment variables and user home in the given path."""
    path = os.path.expandvars(path)
    return os.path.expanduser(path)


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


def _read_yaml_config(config_path: Path | str) -> dict[str, Any]:
    """Parse the YAML file at ``config_path`` and return its top-level mapping.

    An empty file is treated as an empty mapping.

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


def _expand_path_settings(config_dict: dict[str, Any]) -> None:
    """Expand, in place, every path-like setting of ``config_dict``."""
    for setting in _PATH_SETTINGS:
        config_dict[setting] = _expand_path(config_dict[setting])


def get_config(config_path: Path | str) -> dict[str, Any]:
    """Retrieve the config from the specified path, returning a config dict."""
    if not os.path.exists(config_path):
        msg = f'Config file {config_path} does not exist.'
        raise ConfigDoesNotExistException(msg)

    logger.debug('config_path is %s', config_path)
    yaml_dict = _read_yaml_config(config_path)

    config_dict = merge_configs(DEFAULT_CONFIG, yaml_dict)
    _expand_path_settings(config_dict)

    return config_dict


def _get_default_config() -> dict[str, Any]:
    """Return a (shallow) copy of the default configuration."""
    return copy.copy(DEFAULT_CONFIG)


def _is_custom_config_file(config_file: str | None) -> bool:
    """Tell whether ``config_file`` is an explicitly given, non-default file.

    Note: the identity comparison (``is not``) against ``USER_CONFIG_PATH``
    is intentional and preserved from the original implementation.
    """
    return bool(config_file) and config_file is not USER_CONFIG_PATH


def _get_env_or_user_config() -> dict[str, Any]:
    """Load the config pointed to by the environment, the user file or defaults.

    If the ``COOKIECUTTER_CONFIG`` environment variable is set, load the config
    from that path without checking for existence, so invalid paths raise an
    error. Otherwise load the optional user config if it exists, falling back
    to the default values.
    """
    env_config_file = os.environ.get(_CONFIG_ENV_VAR)
    if env_config_file is not None:
        logger.debug("User config not found or not specified. Loading default config.")
        return get_config(env_config_file)

    if os.path.exists(USER_CONFIG_PATH):
        logger.debug("Loading config from %s.", USER_CONFIG_PATH)
        return get_config(USER_CONFIG_PATH)

    logger.debug("User config not found. Loading default config.")
    return _get_default_config()


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
        return _get_default_config()

    # Load the given config file
    if _is_custom_config_file(config_file):
        logger.debug("Loading custom config from %s.", config_file)
        return get_config(config_file)

    return _get_env_or_user_config()
