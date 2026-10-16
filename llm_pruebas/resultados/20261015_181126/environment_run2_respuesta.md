```python
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
```

## Refactorizaciones aplicadas

- **Replace Magic Literal / Extract Variable (a nivel de módulo)** — elementos afectados: la lista local `default_extensions` de `ExtensionLoaderMixin.__init__`, que pasa a ser la constante privada `_DEFAULT_EXTENSIONS`.
  - **Motivo:** la lista de extensiones por defecto es configuración estática del módulo, no lógica de inicialización. Al sacarla del constructor, queda visible y documentada en un único lugar, y `__init__` se limita a orquestar el proceso.
  - Uso una tupla para que la constante sea inmutable y no pueda modificarse por accidente entre instancias.
  - En `__init__` se sigue construyendo una lista nueva (`[*_DEFAULT_EXTENSIONS, *...]`) con el mismo orden y contenido que antes. Por tanto, Jinja2 recibe exactamente el mismo argumento `extensions`.

- **Rename Variable** — elementos afectados: en `_read_extensions`, `extensions` pasa a llamarse `template_extensions` y `ext` pasa a llamarse `extension`.
  - **Motivo:** el nombre `template_extensions` deja claro que son las extensiones declaradas por la plantilla en `_extensions`, y evita confundirlas con la lista completa de `__init__`, que también se llamaba `extensions`.
  - `extension` evita una abreviatura innecesaria.

- **Simplificación del condicional (eliminar la cláusula `else` del `try`)** — elementos afectados: `_read_extensions`.
  - **Motivo:** como la rama `except` ya hace `return`, el `else` solo añadía anidamiento.
  - El `return` con la comprensión queda fuera del bloque `try`, así que un `KeyError` producido al iterar o convertir las extensiones sigue sin capturarse, igual que en el original. El comportamiento es idéntico.

- **Corrección del docstring** — elementos afectados: docstring de `ExtensionLoaderMixin.__init__`.
  - **Motivo:** decía que las extensiones por defecto eran "currently just a Time feature", lo cual estaba desactualizado (son cinco extensiones). Un comentario incorrecto perjudica la mantenibilidad, así que lo alineé con el código real.

**Aspectos que no se han modificado:**
- Los nombres y firmas de `ExtensionLoaderMixin`, `StrictEnvironment` y sus constructores.
- El nombre y la firma de `_read_extensions`, aunque es privado, para no romper posibles tests o subclases que lo sobrescriban.
- La traducción de `ImportError` a `UnknownExtension`, con su mensaje y su encadenamiento `from err`.