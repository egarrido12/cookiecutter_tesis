```python
"""Allow cookiecutter to be executable through `python -m cookiecutter`."""

from cookiecutter.cli import main

if __name__ == "__main__":
    main(prog_name="cookiecutter")
```

## Refactorizaciones aplicadas

**Ninguna.** El archivo no cambia. El módulo ya es mínimo y legible, y cualquier cambio añadiría complejidad o pondría en riesgo el comportamiento:

- **Tiene una sola responsabilidad:** sirve como punto de entrada para `python -m cookiecutter`.
- **Consta de tres sentencias:** el docstring, una importación y la invocación protegida por `if __name__ == "__main__"`.
- **Delega toda la lógica** en `cookiecutter.cli.main`.

Refactorizaciones que consideré y descarté:

- **Replace Magic Literal (extraer `"cookiecutter"` a una constante `_PROG_NAME`):** el literal aparece una sola vez. Además, el argumento con nombre `prog_name=` ya explica su significado. Una constante añadiría una indirección sin mejorar la claridad.
- **Extract Function (envolver la llamada en una función privada `_run()`):** no hay lógica que aislar ni reutilizar. Solo añadiría un nivel de llamada.
- **Mover la importación dentro del bloque `if __name__ == "__main__"`:** cambiaría el comportamiento observable. Hoy, `import cookiecutter.__main__` expone `main` como atributo del módulo y carga `cookiecutter.cli` como efecto secundario, y algún test o herramienta podría depender de ello.
- **Cambiar la forma de invocar `main` (por ejemplo, pasar `standalone_mode` u otros argumentos de Click):** alteraría la gestión de errores y los códigos de salida. Eso sería un cambio de comportamiento, no una refactorización.

La mejor decisión aquí es dejar el archivo como está.