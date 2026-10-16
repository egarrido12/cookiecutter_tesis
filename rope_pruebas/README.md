# Pruebas de Cookiecutter con Rope

Este documento describe el proceso completo: qué se probó, cómo reproducirlo, qué resultados se obtuvieron y cómo interpretarlos. Es una réplica del experimento hecho sobre PySnooper (`../PySnooper_tesis/rope_pruebas/`), con la misma metodología y los mismos tipos de refactorización.

- **Proyecto bajo prueba:** Cookiecutter 2.7.1 (commit `c88fbe9`), carpeta `cookiecutter/` (2806 líneas en 18 módulos).
- **Herramienta:** [Rope](https://github.com/python-rope/rope) 1.15.0, una biblioteca de refactorización automática para Python.
- **Entorno:** Python 3.12.15, pytest 8.4.1, macOS (Darwin 24.6.0). El `.venv` del repositorio se creó con `uv` a partir de `uv.lock`.
- **Fecha de ejecución:** 2026-10-15.

> **Diferencia de entorno con PySnooper:** Cookiecutter requiere Python ≥ 3.10, así que no se pudo usar el Python 3.9.6 del sistema. Se instaló `uv` y se creó el entorno con Python 3.12.

---

## 1. Objetivo y metodología

La pregunta es: **¿las refactorizaciones automáticas de Rope conservan el comportamiento de Cookiecutter?**

La suite de tests de Cookiecutter sirve como oráculo:

1. **Línea base:** se corre la suite original y se anota el resultado de referencia.
2. **Análisis estático:** se usan las herramientas de análisis de Rope (`find_errors`, `find_occurrences`, `find_definition`) sin modificar código.
3. **Refactorizaciones:** cada refactorización se aplica con la API de Rope **sobre una copia limpia e independiente** del proyecto. Se guarda el diff y se vuelve a correr la suite completa.
4. **Veredicto:** si el número de tests que pasan es igual al de la línea base y no hay fallos ni errores, la refactorización **preserva el comportamiento**. Si no, **rompe tests**. Si Rope se niega a aplicarla, queda como **rechazada por Rope**.

Las refactorizaciones **02 a 12 reproducen una por una los tipos probados en PySnooper**, con la misma numeración: 5 Rename, 4 Extract Method, 1 Inline y 1 Move. Las **13 a 15 son casos nuevos** que aparecen por una característica de Cookiecutter: sus tests usan `mocker.patch('cookiecutter.modulo.funcion')` y `mocker.spy(modulo, 'funcion')`, es decir, **referencias a funciones escritas dentro de strings**. Es el equivalente en Cookiecutter del `.format(**locals())` de PySnooper: un acceso dinámico por nombre que el análisis estático no ve.

> El código original en `cookiecutter/` **nunca se modifica**. Todo se hace en `rope_pruebas/_trabajo/<experimento>/`.

---

## 2. Cómo ejecutarlo

Desde la raíz del repositorio:

```bash
# (una sola vez) crear el entorno con Python 3.12 y las dependencias de test
python3 -m pip install --user uv
~/Library/Python/3.9/bin/uv sync --python 3.12 --group test
~/Library/Python/3.9/bin/uv pip install --python .venv/bin/python rope anthropic

# 1) Línea base "a mano" (opcional, el script también la hace)
.venv/bin/python -m pytest tests -q -rs -o addopts=""

# 2) Todo el proceso: línea base + análisis estático + refactorizaciones
.venv/bin/python rope_pruebas/ejecutar_pruebas_rope.py
```

Tarda unos 40 segundos. Cada ejecución **borra y regenera** la carpeta `resultados/`.

Detalles técnicos del script, distintos de la versión de PySnooper:

- **`-o addopts=`** desactiva el `--cov` que `pyproject.toml` agrega a pytest. Así la corrida es más rápida y la salida se puede contar sin ruido.
- **`PYTHONPATH=<copia>`**: `uv sync` instala Cookiecutter en modo editable apuntando al repositorio original. `PYTHONPATH` hace que se importe la copia refactorizada. El script lo verifica (la ruta aparece en la consola).
- **`Project(..., ignore_syntax_errors=True)`**: ver la sección 4.1.
- La copia excluye `docs/`, `logo/`, `.github/` y `.git/`, que los tests no usan.

### Estructura de archivos

```
rope_pruebas/
├── README.md                    ← este documento
├── ejecutar_pruebas_rope.py     ← script que automatiza todo
├── .gitignore                   ← ignora _trabajo/
├── _trabajo/                    ← copias del proyecto, una por experimento (temporal)
└── resultados/
    ├── resumen.md               ← tabla resumen (se genera sola)
    ├── resumen.json             ← los mismos datos en JSON (para gráficos o tablas de la tesis)
    ├── 00_linea_base_pytest.txt ← salida completa de pytest de la línea base
    ├── 01_analisis_estatico.md  ← resultados de find_errors / find_occurrences / find_definition
    ├── NN_<nombre>.diff         ← cambios exactos que hizo Rope
    ├── NN_<nombre>_pytest.txt   ← salida de pytest después de la refactorización
    └── NN_<nombre>_error.txt    ← traceback, si Rope rechazó la refactorización
```

---

## 3. Paso 1: línea base (tests de Cookiecutter sin cambios)

| Resultado | Cantidad |
|---|---|
| Passed | **379** |
| Failed | 0 |
| Skipped | 4 |
| Errors | 0 |

Los 4 tests omitidos (`tests/test_generate_hooks.py:195` y 3 casos de `tests/test_prompt.py:640`) son exclusivos de Windows. Su omisión no indica ningún fallo.

**Referencia para comparar: 379 passed / 0 failed / 4 skipped.**

---

## 4. Paso 2: análisis estático con Rope

Detalle completo en [`resultados/01_analisis_estatico.md`](resultados/01_analisis_estatico.md).

### 4.1 Primer obstáculo: archivos `.py` que no son Python

Sin configuración extra, **Rope no puede ni empezar**. La primera operación que recorre el proyecto (`find_occurrences`) aborta con:

```
rope.base.exceptions.ModuleSyntaxError: Syntax error in file
<tests/hooks-abort-render/hooks/pre_gen_project.py> line <7>: invalid syntax
```

Cookiecutter es un generador de proyectos. Sus tests incluyen **19 archivos `.py` que en realidad son plantillas Jinja**, como `{% if cookiecutter.abort_pre_gen == "yes" %}`. Rope intenta analizarlos como Python y falla. La solución fue abrir el proyecto con `Project(ruta, ignore_syntax_errors=True)`.

Este problema no apareció en PySnooper. Muestra una limitación práctica: **una herramienta de análisis estático asume que todo `.py` es Python válido**, y eso no se cumple en proyectos de plantillas o generadores de código.

### 4.2 `find_occurrences`: búsqueda de referencias

| Símbolo | Ocurrencias encontradas | ¿Correcto? |
|---|---|---|
| `utils.create_env_with_context` | 10 (definición, imports y usos en `generate`, `hooks`, `prompt` y `tests/test_find.py`) | Sí |
| `repository.expand_abbreviations` | 7 (incluye imports y usos en 2 archivos de tests) | Sí |
| `ExtensionLoaderMixin._read_extensions` | 2 | Sí |
| `exceptions.CookiecutterException` | 18 (definición + 17 subclases) | Sí |
| `vcs.is_vcs_installed` | 3 | **Incompleto**: no cuenta las 5 rutas `'cookiecutter.vcs.is_vcs_installed'` de `tests/vcs/test_clone.py` (ver 5.4) |

### 4.3 `find_definition`: ir a la definición

Desde la llamada `create_env_with_context(context)` en `generate.py`, Rope resuelve bien la definición en `cookiecutter/utils.py:102`.

### 4.4 `find_errors`: detección de errores

Rope reporta **39 avisos** en 8 de los 18 módulos (`prompt`: 18, `generate`: 5, `main`: 5, `cli`: 3, `repository`: 3, `environment`: 2, `hooks`: 2, `vcs`: 1). Los revisé uno por uno y **los 39 son falsos positivos**. El código funciona y los 379 tests pasan.

| Categoría | Cant. | Ejemplos | Por qué es falso positivo |
|---|---|---|---|
| Variables de comprensiones o generadores | 24 | `main.py:119` (`k`, `v`), `prompt.py:120-122` (`i`, `p`), `hooks.py:70` (`hook_file`) | Rope no modela bien el alcance propio de las comprensiones |
| Atributos de bibliotecas externas o de objetos dinámicos | 11 | `prompt.py:38` (`Prompt.ask` de `rich`), `generate.py:251` (`rd.newlines`), `repository.py:24` (`re.VERBOSE`) | Rope no infiere bien los tipos de bibliotecas de terceros ni algunos de la biblioteca estándar |
| Parámetro keyword-only | 2 | `generate.py:68` (`in_dictionary_variable`, declarado después de `*`) | El parámetro existe; Rope no lo reconoce |
| Parámetro reasignado | 1 | `environment.py:28` (`context = context or {}`) | Reasignar un parámetro es válido |
| Variable implícita de módulo | 1 | `cli.py:41` (`__file__`) | `__file__` siempre existe en un módulo |

La primera categoría también aparece en PySnooper (14 de 31 avisos) y aquí es la causa directa del fallo de la refactorización 08 (sección 5.3).

---

## 5. Paso 3: refactorizaciones automáticas

### 5.1 Resultados

| # | Tipo | Qué se hizo | Archivos modificados | Tests (passed/failed) | Veredicto |
|---|---|---|---|---|---|
| 02 | Rename | `create_env_with_context` → `create_jinja_env` (usada en 3 módulos y en tests) | 5 | 379 / 0 | ✅ Preservado |
| 03 | Rename | `expand_abbreviations` → `expand_template_abbreviations` (importada por tests) | 3 | 379 / 0 | ✅ Preservado |
| 04 | Rename | método `ExtensionLoaderMixin._read_extensions` → `_extensions_from_context` | 1 | 379 / 0 | ✅ Preservado |
| 05 | Rename | clase `CookiecutterException` → `CookiecutterError` (17 subclases) | 1 | 379 / 0 | ✅ Preservado |
| 06 | Rename | parámetro `cwd` de `hooks.run_script` → `working_dir` | 1 | 379 / 0 | ✅ Preservado |
| 07 | Extract Method | detección de fin de línea en `generate_file` → `_detect_newline` | 1 | 379 / 0 | ✅ Preservado |
| 08 | Extract Method | bloque `if/else` que arma el contexto en `main.cookiecutter` → `_build_context` (2 valores de salida) | 1 | 333 / **46** | ❌ Rompe tests |
| 09 | Extract Method | bloque que termina en `continue` dentro del `for` de `generate_files` (caso límite) | — | — | ⛔ Rechazada por Rope |
| 10 | Extract Method | bucle de copia de directorios en `generate_files` → `_copy_dirs_without_rendering` | 1 | 379 / 0 | ✅ Preservado |
| 11 | Inline | `config._expand_path` dentro de `get_config` (2 llamadas) | 1 | 378 / **1** | ❌ Rompe tests |
| 12 | Move | `utils.make_executable` → módulo `hooks` | 2 | 379 / 0 | ✅ Preservado |
| 13 | Rename | `vcs.is_vcs_installed` → `is_vcs_available` (parcheada por string en tests) | 2 | 370 / **9** | ❌ Rompe tests |
| 14 | Rename | igual que 13, con `docs=True` | 2 | 370 / **9** | ❌ Rompe tests |
| 15 | Rename | `replay.get_file_name` → `get_replay_file_path` (espiada por string en tests) | 2 | 377 / **2** | ❌ Rompe tests |

**Totales:**

- **Casos equivalentes a PySnooper (02–12): 8 de 11 preservan el comportamiento (73 %)**, el mismo porcentaje que en PySnooper. 2 rompen tests y 1 la rechaza Rope.
- **Casos con referencias en strings (13–15): 0 de 3 preservan.**
- **Total: 8 de 14 (57 %).** Cada operación de Rope tardó menos de 0,4 s.

### 5.2 Rename, Move y Extract Method que funcionaron

- **02 y 03:** Rope actualizó todos los usos entre módulos, incluidos los `from cookiecutter.repository import expand_abbreviations` de `tests/repository/test_abbreviation_expansion.py` y `tests/repository/test_is_repo_url.py`.
- **05:** renombró la clase base y las 17 declaraciones `class X(CookiecutterException)`. Ningún otro módulo ni test usaba el nombre directamente, por eso solo cambió un archivo.
- **06:** todos los llamadores pasan `cwd` por posición, así que solo cambió la firma y el cuerpo de la función.
- **07 y 10:** extracciones correctas. Igual que en PySnooper, Rope deja **una sola línea en blanco** antes de la función nueva en vez de las dos de PEP 8.
- **12:** el resultado funciona, pero el diff tiene problemas de estilo que un linter detectaría:
  - Agrega `import stat` **después** del bloque de imports de `cookiecutter`, en lugar de ordenarlo con los imports de la biblioteca estándar (regla `I001` de ruff, que el proyecto usa).
  - Inserta la función entre los imports y `logger = ...` con una sola línea en blanco.
  - Elimina correctamente `from cookiecutter import utils`, que quedó sin usar.

### 5.3 Por qué fallan 08, 09 y 11

**08, Extract Method con dos valores de salida: dos errores de Rope en un solo cambio** ([diff](resultados/08_extract_contexto.diff)).

```python
k, v, context, context_for_prompting = _build_context(replay, context_file, config_dict, context_from_replayfile, extra_context)
```

1. **Toma variables de una comprensión como valores de salida.** `k` y `v` solo existen dentro de `{k: v for k, v in ...}`, pero Rope las devuelve (`return k, v, context, context_for_prompting`). En el camino sin `replay` eso produce `NameError: name 'k' is not defined`. Es el mismo error de alcance que `find_errors` ya reportaba en `main.py:119` como "Defined later k/v" (sección 4.4).
2. **Adelanta la lectura de una variable condicional.** `context_from_replayfile` solo se define si `replay` es verdadero, y el código original solo la lee dentro de `if replay:`. Rope la pasa **siempre** como argumento, así que en el caso normal (sin `replay`) falla con `UnboundLocalError`. Es la causa de la gran mayoría de los 46 fallos (al menos 38 terminan en `UnboundLocalError`; al menos 4, en el `NameError` del punto 1).

Rope **no dio ningún aviso**. Solo los tests detectan el problema.

**09, Extract Method con `continue`: Rope se niega, y está bien.** El bloque termina en `continue`, que salta a la siguiente iteración del `for` que está fuera del bloque. Rope responde `RefactoringError: A break/continue without having a matching for/while loop` y no modifica nada. Es un **fallo seguro**: Rope reconoce un caso que no puede transformar y lo rechaza, en lugar de generar código roto.

**11, Inline de una función que reasigna su parámetro: un error silencioso de Rope** ([diff](resultados/11_inline_funcion.diff)).

```python
# Original                                      # Después del Inline de Rope
def _expand_path(path):                         path = os.path.expandvars(raw_replay_dir)
    path = os.path.expandvars(path)             config_dict['replay_dir'] = os.path.expanduser(raw_replay_dir)
    return os.path.expanduser(path)
config_dict['replay_dir'] = _expand_path(raw_replay_dir)
```

`_expand_path` reasigna su parámetro `path`. Al hacer el inline, Rope sustituye `path` por el argumento (`raw_replay_dir`) **también en la segunda línea**. El resultado de `expandvars` queda en una variable que nadie lee y **las variables de entorno (`$COOKIES/...`) dejan de expandirse**. Solo un test cubre ese caso (`test_expand_vars_for_directories_in_config`). Si no existiera, el bug pasaría inadvertido. Además, el inline deja una variable `path` suelta en `get_config`.

### 5.4 Referencias en strings: 13, 14 y 15

Los tests de Cookiecutter reemplazan funciones con mocks indicando **su ruta como string**:

```python
mocker.patch('cookiecutter.vcs.is_vcs_installed', autospec=True, return_value=False)   # tests/vcs/test_clone.py
spy_get_replay_file = mocker.spy(replay, 'get_file_name')                               # tests/replay/test_dump.py
```

- **13:** Rope renombra la función, su llamada en `vcs.clone` y la llamada directa en `tests/vcs/test_is_vcs_installed.py`, pero **no los 5 strings** de `test_clone.py`. Al correr, `mocker.patch` falla con `AttributeError: <module 'cookiecutter.vcs'> does not have the attribute 'is_vcs_installed'` (9 tests, porque algunos están parametrizados).
- **14:** Rope ofrece la opción `docs=True` para "renombrar también en comentarios y strings". **El diff es idéntico al de 13.** Revisando el código de Rope (`rope/refactor/occurrences.py`), la opción solo incluye strings donde el nombre está **visible en el ámbito** (sigue aplicando el filtro `PyNameFilter`). En `test_clone.py`, `is_vcs_installed` nunca se importa, así que no hay coincidencia. Por eso ni siquiera se renombró el docstring `"""Verify `is_vcs_installed` function..."""`. Conclusión: **`docs=True` no sirve para rutas de `mock.patch`**.
- **15:** mismo problema con `mocker.spy(replay, 'get_file_name')`. 2 tests fallan con `AttributeError: module 'cookiecutter.replay' has no attribute 'get_file_name'`.

**Conclusión:** en PySnooper la referencia invisible para Rope era `locals()` en el código de producción. En Cookiecutter está en los **tests**: los mocks por string. En ambos casos el análisis estático no ve la dependencia, Rope aplica el cambio sin avisar y solo los tests revelan el error. Aquí, irónicamente, son los propios tests los que se rompen.

---

## 6. Conclusiones

1. **Rename y Move son confiables mientras todas las referencias sean código Python.** 6 de 6 preservaron el comportamiento (02–06 y 12), incluso con cambios que cruzan módulos y archivos de tests.
2. **Rename falla con referencias en strings** (13–15). La opción `docs=True` de Rope no lo resuelve. En proyectos con tests basados en `mock.patch('modulo.funcion')`, cada Rename de una función parcheada exige una búsqueda textual manual (`grep`).
3. **Extract Method falla con flujo de datos no trivial:** variables de comprensiones (08), variables definidas solo en una rama (08) y `break`/`continue` (09). La diferencia está en cómo falla: en 09 Rope **avisa y rechaza**, mientras que en 08 **genera código roto sin avisar**.
4. **Inline tiene un bug con parámetros reasignados** (11). Es un error silencioso que cambia el comportamiento y que un solo test detectó.
5. **Rope asume que todo `.py` es Python válido** (sección 4.1). En un proyecto de plantillas hay que usar `ignore_syntax_errors=True`.
6. **`find_errors` vuelve a tener 100 % de falsos positivos** (39/39), igual que en PySnooper (31/31). `find_occurrences` y `find_definition` son precisos para referencias de código, pero no ven los strings.
7. **Calidad de estilo:** igual que en PySnooper, las refactorizaciones correctas dejan imports desordenados (Move) y espaciado distinto a PEP 8 (Extract). Conviene pasar un formateador (`ruff format`, `ruff check --fix`) después de Rope.

### Comparación con PySnooper

| | PySnooper | Cookiecutter |
|---|---|---|
| Tamaño | 964 líneas, 5 módulos, 83 tests | 2806 líneas, 18 módulos, 379 tests |
| Casos equivalentes (02–12) que preservan | 8/11 (73 %) | 8/11 (73 %) |
| Rename (02–06) | 5/5 | 5/5 |
| Extract Method (07–10) | 1/4 | 2/4 (+1 rechazada) |
| Inline (11) | 1/1 | **0/1** (bug con parámetro reasignado) |
| Move (12) | 1/1 | 1/1 |
| Causa principal de los fallos | `.format(**locals())` en el código | mocks por string en los tests; flujo de datos (comprensiones, ramas) |
| Falsos positivos de `find_errors` | 31/31 | 39/39 |
| Obstáculo extra | — | archivos `.py` que son plantillas Jinja |

---

## 7. Cómo agregar una refactorización nueva

En `ejecutar_pruebas_rope.py`:

1. Escribe una función que reciba el proyecto Rope `p` y devuelva los cambios:

   ```python
   def ref_mi_prueba(p):
       r = p.get_resource('cookiecutter/utils.py')
       offset = offset_de(r, 'def work_in', 4)   # apunta al nombre
       return Rename(p, r, offset).get_changes('working_directory')
   ```

   - `offset_de(recurso, marcador, desplazamiento)` busca un texto **único** en el archivo y devuelve su posición. El desplazamiento mueve el cursor hasta el nombre (`'def '` = 4, `'class '` = 6).
   - Para Extract Method se necesita un rango `(inicio, fin)`. Ver `ref_extract_newline` como ejemplo (`inicio_de_linea` y `linea_anterior` ayudan a calcularlo).

2. Agrégala a la lista `REFACTORIZACIONES`:

   ```python
   ('16_mi_prueba', 'Rename', 'work_in -> working_directory', ref_mi_prueba),
   ```

   **Ojo:** el id no puede contener la palabra `tests`. Se usa como nombre de la carpeta de trabajo, y dos tests de Cookiecutter (`test_hooks.py`) verifican que `'tests'` no aparezca en la ruta actual. Esto produjo un falso fallo durante el desarrollo.

3. Vuelve a correr el script. La fila nueva aparece en `resultados/resumen.md`.

La API de Rope usada es la misma que en PySnooper (ver la tabla de referencia en `../PySnooper_tesis/rope_pruebas/README.md`, sección 7), más dos opciones:

| Opción | Dónde | Para qué |
|---|---|---|
| `ignore_syntax_errors=True` | `Project(ruta, ignore_syntax_errors=True)` | Ignorar archivos `.py` que no son Python válido |
| `docs=True` | `Rename(...).get_changes('nuevo', docs=True)` | Renombrar en strings y comentarios, **solo donde el nombre es visible** |
