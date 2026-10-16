```python
"""Main package for Cookiecutter."""

from importlib.metadata import version

__version__ = version("cookiecutter")
```

## Refactorizaciones aplicadas

**Ninguna.** El módulo tiene una sola responsabilidad: exponer la versión instalada del paquete. Lo hace en una línea, con una API estándar y sin duplicación ni lógica que simplificar. Cualquier cambio empeoraría el código o alteraría el comportamiento observable.

Refactorizaciones que evalué y descarté:

- **Rename Variable / ocultar la importación** (`from importlib.metadata import version as _version`)
  - *Elemento afectado:* el nombre `version` en el espacio de nombres de `cookiecutter`.
  - *Motivo del descarte:* `version` es hoy un atributo público del paquete. Cualquier código externo puede usar `cookiecutter.version` o `from cookiecutter import version`, y `from cookiecutter import *` también lo importa. Renombrarlo cambiaría un nombre público y rompería ese comportamiento.

- **Añadir `__all__ = ["__version__"]`**
  - *Elemento afectado:* el comportamiento de `from cookiecutter import *`.
  - *Motivo del descarte:* hoy esa importación incluye `version` y excluye `__version__`, porque empieza por guion bajo. Con `__all__` ocurriría lo contrario, así que el comportamiento observable cambiaría.

- **Extract Function** (por ejemplo, `def _get_version() -> str`)
  - *Elemento afectado:* el cálculo de `__version__`.
  - *Motivo del descarte:* añadiría una indirección sin aportar claridad. La expresión `version("cookiecutter")` ya se explica por sí misma, y la función no se reutilizaría en ningún sitio.

- **Añadir una anotación de tipo** (`__version__: str = ...`)
  - *Elemento afectado:* `__version__` y el `__annotations__` del módulo.
  - *Motivo del descarte:* los verificadores de tipos ya infieren `str` desde la firma de `importlib.metadata.version`. Además, la anotación modificaría `cookiecutter.__annotations__` sin ganar legibilidad.

En resumen, el archivo ya cumple los objetivos de legibilidad y mantenibilidad, y lo correcto es dejarlo tal cual.