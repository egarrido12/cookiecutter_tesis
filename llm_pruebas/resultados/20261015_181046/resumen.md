# Resumen de pruebas con LLM (prompt general) — Cookiecutter

- Python: `3.12.15`
- SDK anthropic: `1.15.0`
- Modelo solicitado: `claude-opus-5-5` (effort `high`)
- Prompt: `prompt_v1.md`
- Corridas por módulo: 1
- Fecha: 2026-10-15 18:11
- Costo total estimado: US$ 0.21

## Línea base

379 passed, 0 failed, 4 skipped, 0 errors

## Corridas

| Corrida | Modelo | +/− líneas | Tests (passed/failed/errors) | Veredicto | Tipo de fallo | Cambios API pública | Tiempo (s) | Costo (US$) |
|---|---|---|---|---|---|---|---|---|
| find_run1 | claude-opus-5-5 | +27 / −13 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 20.4 | 0.2133 |

## Determinismo

| Módulo | Corridas | Diffs distintos |
|---|---|---|
| find | 1 | 1 |

Las refactorizaciones que el modelo dice haber aplicado están al final de cada `<corrida>_respuesta.md`.
