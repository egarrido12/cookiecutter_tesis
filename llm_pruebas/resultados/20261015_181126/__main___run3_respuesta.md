```python
"""Allow cookiecutter to be executable through `python -m cookiecutter`."""

from cookiecutter.cli import main

if __name__ == "__main__":
    main(prog_name="cookiecutter")
```

## Refactorizaciones aplicadas

**Ninguna.** El archivo se entrega sin cambios. Tiene tres líneas de código, ya sigue el idioma estándar de Python para `python -m paquete` y no presenta problemas de legibilidad ni de mantenibilidad. Cualquier cambio añadiría complejidad sin beneficio.

### Opciones evaluadas y descartadas

- **Replace Magic Literal** (extraer `"cookiecutter"` a una constante como `_PROG_NAME`)
  - *Elemento afectado:* el argumento `prog_name="cookiecutter"`.
  - *Motivo del descarte:* el literal no es "mágico". Se usa una sola vez y el nombre del argumento ya explica su significado. Una constante obligaría al lector a saltar a otra línea para entender lo mismo.

- **Extract Function** (envolver la llamada en una función privada `_run()`)
  - *Elemento afectado:* el bloque `if __name__ == "__main__":`.
  - *Motivo del descarte:* solo añadiría una capa de indirección. Además, el bloque de una línea es el patrón que cualquier desarrollador de Python reconoce al instante.

- **Move Statement** (llevar `from cookiecutter.cli import main` dentro del bloque `if`)
  - *Elemento afectado:* el import a nivel de módulo.
  - *Motivo del descarte:* alteraría el comportamiento observable. Hoy, importar `cookiecutter.__main__` expone el atributo `main` y carga `cookiecutter.cli` como efecto secundario, y algún test o herramienta podría depender de ello. La regla de mantener un comportamiento idéntico lo impide.

- **Añadir `from __future__ import annotations`** (por coherencia con el resto del paquete)
  - *Motivo del descarte:* el módulo no contiene anotaciones de tipo, así que la directiva no tendría ningún efecto y sería ruido.