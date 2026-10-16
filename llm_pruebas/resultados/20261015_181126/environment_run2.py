"""Jinja2 environment and extensions loading."""

from __future__ import annotations

from typing import Any

from jinja2 import Environment, StrictUndefined

from cookiecutter.exceptions import UnknownExtension

# Extensiones de Jinja2 que Cookiecutter carga siempre, antes de las que
# declare la plantilla en la clave ``_extensions`` de cookiecutter.json.
_DEFAULT_EXTENSIONS: tuple[str, ...] = (
    'cookiecutter.extensions.JsonifyExtension',
    'cookiecutter.extensions.RandomStringExtension',
    'cookiecutter.extensions.SlugifyExtension',
    'cookiecutter.extensions.TimeExtension',
    'cookiecutter.extensions.UUIDExtension',
)


class ExtensionLoaderMixin:
    """Mixin providing sane loading of extensions specified in a given context.

    The context is being extracted from the keyword arguments before calling
    the next parent class in line of the child.
    """

    def __init__(self, *, context: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Initialize the Jinja2 Environment object while loading extensions.

        Does the following:

        1. Takes the default Cookiecutter extensions (JSON, random strings,
           slugify, time and UUID helpers).
        2. Reads extensions set in the cookiecutter.json _extensions key.
        3. Attempts to load the extensions. Provides useful error if fails.
        """
        context = context or {}
        extensions = [*_DEFAULT_EXTENSIONS, *self._read_extensions(context)]

        try:
            super().__init__(extensions=extensions, **kwargs)  # type: ignore[call-arg]
        except ImportError as err:
            msg = f'Unable to load extension: {err}'
            raise UnknownExtension(msg) from err

    def _read_extensions(self, context: dict[str, Any]) -> list[str]:
        """Return list of extensions as str to be passed on to the Jinja2 env.

        If context does not contain the relevant info, return an empty
        list instead.
        """
        try:
            template_extensions = context['cookiecutter']['_extensions']
        except KeyError:
            return []
        return [str(extension) for extension in template_extensions]


class StrictEnvironment(ExtensionLoaderMixin, Environment):
    """Create strict Jinja2 environment.

    Jinja2 environment will raise error on undefined variable in template-
    rendering context.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Set the standard Cookiecutter StrictEnvironment.

        Also loading extensions defined in cookiecutter.json's _extensions key.
        """
        super().__init__(undefined=StrictUndefined, **kwargs)
