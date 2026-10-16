# Pruebas de Cookiecutter con un LLM (prompt general)

Este documento describe el proceso completo: qué se probó, cómo reproducirlo, qué resultados se obtuvieron, cómo interpretarlos y cómo se comparan con las pruebas de Rope (`../rope_pruebas/`). Es una réplica del experimento hecho sobre PySnooper (`../PySnooper_tesis/llm_pruebas/`).

- **Proyecto bajo prueba:** Cookiecutter 2.7.1 (commit `c88fbe9`), carpeta `cookiecutter/` (2806 líneas en 18 módulos).
- **Modelo:** Claude Opus 5.5 (`claude-opus-5-5`), effort `high`, API de Anthropic (SDK `anthropic` 1.15.0).
- **Entorno:** Python 3.12.15, pytest 8.4.1, macOS (Darwin 24.6.0), `.venv` creado con `uv`.
- **Fecha de ejecución:** 2026-10-15.
- **Ejecución principal:** `resultados/20261015_181126/` (51 corridas: 17 módulos × 3).
- **Piloto:** `resultados/20261015_181046/` (1 corrida de `find`).

---

## 1. Objetivo y diferencia con Rope

La pregunta es: **cuando un LLM refactoriza Cookiecutter por su cuenta, ¿conserva el comportamiento? ¿Qué refactorizaciones elige?**

| | Rope | LLM |
|---|---|---|
| ¿Quién decide qué refactorizar? | La persona (offset + nombre nuevo) | **El modelo** |
| ¿Quién ejecuta el cambio? | Rope | El modelo |
| Instrucción | Una refactorización concreta por prueba (14 en total) | **Un único prompt general**, igual para todos los módulos |
| Determinismo | Total | No: el mismo prompt puede dar resultados distintos |

## 2. Metodología

Es la misma que en PySnooper. Los únicos cambios son el nombre del proyecto en el prompt y una verificación automática de la API pública.

1. **Prompt fijo y versionado:** [`prompt_v1.md`](prompt_v1.md). Es idéntico al de PySnooper salvo por la palabra "Cookiecutter". Pide mejorar legibilidad y mantenibilidad sin cambiar el comportamiento, con estas reglas:
   - no cambiar nombres ni firmas públicas;
   - no agregar funcionalidades ni dependencias;
   - modificar solo el archivo indicado;
   - mantener la compatibilidad con las versiones de Python soportadas.

   También pide devolver el archivo completo y una lista de las refactorizaciones aplicadas según el catálogo de Fowler.
2. **Contexto:** en cada llamada el modelo recibe **los 18 módulos del paquete** (~34 500 tokens) como contexto de solo lectura, más la instrucción `Refactoriza el archivo cookiecutter/<modulo>.py`. El contexto es idéntico en todas las llamadas, así que se reutiliza la caché de prompts.
3. **Unidad de trabajo:** un módulo por llamada.
4. **Repeticiones:** **3 corridas por módulo.** Opus 5.5 no permite fijar la temperatura, así que la variabilidad se mide repitiendo.
5. **Evaluación**, igual que con Rope:
   - se aplica el archivo devuelto sobre una **copia limpia** del proyecto;
   - se genera el diff;
   - se corre la suite completa (379 tests).

   Si pasan los mismos tests que en la línea base, sin fallos ni errores, el veredicto es **comportamiento preservado**.
6. **Verificación automática de la API pública (nuevo):** con `ast` se comparan, antes y después, los nombres públicos de nivel de módulo (funciones, clases, constantes e imports) y las firmas de las funciones y métodos públicos. Cualquier eliminación o cambio de firma queda en la columna "Cambios API pública". En PySnooper esto se hizo a mano.
7. **Análisis posterior:** clasificación según Fowler y comparación con los casos de Rope.

> El código original en `cookiecutter/` **nunca se modifica**. Cada ejecución se guarda en su propia carpeta `resultados/<fecha_hora>/`.

### 2.1 Alcance: 17 de 18 módulos

El plan inicial eran los 18 módulos (54 corridas), como en PySnooper, donde se hizo el paquete completo. A mitad de la ejecución se decidió **limitar el alcance a los módulos relevantes para la comparación con Rope**. Para entonces ya estaban hechas 50 corridas, así que se completó `vcs` y **solo quedó fuera `zipfile`** (125 líneas), que Rope no tocó en ninguna prueba.

### 2.2 Incidencias durante la ejecución

- **Corte de red:** la primera ejecución se detuvo en la corrida 15 (`environment_run3`) por un `ReadTimeout` en el streaming. La causa fue que el Mac entró en reposo al cerrar la tapa ("Clamshell Sleep" en `pmset -g log`). Se agregó al script:
  - reintentos automáticos ante errores de red;
  - la opción `--reanudar`, que continúa en la misma carpeta sin repetir ni pagar las corridas ya hechas, y antes verifica que el prompt, el modelo y el effort sean los mismos.

  Una corrida posterior (`exceptions_run1`) necesitó 1 reintento por el mismo motivo. Los reintentos no afectan los resultados: cada corrida registrada es una respuesta completa (`stop_reason = end_turn`).
- **Recomendación para repetir el experimento:** dejar el equipo conectado a la corriente y lanzar el script con `caffeinate -dimsu`.

## 3. Cómo ejecutarlo

Requiere una API key de Anthropic en `ANTHROPIC_API_KEY` (en este equipo está en `~/.zshrc`).

```bash
# ver el prompt exacto, sin llamar a la API ni gastar
.venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py --dry-run

# ejecución completa (18 módulos × 3 corridas, ~50 min de API, ~US$ 7)
caffeinate -dimsu .venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py

# la que se usó en la tesis (sin zipfile)
.venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py --modulos __init__ __main__ cli config \
    environment exceptions extensions find generate hooks log main prompt replay repository utils vcs

# continuar una ejecución interrumpida
.venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py --reanudar 20261015_181126

# variantes
.venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py --modulos main generate --corridas 5
.venv/bin/python llm_pruebas/ejecutar_pruebas_llm.py --modelo claude-sonnet-5-5
```

### Estructura de archivos

```
llm_pruebas/
├── README.md                  ← este documento
├── ejecutar_pruebas_llm.py    ← script que automatiza todo
├── prompt_v1.md               ← prompt general (versionado)
├── .gitignore                 ← ignora _trabajo/
├── _trabajo/                  ← copias del proyecto, una por corrida (temporal, se puede borrar)
└── resultados/
    └── <fecha_hora>/
        ├── resumen.md / resumen.json       ← tabla general, API, tokens, costo, determinismo
        ├── prompt.md                       ← copia del prompt usado
        ├── 00_linea_base_pytest.txt
        ├── <modulo>_run<n>_respuesta.md    ← respuesta completa del modelo (incluye su lista de refactorizaciones)
        ├── <modulo>_run<n>.py              ← archivo refactorizado
        ├── <modulo>_run<n>.diff            ← diff contra el original
        └── <modulo>_run<n>_pytest.txt      ← salida de pytest con ese archivo
```

---

## 4. Resultados

### 4.1 Línea base

`379 passed, 0 failed, 4 skipped, 0 errors`, idéntica a la de Rope.

### 4.2 Preservación del comportamiento: 51 de 51

| Módulo | Líneas | Tests en las 3 corridas | +/− líneas (rango) | Tiempo medio | Costo (3 corridas) |
|---|---|---|---|---|---|
| `__init__` | 5 | 379 / 0 / 0 ✅✅✅ | **sin cambios** | 20 s | US$ 0.10 |
| `__main__` | 6 | 379 / 0 / 0 ✅✅✅ | **sin cambios** | 13 s | US$ 0.09 |
| `cli` | 258 | 379 / 0 / 0 ✅✅✅ | +73…85 / −44…55 | 54 s | US$ 0.46 |
| `config` | 140 | 379 / 0 / 0 ✅✅✅ | +60…79 / −35…37 | 47 s | US$ 0.36 |
| `environment` | 71 | 379 / 0 / 0 ✅✅✅ | +14…17 / −12…13 | 28 s | US$ 0.38 |
| `exceptions` | 180 | 379 / 0 / 0 ✅✅✅ | +131…138 / −102…116 | 41 s | US$ 0.47 |
| `extensions` | 175 | 379 / 0 / 0 ✅✅✅ | +48…115 / −33…92 | 52 s | US$ 0.40 |
| `find` | 38 | 379 / 0 / 0 ✅✅✅ | +28…33 / −13 | 21 s | US$ 0.16 |
| `generate` | 466 | 379 / 0 / 0 ✅✅✅ | +262…292 / −165…178 | 108 s | US$ 0.89 |
| `hooks` | 201 | 379 / 0 / 0 ✅✅✅ | +56…65 / −38…44 | 53 s | US$ 0.42 |
| `log` | 56 | 379 / 0 / 0 ✅✅✅ | +22…30 / −17…18 | 25 s | US$ 0.20 |
| `main` | 212 | 379 / 0 / 0 ✅✅✅ | +106…128 / −54…56 | 85 s | US$ 0.67 |
| `prompt` | 438 | 379 / 0 / 0 ✅✅✅ | +146…190 / −112…142 | 132 s | US$ 1.02 |
| `replay` | 51 | 379 / 0 / 0 ✅✅✅ | +15…40 / −9…15 | 19 s | US$ 0.16 |
| `repository` | 139 | 379 / 0 / 0 ✅✅✅ | +52…61 / −28…34 | 40 s | US$ 0.27 |
| `utils` | 106 | 379 / 0 / 0 ✅✅✅ | +17…21 / −13…14 | 39 s | US$ 0.29 |
| `vcs` | 139 | 379 / 0 / 0 ✅✅✅ | +84…94 / −52…55 | 59 s | US$ 0.45 |
| **Total** | **2681** | **51 / 51 preservan** | | **49 s** | **US$ 6.80** |

- No hubo errores de sintaxis, respuestas truncadas, rechazos ni fallback a otro modelo: las 51 respuestas las generó `claude-opus-5-5`.
- Tokens: 305 416 de salida (incluye el razonamiento interno), 1 693 538 de entrada leídos desde la caché y 69 124 escritos en caché.
- **Costo:**

  | Concepto | US$ |
  |---|---|
  | Corridas registradas | 6.80 |
  | Piloto | 0.21 |
  | Llamadas interrumpidas por los cortes de red y por la detención antes de `zipfile` (no registradas; estimado) | < 0.50 |
  | **Total aproximado** | **7.0–7.5** |

Detalle por corrida: [`resultados/20261015_181126/resumen.md`](resultados/20261015_181126/resumen.md).

### 4.3 El modelo decide no refactorizar lo que no lo necesita

En `__init__` (5 líneas) y `__main__` (6 líneas), las 3 corridas devolvieron **el archivo sin cambios**. En la respuesta, el modelo explica qué transformaciones consideró y por qué las descartó. Por ejemplo, en `__init__`:

> - Añadir `__all__`: "cambiaría el resultado de `from cookiecutter import *`… es un cambio de API".
> - Un *fallback* ante `PackageNotFoundError`: "sería funcionalidad nueva, y las reglas lo prohíben".

En PySnooper, el modelo sí modificó `__init__` (renombró `__VersionInfo`). Aquí **se abstuvo explícitamente**, aplicando las reglas del prompt.

### 4.4 Refactorizaciones elegidas por el modelo

Esta clasificación sale de la lista que el modelo entrega al final de cada respuesta, contrastada con las funciones y constantes nuevas que aparecen en los diffs.

| Módulo | Lo que aparece en **las 3 corridas** | Variaciones entre corridas |
|---|---|---|
| `generate` | Extract Function en `generate_file` (cálculo del fin de línea: `_determine_newline` / `_get_newline`; copia con permisos `_copy_file_with_permissions`); **descomposición de `generate_files`** (`_split_copy_and_render_dirs`, `_copy_dir(s)_without_render`, `_create_rendered_dir(s)`, **`_copy_file_without_render`**); extracción de las conversiones de `apply_overwrites_to_context` (`_convert_overwrite_to_bool`, multichoice, choice); `_load_context_file` en `generate_context` | Nombres; la corrida 1 crea también `_render_string` y `_generate_files_in_dir` |
| `main` | Extract Function: validación del modo replay (`_check_replay_mode_compatibility`), carga del replay (`_load_replay_context`), **variables que faltan en el replay** (`_prompting_context_for_replay` / `_variables_missing_from_replay`), opciones públicas (`_public_variables`), detección de plantillas anidadas (`_has_nested_templates`), metadatos de generación (`_add_generation_metadata`) | Las corridas 2 y 3 unifican las dos llamadas a `generate_context` en una sola (`extra_context=None if replay else extra_context`), justificándolo con la validación del modo; la corrida 3 extrae además el hook pre-prompt |
| `prompt` | Extract Function en `prompt_for_config` (`_prompt_for_simple_variable`, `_progress_prefix`, predicados `_is_private_variable`…); `_format_choice_line` en `read_user_choice` (reemplaza `starmap` por un generador y elimina 1–2 imports); `_delete_path` en `prompt_and_delete`; constante `DEFAULT_DISPLAY` | Cuántos predicados extrae; la corrida 3 separa la elección de plantillas nuevas y antiguas |
| `vcs` | Constante `_SUPPORTED_REPO_TYPES`; descomposición de `clone` (directorio destino, decisión de clonar, comandos de clone/checkout, `_raise_for_known_clone_error`) | Cómo agrupa los comandos de clone y checkout |
| `cli` | Replace Magic Literal (separador `=`, nombre de archivo de configuración, variable de entorno de la contraseña); Extract Function (`_ensure_key_value_form`, `_find_installed_templates`, `_is_help_requested`, `_resolve_accept_hooks`, `_report_undefined_variable`); tupla de excepciones reportadas al usuario | Nombres de constantes y funciones |
| `config` | Constantes `_CONFIG_ENV_VAR` y lista de claves de rutas; Extract Function (`_read_yaml_config`, `_expand_config_paths`); **conserva `_expand_path`** y la aplica en un bucle | La corrida 2 separa más la lógica de `get_user_config` |
| `hooks` | `_build_script_command`, mensaje de `OSError` (`_describe_os_error` / `_os_error_message`), `_render_script`; constante `_PRE_PROMPT_HOOK` | La corrida 2 agrega una tupla de errores de hooks |
| `repository` | Constante del nombre `cookiecutter.json`; `_get_repository_candidates`; mensaje de `RepositoryNotFound` | Nombres |
| `extensions` | Constante del formato de fecha por defecto; `_parse_shift_params` y `_parse_datetime_format` en `TimeExtension.parse`; `_resolve_datetime_format` | Tamaño muy variable (+48 a +115): la corrida 3 extrae los filtros como funciones de módulo (`_jsonify`, `_slugify`, `_uuid4`…) y agrega una constante **pública** `DEFAULT_DATETIME_FORMAT` (ver 4.6) |
| `exceptions` | **Slide Statements:** reordena las 17 excepciones en secciones temáticas (configuración, repositorios, plantillas, ejecución); mejora comentarios y docstrings | Solo el texto de los comentarios |
| `replay`, `find`, `log`, `utils`, `environment` | Cambios pequeños: constantes (`_REQUIRED_CONTEXT_KEY`, extensión `.json`, nombre del logger, `_DEFAULT_EXTENSIONS`); una función de validación o de handler; Rename Variable | `utils` corrida 3 agrega anotaciones de tipo a `force_delete` y `simple_filter`; `environment` corrida 3 extrae `_collect_extensions` (extensiones por defecto + `_read_extensions`) |

**Tipos más frecuentes** (corridas en que aparecen, de 51):

| Tipo | Corridas |
|---|---|
| Extract Function/Method | ~42 |
| Rename Variable | 33 |
| Replace Magic Literal | 24 |
| Inline Variable | 11 |
| Replace Nested Conditional with Guard Clauses | 10 |
| Substitute Algorithm | 10 |

Le siguen Extract Variable, Consolidate Duplicate Conditional Fragments, Simplify Conditional Expression, Remove Dead Code, Slide Statements y Split Variable. Igual que en PySnooper, **no usó Move ni Inline Function**: el prompt limita los cambios a un archivo.

### 4.5 Determinismo

| Módulos | Corridas | Diffs distintos |
|---|---|---|
| `__init__`, `__main__` | 3 | **1** (los 3 vacíos) |
| los otros 15 | 3 | **3** |

Fuera de los dos módulos que no tocó, ninguna corrida produjo un diff idéntico a otra. Igual que en PySnooper, **la estrategia es estable**: en `generate` y `main` las 3 corridas extraen prácticamente los mismos bloques. Lo que cambia son los nombres, los docstrings y el grado de detalle. La única variación de fondo importante es `extensions`, donde el tamaño del cambio va de +48 a +115 líneas.

### 4.6 Respeto de la API pública (verificación automática con `ast`)

| Cambio detectado | Corridas | ¿Rompe algo? |
|---|---|---|
| Eliminado `import starmap` (`prompt`) | 2/3 | No: dejó de usarse al reemplazar `starmap` por un generador. Solo desaparece como atributo del módulo |
| Eliminado `import Iterator` (`prompt`) | 1/3 | No, por la misma razón |

Ningún nombre público usado por otros módulos o por los tests cambió de nombre ni de firma en las 51 corridas. Esto incluye las funciones que los tests parchean por string (`cookiecutter.main.generate_files`, `cookiecutter.vcs.is_vcs_installed`, etc.).

Un detalle que el verificador no marca, porque es una **adición**: en `extensions_run3` el modelo creó la constante pública `DEFAULT_DATETIME_FORMAT` (sin `_`). No rompe nada, pero amplía la API pública. Es una **infracción menor del espíritu del prompt** ("no agregues funcionalidades"), similar al cambio de nombre de parámetro observado en PySnooper.

---

## 5. Comparación con Rope

### 5.1 Los casos clave: las mismas extracciones que rompieron Rope

En dos casos, **el LLM extrajo por su cuenta los mismos bloques** que en las pruebas de Rope dieron problemas, sin recibir ninguna instrucción. Además, hizo las extracciones que a Rope le salieron bien:

| Bloque | Rope | Resultado de Rope | LLM (3 corridas) | Resultado del LLM |
|---|---|---|---|---|
| Fin de línea en `generate_file` | `_detect_newline` (07) | ✅ 379 / 0 | `_determine_newline` / `_get_newline` | ✅ 3/3 |
| Copia de directorios sin renderizar | `_copy_dirs_without_rendering` (10) | ✅ 379 / 0 | `_copy_dir(s)_without_render` | ✅ 3/3 |
| Copia de archivo sin renderizar (termina en `continue`) | `_copy_file_without_rendering` (09) | ⛔ rechazada | `_copy_file_without_render(infile, project_dir, context, env)` | ✅ 3/3 |
| Contexto en modo `replay` (comprensión `k, v` + variable condicional) | `_build_context` (08) | ❌ 333 / 46 | `_prompting_context_for_replay` / `_variables_missing_from_replay` / `_context_missing_from_replay` | ✅ 3/3 |
| `_expand_path` en `config` | Inline (11) | ❌ 378 / 1 (bug) | **no la elimina**; la reutiliza en un bucle sobre las claves de rutas | ✅ 3/3 |

**Por qué el LLM lo logra donde Rope falla:**

- **09 (`continue`):** Rope intentó extraer el bloque *con* el `continue` y lo rechazó, porque el salto apunta a un bucle externo. El LLM extrajo solo el **cuerpo útil** (calcular la ruta y copiar) y **dejó el `continue` en el bucle**:

  ```python
  if is_copy_only_path(infile, context):
      _copy_file_without_render(infile, project_dir, context, env)
      continue
  ```

  Es decir, eligió un límite de extracción distinto, que hace la refactorización posible.
- **08 (contexto de `replay`):** Rope extrajo el `if/else` completo. Eso le exigía devolver varios valores, y se equivocó dos veces: devolvió `k, v` de la comprensión y adelantó la lectura de `context_from_replayfile`. El LLM **dejó el `if replay:` en el llamador** y extrajo solo el cálculo de las variables pendientes. Ese cálculo devuelve **un único valor** y se llama solo dentro de la rama donde `context_from_replayfile` existe:

  ```python
  if replay:
      context = replay_context
      context_for_prompting = _prompting_context_for_replay(context_file, ..., replay_context)
  else:
      ...
  ```

  Las variables de la comprensión quedan dentro de la función nueva (renombradas a `key, value`), donde no pueden escaparse.

En PySnooper, la clave era que el LLM eliminaba primero los `.format(**locals())`. Aquí, la clave es que **elige el límite del bloque** para que la extracción tenga una sola salida y no arrastre flujo de control. Es la misma idea: el LLM **reestructura el código para que la refactorización sea segura**, mientras que Rope aplica mecánicamente la transformación sobre el rango que se le da.

### 5.2 Referencias en strings (mocks)

Los casos 13 a 15 de Rope fallaron porque los tests referencian funciones por string (`mocker.patch('cookiecutter.vcs.is_vcs_installed')`). El LLM **nunca tuvo ese problema**, pero por un motivo distinto a la "comprensión": el prompt le prohíbe renombrar elementos públicos, y todas las funciones parcheadas son públicas.

Tampoco renombró ningún elemento privado que los tests usen por nombre. Por ejemplo, conservó `_read_extensions`, el método que Rope renombró en la prueba 04. **El experimento no demuestra que el LLM detecte referencias en strings de otros archivos**: el modelo solo veía el paquete, no los tests.

### 5.3 Resto de los tipos

| Tipo | Rope | LLM |
|---|---|---|
| Rename (función, método, clase, parámetro) | 5/5 en casos normales; **0/3 con referencias en strings** | Solo renombra **elementos privados o locales** (el prompt prohíbe tocar la API pública); 51/51 preservan |
| Extract Method | 2/4 preservan (+1 rechazada; falla con flujo de datos no trivial) | Es su refactorización principal (42 de 51 corridas); todas preservan |
| Inline | 0/1 (bug con parámetro reasignado) | No usa Inline Function; sí Inline Variable (11 corridas) |
| Move | 1/1 preserva | No lo usa (un archivo por llamada); sí Slide Statements dentro del archivo |
| Otros (Magic Literal, Guard Clauses, Substitute Algorithm, Dead Code, docstrings) | No disponibles en Rope | Los usa con frecuencia |

### 5.4 Resumen

| Criterio | Rope | LLM (Opus 5.5) |
|---|---|---|
| Preservación del comportamiento | 8/14 (57 %); 8/11 en los casos equivalentes a PySnooper | **51/51 corridas (100 %)** |
| Decide qué refactorizar | No | Sí (y decide **no** tocar `__init__` ni `__main__`) |
| Determinismo | Total | Estrategia estable, texto variable (3/3 diffs distintos en 15 módulos) |
| Alcance de cada cambio | Pequeño y acotado (1 operación) | Grande (hasta +292 líneas en un módulo, muchas operaciones juntas) |
| Cambios en varios archivos | Sí (actualiza los usos en código, pero no en strings) | No en este diseño (un archivo por llamada) |
| Tiempo | < 0,4 s por refactorización | 12–167 s por corrida |
| Costo | Gratis | US$ 0.03–0.43 por corrida (US$ 6.80 en total) |
| Revisabilidad | Diff mínimo y predecible | Diff grande que requiere revisión humana |
| Obstáculos del proyecto | Archivos `.py` que son plantillas Jinja (requirió `ignore_syntax_errors`) | Ninguno |

### 5.5 Comparación entre proyectos

| | PySnooper | Cookiecutter |
|---|---|---|
| Rope: casos equivalentes que preservan | 8/11 | 8/11 |
| Rope: causa principal de los fallos | `.format(**locals())` | flujo de datos (comprensiones, ramas, parámetro reasignado) y mocks por string |
| LLM: corridas que preservan | 15/15 | 51/51 |
| LLM: costo | US$ 2.55 | US$ 6.80 |
| LLM: ¿extrajo los bloques donde Rope falló? | Sí (07, 08, 09), los 3 preservan | Sí (08, 09), los 2 preservan |
| LLM: infracciones menores del prompt | Cambio de nombre de un parámetro posicional | Constante pública nueva (`DEFAULT_DATETIME_FORMAT`) |

**Conclusión:** los resultados de PySnooper se reproducen en un segundo proyecto, 3 veces más grande y con 4,5 veces más tests. Rope es preciso pero frágil ante dependencias que su análisis estático no ve. El LLM preserva el comportamiento en todas las corridas y, en los mismos bloques donde Rope falla, **adapta la refactorización** para que sea segura.

---

## 6. Limitaciones y amenazas a la validez

1. **Los tests son el único oráculo.** Pasar los 379 tests no demuestra que la refactorización sea equivalente. Algunas ramas no se ejercitan en este entorno: las específicas de Windows (4 tests omitidos), algunos errores de red de `vcs` y `zipfile`. Los cambios del LLM en esas zonas habría que revisarlos a mano.
2. **Diffs grandes.** En `generate` el LLM cambia más de 400 líneas por corrida (sumando agregadas y eliminadas). Si algo fallara sería difícil aislar la causa, y revisar el diff cuesta más que con Rope.
3. **Un solo modelo, un solo prompt.** Los resultados corresponden a `claude-opus-5-5`, effort `high` y `prompt_v1.md`.
4. **3 corridas por módulo** bastan para observar variabilidad, pero no para estimar con precisión una tasa de error. 51/51 no descarta una tasa baja pero no nula.
5. **Comparación no simétrica.** Rope recibió 14 operaciones elegidas por una persona (incluidos casos límite a propósito). El LLM eligió las suyas. La sección 5.1 compara los casos donde ambos hicieron la misma operación sobre el mismo bloque.
6. **La lista de refactorizaciones la escribe el propio modelo.** Se contrastó con las funciones nuevas de cada diff y con `ast` para la API, pero no se verificó cada elemento de forma exhaustiva. El conteo de tipos (4.4) es aproximado: algunas respuestas mezclan varios tipos en un mismo punto.
7. **`zipfile` quedó fuera** (sección 2.1). Las conclusiones sobre el paquete cubren 2681 de 2806 líneas (96 %).
8. **El modelo no veía los tests.** Por eso no se puede concluir que el LLM detectaría referencias en strings, como los mocks, si se le pidiera renombrar algo público (sección 5.2).

## 7. Próximos pasos posibles

- Repetir con otros modelos o proveedores (Sonnet 5.5, OpenAI, Gemini, un modelo local con Ollama) para comparar varios LLM contra Rope en los dos proyectos.
- **Prompt con los tests en el contexto y permiso para cambios públicos:** permitiría comparar directamente con los Rename 13–15 de Rope (¿actualiza el LLM los strings de `mocker.patch`?).
- Correr `zipfile` (3 corridas, ~US$ 0.4) para completar el paquete.
- Pasar `ruff check` sobre los archivos del LLM y de Rope para comparar la calidad de estilo de forma objetiva.
