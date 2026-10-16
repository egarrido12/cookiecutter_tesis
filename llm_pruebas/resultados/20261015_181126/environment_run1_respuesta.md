```python
"""Jinja2 environment and extensions loading."""

from __future__ import annotations

from typing import Any

from jinja2 import Environment, StrictUndefined

from cookiecutter.exceptions import UnknownExtension

# Extensiones que Cookiecutter carga siempre, antes de las declaradas por la
# plantilla en la clave ``_extensions`` de cookiecutter.json.
_DEFAULT_EXTENSIONS = (
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

        1. Establishes the default extensions bundled with Cookiecutter.
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
        else:
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
```

## Refactorizaciones aplicadas

- **Replace Magic Literal / Extract Variable (a nivel de módulo)**: `default_extensions` → constante privada `_DEFAULT_EXTENSIONS`.
  - **Elementos afectados:** `ExtensionLoaderMixin.__init__`.
  - **Motivo:** la lista de extensiones por defecto es un dato de configuración fijo, no una variable local. Se volvía a crear en cada instanciación y quedaba mezclada con la lógica del constructor.
  - **Detalles de la nueva constante:**
    - Al estar en el ámbito del módulo, queda documentada en un único lugar.
    - Es una tupla, para que no se pueda mutar por accidente.
    - Es privada (con `_`), para no ampliar la API pública.
  - **Comportamiento:** no cambia. Jinja2 sigue recibiendo una `list` nueva con el mismo orden: primero las extensiones por defecto y después las de la plantilla. Se construye con desempaquetado (`[*a, *b]`) en lugar de concatenar listas.

- **Rename Variable**: `extensions` → `template_extensions` y `ext` → `extension`.
  - **Elementos afectados:** `ExtensionLoaderMixin._read_extensions`.
  - **Motivo:** distinguir las extensiones declaradas por la plantilla en `_extensions` de la lista final de extensiones que construye `__init__`. Además, se evitan abreviaturas en la comprensión de lista.
  - **Lo que se conserva:** la estructura `try/except KeyError/else`. Así, solo un `KeyError` al acceder al contexto produce la lista vacía. Los errores al iterar o convertir los elementos se siguen propagando como antes.

- **Actualización de docstring (no es una refactorización del catálogo de Fowler)**.
  - **Elementos afectados:** el docstring de `ExtensionLoaderMixin.__init__`.
  - **Motivo:** el paso 1 decía "currently just a Time feature", lo que ya no era cierto, porque se cargan cinco extensiones por defecto. Ahora el texto describe el comportamiento real sin enumerar extensiones concretas, para que no vuelva a quedar desactualizado.

- **Sin cambios en la API pública**: `ExtensionLoaderMixin` y `StrictEnvironment` mantienen sus nombres y firmas, y también se conserva el método `_read_extensions`, por si existen subclases o tests que lo usen. Las excepciones lanzadas (`UnknownExtension`, encadenada desde `ImportError`) y sus mensajes son idénticos.