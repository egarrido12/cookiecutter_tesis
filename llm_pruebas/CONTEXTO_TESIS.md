# Contexto del experimento Rope vs LLM en Cookiecutter, para redactar la tesis

Este documento resume todo lo que se hizo en el repositorio `cookiecutter_tesis`, para que un asistente de redacción tenga el contexto completo sin acceso al código. Es el segundo proyecto del estudio; el primero es PySnooper (`../PySnooper_tesis/llm_pruebas/CONTEXTO_TESIS.md`). Los detalles están en `llm_pruebas/README.md` y `rope_pruebas/README.md`.

---

## 1. Qué se compara

- **Objeto de estudio:** Cookiecutter 2.7.1 (commit `c88fbe9`), paquete `cookiecutter/`: 18 módulos, 2806 líneas. Es unas 3 veces más grande que PySnooper (964 líneas).
- **Oráculo:** la suite de tests del proyecto. Línea base: **379 passed, 0 failed, 4 skipped** (los 4 son tests solo para Windows). Una refactorización "preserva el comportamiento" si después pasan los mismos 379 tests sin fallos ni errores.
- **Rope** (1.15.0): una persona elige 14 refactorizaciones concretas y Rope las ejecuta. Las 02–12 reproducen los tipos y la numeración de PySnooper; las 13–15 son casos nuevos propios de Cookiecutter (2026-10-15).
- **LLM** (Claude Opus 5.5): recibe el **mismo prompt general** que en PySnooper (solo cambia el nombre del proyecto) y decide qué refactorizar (2026-10-15).
- En ambos casos cada refactorización se aplica sobre una **copia limpia** del proyecto, se guarda el diff y se corren los tests. El código original nunca se modifica.
- **Entorno:** Python 3.12.15, pytest 8.4.1, macOS. Cookiecutter requiere Python ≥ 3.10, así que no se pudo usar el Python 3.9.6 del sistema que se usó con PySnooper; el entorno se creó con `uv` a partir del `uv.lock` del proyecto.

## 2. Resultados de Rope (14 refactorizaciones)

| # | Tipo | Descripción | Tests (passed/failed) | Veredicto |
|---|---|---|---|---|
| 02 | Rename | `utils.create_env_with_context` → `create_jinja_env` (3 módulos + tests) | 379 / 0 | Preserva |
| 03 | Rename | `repository.expand_abbreviations` → `expand_template_abbreviations` (importada por tests) | 379 / 0 | Preserva |
| 04 | Rename | `ExtensionLoaderMixin._read_extensions` → `_extensions_from_context` | 379 / 0 | Preserva |
| 05 | Rename | clase `CookiecutterException` → `CookiecutterError` (17 subclases) | 379 / 0 | Preserva |
| 06 | Rename | parámetro `cwd` de `hooks.run_script` → `working_dir` | 379 / 0 | Preserva |
| 07 | Extract Method | detección de fin de línea de `generate_file` → `_detect_newline` | 379 / 0 | Preserva |
| 08 | Extract Method | `if/else` que arma el contexto en `main.cookiecutter` → `_build_context` (2 valores de salida) | 333 / 46 | **Rompe** |
| 09 | Extract Method | bloque que termina en `continue` dentro del `for` de `generate_files` | — | **Rechazada por Rope** |
| 10 | Extract Method | bucle de copia de directorios de `generate_files` → `_copy_dirs_without_rendering` | 379 / 0 | Preserva |
| 11 | Inline | `config._expand_path` en `get_config` | 378 / 1 | **Rompe** |
| 12 | Move | `utils.make_executable` → `hooks` | 379 / 0 | Preserva |
| 13 | Rename | `vcs.is_vcs_installed` → `is_vcs_available` (parcheada por string en tests) | 370 / 9 | **Rompe** |
| 14 | Rename | igual que 13, con la opción `docs=True` | 370 / 9 | **Rompe** |
| 15 | Rename | `replay.get_file_name` → `get_replay_file_path` (espiada por string en tests) | 377 / 2 | **Rompe** |

Totales:

- **Casos equivalentes a PySnooper (02–12): 8/11 preservan (73 %)**, el mismo porcentaje que en PySnooper.
- **Casos nuevos (13–15): 0/3.**
- **Total: 8/14 (57 %).**

Causa de cada fallo:

- **08:** Rope tomó las variables `k, v` de una comprensión de diccionario como valores de salida (`return k, v, context, ...`) → `NameError`. Además, pasó como argumento `context_from_replayfile`, que solo existe si `replay` es verdadero → `UnboundLocalError` en el caso normal. Rope no dio ningún aviso.
- **09:** Rope **rechaza** la extracción (`RefactoringError: A break/continue without having a matching for/while loop`). Es un fallo seguro: no genera código roto.
- **11:** bug de Rope. `_expand_path` reasigna su parámetro (`path = os.path.expandvars(path)`); al hacer el inline, Rope sustituye el parámetro también en la segunda línea y se pierde la expansión de variables de entorno. Error silencioso; solo 1 test lo detecta.
- **13–15:** los tests referencian las funciones **dentro de strings** (`mocker.patch('cookiecutter.vcs.is_vcs_installed')`, `mocker.spy(replay, 'get_file_name')`). El análisis estático de Rope no los ve. La opción `docs=True` **no lo resuelve**: según el código de Rope, solo renombra strings donde el nombre es visible en el ámbito. Es el equivalente en Cookiecutter del `.format(**locals())` de PySnooper, pero en los tests en vez de en el código de producción.

Otros hallazgos de Rope:

- **Rope no podía ni empezar:** los tests incluyen 19 archivos `.py` que en realidad son plantillas Jinja (`{% if ... %}`). Hubo que abrir el proyecto con `Project(ruta, ignore_syntax_errors=True)`.
- `find_errors` reportó **39 avisos y los 39 son falsos positivos** (PySnooper: 31/31). 24 son variables de comprensiones (el mismo error de alcance que causa el fallo 08), 11 son atributos de bibliotecas externas, 2 son parámetros keyword-only, 1 es un parámetro reasignado y 1 es `__file__`.
- Estilo: igual que en PySnooper, las refactorizaciones correctas dejan imports desordenados (Move) y una sola línea en blanco antes de las funciones extraídas.

## 3. Configuración del LLM (datos para la Tabla 5.7)

| Elemento | Valor |
|---|---|
| Modelo | `claude-opus-5-5` (Claude Opus 5.5, Anthropic) |
| Herramienta de acceso | SDK oficial de Anthropic para Python, `anthropic` 1.15.0 (en PySnooper fue 0.125.0, por la restricción de Python 3.9) |
| Interfaz | Messages API (`/v1/messages`), modo streaming |
| Autenticación | API key personal de la consola de Anthropic, leída de la variable de entorno `ANTHROPIC_API_KEY` (no aparece en el código) |
| Script | `llm_pruebas/ejecutar_pruebas_llm.py` (Python 3.12.15) |
| Effort | `high` |
| Thinking | Adaptativo (siempre activo en este modelo) |
| Temperatura | No configurable: la API la rechaza en este modelo, así que la variabilidad se mide repitiendo corridas |
| `max_tokens` | 64 000 |
| Fallback de refusals | `fallbacks: "default"`; no se activó en ninguna corrida (las 51 respuestas son de `claude-opus-5-5`) |
| Caché de prompts | `cache_control: ephemeral` sobre el contexto (~34 500 tokens; no afecta a la respuesta) |
| Unidad de trabajo | **Un módulo por llamada** |
| Módulos | 17 de 18: `__init__`, `__main__`, `cli`, `config`, `environment`, `exceptions`, `extensions`, `find`, `generate`, `hooks`, `log`, `main`, `prompt`, `replay`, `repository`, `utils`, `vcs`. Quedó fuera `zipfile` (ver sección 10) |
| Repeticiones | 3 corridas por módulo = **51 llamadas** (+1 piloto) |
| Costo | US$ 6.80 la ejecución principal; ~US$ 7.0–7.5 contando el piloto (US$ 0.21) y las llamadas interrumpidas |
| Tiempo | 12–167 s por llamada (media 49 s) |
| Tokens | 305 416 de salida; 1 693 538 de entrada leídos desde caché; 69 124 escritos en caché |
| Novedad respecto de PySnooper | Verificación automática de la API pública con `ast` en cada corrida (en PySnooper se hizo a mano) |

## 4. Prompt v1 (texto exacto)

**Mensaje de sistema** (`llm_pruebas/prompt_v1.md`):

```
Eres un ingeniero de software experto en Python. Tu tarea es refactorizar un módulo del proyecto Cookiecutter para mejorar su legibilidad y mantenibilidad, sin cambiar su comportamiento.

Reglas:
- El comportamiento observable debe ser idéntico al original.
- No cambies los nombres ni las firmas de las funciones, clases y métodos públicos (los que no empiezan con "_"), porque otros módulos y los tests los usan.
- No agregues funcionalidades nuevas ni dependencias.
- Modifica solo el archivo indicado; el resto del paquete se muestra como contexto de solo lectura.
- Mantén la compatibilidad con las versiones de Python que el proyecto ya soporta.

Formato de respuesta:
1. El archivo completo refactorizado, en un único bloque ```python.
2. Después, una sección "## Refactorizaciones aplicadas" con una lista: tipo de refactorización (según el catálogo de Fowler, por ejemplo Extract Method, Rename Variable, Inline Function...), elementos afectados y motivo.
```

La única diferencia con el prompt de PySnooper es la palabra "Cookiecutter" en la primera línea.

**Mensaje de usuario:** el código completo de los 18 módulos dentro de etiquetas `<archivo ruta="cookiecutter/...">…</archivo>`, seguido de la instrucción `Refactoriza el archivo cookiecutter/<modulo>.py.` El modelo **no ve los tests**.

## 5. Resultados del LLM

- **51/51 corridas preservan el comportamiento** (379 passed en todas). No hubo errores de sintaxis, respuestas truncadas, rechazos ni fallback.
- **Módulos que decidió no tocar:** en `__init__` (5 líneas) y `__main__` (6 líneas) las 3 corridas devolvieron el archivo sin cambios. El modelo explicó qué transformaciones consideró y por qué las descartó, por ejemplo que agregar `__all__` "cambiaría el resultado de `from cookiecutter import *`". En PySnooper, en cambio, sí modificó `__init__`.
- **Tamaño de los diffs (líneas agregadas):**
  - `environment` +14…17, `utils` +17…21, `replay` +15…40, `log` +22…30, `find` +28…33;
  - `hooks` +56…65, `repository` +52…61, `config` +60…79, `cli` +73…85, `vcs` +84…94, `extensions` +48…115;
  - `main` +106…128, `exceptions` +131…138, `prompt` +146…190, `generate` +262…292.
- **Determinismo:** los 15 módulos modificados dieron 3 diffs distintos en 3 corridas. La **estrategia es muy estable**: en `generate` y `main` las 3 corridas extraen prácticamente los mismos bloques; cambian los nombres, los docstrings y el nivel de detalle. La excepción es `extensions` (de +48 a +115 líneas según la corrida).
- **Tipos más usados (corridas en que aparecen, de 51):**

  | Tipo | Corridas |
  |---|---|
  | Extract Function/Method | ~42 |
  | Rename Variable (solo elementos privados o locales) | 33 |
  | Replace Magic Literal | 24 |
  | Inline Variable | 11 |
  | Replace Nested Conditional with Guard Clauses | 10 |
  | Substitute Algorithm | 10 |

  Le siguen Extract Variable, Consolidate Duplicate Conditional Fragments, Remove Dead Code, Slide Statements y Split Variable. **No usó Move ni Inline Function**, igual que en PySnooper.
- **API pública:** verificada automáticamente con `ast`; ningún nombre público usado por otros módulos o por los tests cambió de nombre ni de firma.
  - Únicos cambios detectados: en `prompt` se eliminaron los imports `starmap` (2/3) e `Iterator` (1/3), que dejaron de usarse. No rompen nada.
  - **Infracción menor:** en `extensions_run3` el modelo creó una constante **pública** nueva (`DEFAULT_DATETIME_FORMAT`). No rompe nada, pero amplía la API, contra el espíritu de "no agregues funcionalidades".
- **Idioma:** todos los identificadores nuevos están en inglés, pero en 4 de 51 corridas (`cli_run3` y las 3 de `environment`) el modelo escribió comentarios en español, probablemente por efecto del prompt en español. En PySnooper fueron 2 de 15.

## 6. Fragmentos K1–K5 y qué hizo cada herramienta

Son los bloques que Rope intentó refactorizar y que el LLM también tocó por iniciativa propia. Líneas referidas a los archivos originales.

| ID | Fragmento | Archivo:líneas | Rope | LLM run1 | LLM run2 | LLM run3 |
|---|---|---|---|---|---|---|
| K1 | Detección del carácter de fin de línea | `generate.py:241–252` | ✅ prueba 07 (`_detect_newline`) | `_determine_newline` | `_get_newline` | `_determine_newline` |
| K2 | Armado del contexto en modo `replay` | `main.py:111–133` | ❌ prueba 08 (333/46) | `_prompting_context_for_replay` | `_variables_missing_from_replay` | `_context_missing_from_replay` |
| K3 | Copia de un archivo sin renderizar (termina en `continue`) | `generate.py:437–446` | ⛔ prueba 09 (rechazada) | `_copy_file_without_render` | ídem | ídem |
| K4 | Bucle de copia de directorios sin renderizar | `generate.py:406–417` | ✅ prueba 10 (`_copy_dirs_without_rendering`) | `_copy_dirs_without_render` | `_copy_dir_without_render` | `_copy_dir_without_render` |
| K5 | Expansión de rutas (`_expand_path`) | `config.py:36–39` y `:81–84` | ❌ prueba 11 (Inline, 378/1) | conserva `_expand_path` y la aplica en un bucle (`_expand_config_paths`) | ídem (`_expand_path_settings`) | ídem (`_expand_config_paths`) |

En las 3 corridas, **el LLM extrajo K1–K4 por iniciativa propia**, sin que el prompt los mencionara, y los 379 tests pasan.

**Por qué el LLM logra K2 y K3 y Rope no:**
- **K3:** Rope intenta extraer el bloque **con** el `continue`, cuyo salto apunta a un bucle externo al bloque, y lo rechaza. El LLM extrae solo el cuerpo útil (calcular la ruta y copiar) y **deja el `continue` en el bucle**: elige un límite de extracción distinto que hace posible la refactorización.
- **K2:** Rope extrae el `if/else` completo, lo que le obliga a devolver varios valores, y se equivoca dos veces (variables de la comprensión y lectura adelantada de una variable condicional). El LLM **deja el `if replay:` en el llamador** y extrae solo el cálculo de las variables pendientes, que devuelve **un único valor** y se invoca solo dentro de la rama donde `context_from_replayfile` existe. Las variables de la comprensión quedan encerradas en la función nueva.
- **K5:** no es comparable en sentido estricto: el LLM no hizo un Inline, sino lo contrario, **reutilizó** la función. Pero muestra que no eliminó la lógica de expansión que Rope rompió.

En PySnooper, la clave era que el LLM **eliminaba primero** los `.format(**locals())`. En Cookiecutter, la clave es que **elige dónde cortar** el bloque para que la extracción tenga una sola salida y no arrastre flujo de control. Es la misma idea en ambos proyectos: Rope aplica una transformación mecánica sobre el rango que se le da, y el LLM adapta la refactorización a las dependencias del código.

## 7. Alcance real de la comparación (importante para no sobreafirmar)

| Refactorizaciones de Rope | ¿Comparables con el LLM? | Motivo |
|---|---|---|
| 07, 08, 09, 10 (Extract Method) | ✅ Sí | El LLM extrajo los mismos bloques (K1–K4). Resultado: **LLM 4/4 (12/12 corridas) frente a Rope 2/4 (+1 rechazada)**. En PySnooper fue LLM 4/4 frente a Rope 1/4 |
| 11 (Inline de función privada) | ⚠️ Parcial | El LLM podía hacerlo (la función es privada) y decidió conservarla (K5) |
| 04 (Rename de método privado) | ⚠️ Parcial | El LLM podía hacerlo y decidió no hacerlo: conservó `_read_extensions` en las 3 corridas |
| 02, 03, 05, 06 (Rename público) | ❌ No | El prompt prohíbe cambiar la API pública |
| 13, 14, 15 (Rename de funciones referenciadas por string) | ❌ No | Son funciones públicas, y además el LLM no ve los tests. El experimento **no permite afirmar** que el LLM detectaría esas referencias |
| 12 (Move entre archivos) | ❌ No | El prompt prohíbe tocar otros archivos |

Conclusión: igual que en PySnooper, con el prompt v1 la comparación directa con Rope **solo es válida para Extract Method**. Sobre Rename, Inline y Move no se puede afirmar nada.

## 8. Discrepancia de diseño pendiente de resolver

Es la misma que en PySnooper. Si la tesis describe "una llamada al modelo por fragmento", eso **no coincide con lo ejecutado**: se hizo **una llamada por módulo completo**. K1–K5 aparecen dentro de las respuestas de las llamadas de `generate`, `main` y `config`. Hay que mantener la decisión que se tome para PySnooper:
1. **Redactar la tesis según lo ejecutado:** llamada por módulo, en ambos proyectos.
2. **Ejecutar un experimento por fragmento:** en ambos proyectos, para que sigan siendo comparables.

## 9. Limitaciones (para la sección de amenazas a la validez)

1. **Los tests son el único oráculo:** "preserva" significa "pasa los 379 tests", no equivalencia demostrada. Hay ramas que no se ejercitan en este entorno: las de Windows (4 tests omitidos) y algunos errores de red en `vcs`.
2. **Diffs grandes** (más de 400 líneas cambiadas en `generate`): son más difíciles de revisar y de aislar si algo falla.
3. **No hay determinismo**, y no se puede fijar la temperatura en este modelo.
4. **Pocas repeticiones** (3 por módulo): 51/51 no descarta una tasa de error baja.
5. **Un solo modelo y un solo prompt:** no se puede generalizar a "los LLM".
6. **Posible sesgo del prompt:** el formato de salida pone como ejemplo "Extract Method, Rename Variable", que son justamente los dos tipos más usados por el modelo (igual que en PySnooper).
7. **La lista de refactorizaciones la escribe el propio modelo.** Se verificó contra las funciones nuevas de cada diff y con `ast` para la API, no de forma exhaustiva. El conteo de tipos es aproximado.
8. **Comparación no simétrica:** Rope ejecutó operaciones elegidas por una persona (incluidos casos límite) y el LLM eligió las suyas.
9. **`zipfile` quedó fuera:** los resultados del LLM cubren 2681 de 2806 líneas (96 %).
10. **El LLM no veía los tests,** así que no se puede comparar con los fallos 13–15 de Rope.

## 10. Incidencias del proceso (bitácora)

| Incidencia | Efecto | Solución |
|---|---|---|
| Cookiecutter requiere Python ≥ 3.10 y el sistema tiene 3.9.6 | No se podía correr la suite | Se instaló `uv` y se creó `.venv` con Python 3.12 desde `uv.lock` |
| `uv sync` instala Cookiecutter en modo editable apuntando al repositorio original | Los tests podían importar el código original en vez de la copia refactorizada | `PYTHONPATH=<copia>` en cada corrida; el script de Rope verifica la ruta importada |
| `pyproject.toml` agrega `--cov` a pytest | Corridas más lentas y salida con ruido | `pytest -o addopts=` |
| Rope abortaba con `ModuleSyntaxError` por los archivos `.py` que son plantillas Jinja | Rope no podía analizar el proyecto | `Project(..., ignore_syntax_errors=True)` |
| **Falso fallo** en la prueba de Rope 03: la carpeta de trabajo se llamaba `03_rename_funcion_tests` y 2 tests de `test_hooks.py` verifican que `'tests'` no esté en la ruta actual | 2 tests fallaban sin relación con Rope | Se renombró el id a `03_rename_funcion_importada`; quedó documentado en el README |
| El Mac entra en reposo al cerrar la tapa ("Clamshell Sleep") y corta la conexión con la API | La primera ejecución se cayó en la corrida 15 (`ReadTimeout`); después una llamada quedó colgada | Reintentos automáticos ante errores de red, opción `--reanudar` (continúa sin repetir ni pagar corridas hechas) y `caffeinate -dimsu` |
| El plan inicial era de 54 corridas (18 módulos × 3) | El autor lo consideró excesivo | Decisión del autor: limitar a los módulos relevantes para Rope. Como ya había 50 hechas, solo quedó fuera `zipfile` |

## 11. Archivos de evidencia

- **LLM, ejecución principal:** `llm_pruebas/resultados/20261015_181126/` → `resumen.md`, `resumen.json` y, por corrida, `<modulo>_run<n>_respuesta.md`, `.py`, `.diff` y `_pytest.txt`.
- **LLM, piloto:** `llm_pruebas/resultados/20261015_181046/`.
- **Rope:** `rope_pruebas/resultados/` (`resumen.md`, `resumen.json`, `01_analisis_estatico.md` y, por refactorización, `.diff` y `_pytest.txt`, o `_error.txt` si Rope la rechazó).
- **Informes completos:** `rope_pruebas/README.md` y `llm_pruebas/README.md`.
- **Versionado:** todo está en la rama git `tesis/pruebas-rope-llm` (commits `b2d6bae` Rope y `4045cb9` LLM). Las copias temporales `_trabajo/` están excluidas.

## 12. Resumen comparativo de los dos proyectos

| | PySnooper | Cookiecutter |
|---|---|---|
| Tamaño | 964 líneas, 5 módulos, 83 tests | 2806 líneas, 18 módulos, 379 tests |
| Rope: casos equivalentes (02–12) que preservan | 8/11 (73 %) | 8/11 (73 %) |
| Rope: Extract Method que preservan | 1/4 | 2/4 (+1 rechazada) |
| Rope: causa principal de los fallos | `.format(**locals())` en el código | flujo de datos (comprensiones, ramas, parámetro reasignado) y referencias en strings en los tests |
| Rope: falsos positivos de `find_errors` | 31/31 | 39/39 |
| LLM: corridas que preservan | 15/15 | 51/51 |
| LLM: Extract Method sobre los mismos bloques que Rope | 4/4 (12/12 corridas) | 4/4 (12/12 corridas) |
| LLM: cómo evita los fallos de Rope | elimina primero `**locals()` | elige el límite del bloque (una sola salida, sin flujo de control) |
| LLM: infracción menor del prompt | renombra un parámetro posicional | agrega una constante pública |
| LLM: costo | US$ 2.55 | US$ 6.80 |
