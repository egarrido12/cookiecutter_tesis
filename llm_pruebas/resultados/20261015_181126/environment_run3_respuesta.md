```python
"""Jinja2 environment and extensions loading."""

from __future__ import annotations

from typing import Any

from jinja2 import Environment, StrictUndefined

from cookiecutter.exceptions import UnknownExtension

# Extensiones de Cookiecutter que se cargan siempre en todo entorno Jinja2,
# antes de las declaradas por la plantilla en ``_extensions``.
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

        1. Establishes the default Cookiecutter extensions.
        2. Reads extensions set in the cookiecutter.json _extensions key.
        3. Attempts to load the extensions. Provides useful error if fails.
        """
        extensions = self._collect_extensions(context or {})

        try:
            super().__init__(extensions=extensions, **kwargs)  # type: ignore[call-arg]
        except ImportError as err:
            msg = f'Unable to load extension: {err}'
            raise UnknownExtension(msg) from err

    def _collect_extensions(self, context: dict[str, Any]) -> list[str]:
        """Return the default extensions followed by those defined in the context."""
        return list(_DEFAULT_EXTENSIONS) + self._read_extensions(context)

    def _read_extensions(self, context: dict[str, Any]) -> list[str]:
        """Return list of extensions as str to be passed on to the Jinja2 env.

        If context does not contain the relevant info, return an empty
        list instead.
        """
        try:
            extensions = context['cookiecutter']['_extensions']
        except KeyError:
            return []
        return [str(ext) for ext in extensions]


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
```

## Refactorizaciones aplicadas

- **Replace Magic Literal / Extract Variable (promovida a constante de módulo)**
  - *Elementos afectados:* la lista local `default_extensions` de `ExtensionLoaderMixin.__init__` pasa a ser la constante privada `_DEFAULT_EXTENSIONS`.
  - *Motivo:* el conjunto de extensiones por defecto es configuración estática del módulo y no lógica del constructor. Como constante es más fácil de localizar y mantener.
  - *Por qué es privada y es una tupla:* el prefijo `_` evita ampliar la API pública. La tupla impide que alguien la mute por accidente entre instancias.
  - *Comportamiento:* se convierte con `list(...)` antes de concatenar, así que el valor que recibe Jinja2 es exactamente la misma lista que antes.

- **Extract Method**
  - *Elementos afectados:* la composición de la lista final de extensiones sale de `__init__` al nuevo método privado `_collect_extensions(context)`.
  - *Motivo:* `__init__` queda reducido a tres pasos: obtener extensiones, inicializar el entorno y traducir el error.
  - *Comportamiento:* se mantiene el orden de las llamadas: `_read_extensions` sigue ejecutándose antes de `super().__init__`. También se conserva el uso de `+` entre listas, igual que el original.

- **Inline Variable**
  - *Elementos afectados:* la reasignación `context = context or {}` se sustituye por pasar directamente `context or {}` a `_collect_extensions`.
  - *Motivo:* se elimina la reasignación del parámetro. La semántica no cambia: cualquier contexto "falsy" se trata como un diccionario vacío.

- **Remove Redundant `else` (simplificación de condicional)**
  - *Elementos afectados:* `_read_extensions`.
  - *Motivo:* la rama `except` ya retorna, así que el bloque `else` del `try` era innecesario. Ahora el camino principal se lee de forma lineal.
  - *Comportamiento:* solo se sigue capturando `KeyError`, así que no cambia frente a contextos con otra forma inesperada. El método conserva su nombre por si alguna subclase o test lo sobrescribe o invoca.

- **Update Documentation**
  - *Elementos afectados:* docstring de `ExtensionLoaderMixin.__init__`.
  - *Motivo:* el punto 1 decía "currently just a Time feature", que estaba desactualizado porque hay cinco extensiones por defecto. Ahora remite a las extensiones por defecto de Cookiecutter sin enumerarlas, para no volver a quedar obsoleto.