```python
"""Allow cookiecutter to be executable through `python -m cookiecutter`."""

from cookiecutter.cli import main

if __name__ == "__main__":
    main(prog_name="cookiecutter")
```

## Refactorizaciones aplicadas

No apliqué ninguna. El archivo ya está en su forma más legible. Cualquier cambio añadiría indirección sin mejorar la legibilidad ni la mantenibilidad.

Estas son las refactorizaciones que evalué y por qué las descarté:

- **Extract Variable / Replace Magic Literal** sobre `"cookiecutter"`, por ejemplo con una constante `_PROG_NAME`:
  - El literal se usa una sola vez y es autoexplicativo gracias al argumento nombrado `prog_name=`.
  - Una constante obligaría al lector a saltar a otra línea para entender lo mismo.

- **Extract Function** del bloque `if __name__ == "__main__":`, por ejemplo con una función `_run()`:
  - El bloque tiene una única llamada.
  - Envolverla en una función solo crearía un nivel extra de indirección, sin reutilización ni posibilidad de test adicional. `cookiecutter.cli.main` ya es directamente testeable.

- **Eliminar el argumento `prog_name="cookiecutter"`** por considerarlo redundante: no es una refactorización válida porque cambia el comportamiento observable. Sin él, Click mostraría `__main__.py` (o `python -m cookiecutter`, según la versión) como nombre del programa en `--help` y en los mensajes de uso, en lugar de `cookiecutter`.

- **Añadir `from __future__ import annotations`** por consistencia con el resto del paquete: el módulo no tiene anotaciones de tipo, así que la importación no aportaría nada.

Se conservan intactos:
- el docstring del módulo;
- la importación de `main`, que tiene el efecto lateral de cargar `cookiecutter.cli` al importar el módulo, igual que antes;
- la guarda `__main__`.

El comportamiento es idéntico.