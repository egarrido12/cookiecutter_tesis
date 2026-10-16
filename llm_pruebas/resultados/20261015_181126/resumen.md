# Resumen de pruebas con LLM (prompt general) — Cookiecutter

- Python: `3.12.15`
- SDK anthropic: `1.15.0`
- Modelo solicitado: `claude-opus-5-5` (effort `high`)
- Prompt: `prompt_v1.md`
- Corridas por módulo: 3
- Fecha: 2026-10-15 23:11
- Costo total estimado: US$ 6.80

## Línea base

379 passed, 0 failed, 4 skipped, 0 errors

## Corridas

| Corrida | Modelo | +/− líneas | Tests (passed/failed/errors) | Veredicto | Tipo de fallo | Cambios API pública | Tiempo (s) | Costo (US$) |
|---|---|---|---|---|---|---|---|---|
| __init___run1 | claude-opus-5-5 | +0 / −0 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 18.0 | 0.0336 |
| __init___run2 | claude-opus-5-5 | +0 / −0 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 27.0 | 0.0301 |
| __init___run3 | claude-opus-5-5 | +0 / −0 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 15.3 | 0.0356 |
| __main___run1 | claude-opus-5-5 | +0 / −0 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 12.0 | 0.028 |
| __main___run2 | claude-opus-5-5 | +0 / −0 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 13.8 | 0.0306 |
| __main___run3 | claude-opus-5-5 | +0 / −0 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 13.3 | 0.0319 |
| cli_run1 | claude-opus-5-5 | +78 / −46 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 59.9 | 0.1616 |
| cli_run2 | claude-opus-5-5 | +85 / −55 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 55.0 | 0.1496 |
| cli_run3 | claude-opus-5-5 | +73 / −44 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 46.8 | 0.1527 |
| config_run1 | claude-opus-5-5 | +60 / −35 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 42.3 | 0.1079 |
| config_run2 | claude-opus-5-5 | +79 / −37 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 57.9 | 0.1495 |
| config_run3 | claude-opus-5-5 | +61 / −35 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 39.6 | 0.1053 |
| environment_run1 | claude-opus-5-5 | +14 / −12 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 26.1 | 0.0653 |
| environment_run2 | claude-opus-5-5 | +15 / −13 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 27.0 | 0.0669 |
| environment_run3 | claude-opus-5-5 | +17 / −13 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 29.8 | 0.2428 |
| exceptions_run1 | claude-opus-5-5 | +131 / −102 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 42.7 | 0.2701 |
| exceptions_run2 | claude-opus-5-5 | +137 / −116 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 42.8 | 0.1059 |
| exceptions_run3 | claude-opus-5-5 | +138 / −116 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 38.5 | 0.097 |
| extensions_run1 | claude-opus-5-5 | +48 / −33 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 44.5 | 0.1175 |
| extensions_run2 | claude-opus-5-5 | +66 / −45 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 55.8 | 0.1406 |
| extensions_run3 | claude-opus-5-5 | +115 / −92 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 55.3 | 0.1435 |
| find_run1 | claude-opus-5-5 | +31 / −13 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 22.3 | 0.059 |
| find_run2 | claude-opus-5-5 | +28 / −13 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 17.7 | 0.0466 |
| find_run3 | claude-opus-5-5 | +33 / −13 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 23.0 | 0.0586 |
| generate_run1 | claude-opus-5-5 | +262 / −165 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 107.8 | 0.2963 |
| generate_run2 | claude-opus-5-5 | +283 / −171 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 106.9 | 0.2952 |
| generate_run3 | claude-opus-5-5 | +292 / −178 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 109.0 | 0.2992 |
| hooks_run1 | claude-opus-5-5 | +56 / −43 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 49.6 | 0.1296 |
| hooks_run2 | claude-opus-5-5 | +65 / −44 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 55.8 | 0.1467 |
| hooks_run3 | claude-opus-5-5 | +56 / −38 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 52.8 | 0.1401 |
| log_run1 | claude-opus-5-5 | +23 / −17 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 25.5 | 0.0651 |
| log_run2 | claude-opus-5-5 | +22 / −18 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 25.3 | 0.0638 |
| log_run3 | claude-opus-5-5 | +30 / −18 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 24.9 | 0.0663 |
| main_run1 | claude-opus-5-5 | +128 / −56 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 84.0 | 0.2201 |
| main_run2 | claude-opus-5-5 | +106 / −56 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 78.3 | 0.2066 |
| main_run3 | claude-opus-5-5 | +114 / −54 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 93.5 | 0.242 |
| prompt_run1 | claude-opus-5-5 | +146 / −112 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 109.7 | 0.2861 |
| prompt_run2 | claude-opus-5-5 | +166 / −128 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | eliminado import Iterator; eliminado import starmap | 117.9 | 0.3083 |
| prompt_run3 | claude-opus-5-5 | +190 / −142 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | eliminado import starmap | 167.4 | 0.4287 |
| replay_run1 | claude-opus-5-5 | +19 / −13 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 16.8 | 0.0453 |
| replay_run2 | claude-opus-5-5 | +40 / −15 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 23.7 | 0.0638 |
| replay_run3 | claude-opus-5-5 | +15 / −9 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 17.8 | 0.0466 |
| repository_run1 | claude-opus-5-5 | +61 / −33 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 48.8 | 0.0926 |
| repository_run2 | claude-opus-5-5 | +56 / −28 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 38.2 | 0.0888 |
| repository_run3 | claude-opus-5-5 | +52 / −34 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 33.8 | 0.0878 |
| utils_run1 | claude-opus-5-5 | +19 / −14 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 33.6 | 0.0867 |
| utils_run2 | claude-opus-5-5 | +21 / −14 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 35.1 | 0.0895 |
| utils_run3 | claude-opus-5-5 | +17 / −13 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 47.7 | 0.1186 |
| vcs_run1 | claude-opus-5-5 | +90 / −52 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 51.8 | 0.1293 |
| vcs_run2 | claude-opus-5-5 | +84 / −52 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 66.5 | 0.1711 |
| vcs_run3 | claude-opus-5-5 | +94 / −55 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |  | — | 59.2 | 0.1536 |

## Determinismo

| Módulo | Corridas | Diffs distintos |
|---|---|---|
| __init__ | 3 | 1 |
| __main__ | 3 | 1 |
| cli | 3 | 3 |
| config | 3 | 3 |
| environment | 3 | 3 |
| exceptions | 3 | 3 |
| extensions | 3 | 3 |
| find | 3 | 3 |
| generate | 3 | 3 |
| hooks | 3 | 3 |
| log | 3 | 3 |
| main | 3 | 3 |
| prompt | 3 | 3 |
| replay | 3 | 3 |
| repository | 3 | 3 |
| utils | 3 | 3 |
| vcs | 3 | 3 |

Las refactorizaciones que el modelo dice haber aplicado están al final de cada `<corrida>_respuesta.md`.
