```python
"""Main package for Cookiecutter."""

from importlib.metadata import version

__version__ = version("cookiecutter")
```

## Refactorizaciones aplicadas

No apliqué ninguna. El archivo queda igual que el original.

El módulo tiene una sola responsabilidad: exponer `__version__` a partir de los metadatos del paquete instalado. Lo hace en una línea, con nombres claros, sin duplicación y sin lógica que extraer o simplificar. Cualquier cambio añadiría ruido sin mejorar la legibilidad ni la mantenibilidad.

### Refactorizaciones consideradas y descartadas

- **Introducir una constante** como `_PACKAGE_NAME = "cookiecutter"`.
  - Motivo del descarte: el literal aparece una sola vez y se entiende por sí mismo. La constante añade una indirección sin beneficio.

- **Rename / alias en la importación** (`from importlib.metadata import version as _version`) o **eliminar el nombre tras usarlo** (`del version`).
  - Motivo del descarte: mantendría limpio el espacio de nombres del paquete, pero cambia el comportamiento observable. Hoy `cookiecutter.version` existe como atributo del módulo, y algún código externo podría depender de él. Esto viola la regla de comportamiento idéntico.

- **Extract Function** (por ejemplo, `_get_version()`).
  - Motivo del descarte: encapsular una sola llamada a la biblioteca estándar no aporta claridad. Además añadiría un atributo nuevo al módulo.

- **Añadir un fallback** con `try/except PackageNotFoundError` para cuando el paquete no está instalado.
  - Motivo del descarte: sería funcionalidad nueva y cambiaría el comportamiento. Hoy, si el paquete no está instalado, se lanza la excepción.

El archivo ya está en su forma más simple. El esfuerzo de refactorización rinde más en otros módulos del paquete, por ejemplo `generate.py` (la función `generate_files` es larga y tiene varias responsabilidades), `main.py` o `zipfile.py`.