```python
"""Main package for Cookiecutter."""

from importlib.metadata import version

__version__ = version("cookiecutter")
```

## Refactorizaciones aplicadas

**Ninguna.** El archivo queda igual. Tiene una sola instrucción, es legible y no presenta problemas de diseño. No hay duplicación, nombres confusos, funciones largas ni lógica condicional que justifique aplicar alguna refactorización del catálogo de Fowler.

Estas son las transformaciones que evalué y por qué las descarté:

| Transformación evaluada | Motivo del descarte |
|---|---|
| **Rename Variable** de la importación (`from importlib.metadata import version as _version`) para ocultar `version` del espacio de nombres del paquete | Hoy `cookiecutter.version` existe como atributo público del módulo y `from cookiecutter import *` lo exporta. Renombrarlo eliminaría ese atributo, lo que cambia el comportamiento observable y puede romper código externo que dependa de él. |
| Añadir `__all__ = ["__version__"]` | Cambiaría el resultado de `from cookiecutter import *`, que hoy exporta `version`. Es un cambio de API, no una refactorización. |
| Añadir un *fallback* ante `PackageNotFoundError`, por ejemplo `__version__ = "unknown"` cuando el paquete no está instalado | Hoy la importación falla en ese caso. Capturar el error sería funcionalidad nueva, y las reglas lo prohíben. |
| Anotar el tipo (`__version__: str = ...`) | Aporta poco, porque `version()` ya está tipada como `str`. Además crearía `__annotations__` en el módulo, un efecto secundario innecesario en un archivo que no lo necesita. |
| Ampliar o reescribir el docstring | El docstring forma parte del módulo (`cookiecutter.__doc__`) y el actual describe correctamente el paquete. Cambiarlo no mejora la mantenibilidad. |

Forzar cambios en un módulo de tres líneas añadiría riesgo sin ganar legibilidad ni mantenibilidad. `cookiecutter/cli.py` depende de `__version__` y de que este módulo se comporte exactamente como ahora.