# Resumen de pruebas con Rope (Cookiecutter)

- Python: `3.12.15`
- Rope: `1.15.0`
- Fecha: 2026-10-15 18:13

## Línea base

379 passed, 0 failed, 4 skipped, 0 errors

## Refactorizaciones

| # | Tipo | Descripción | Rope | Tiempo (s) | Tests (passed/failed/errors) | Veredicto |
|---|---|---|---|---|---|---|
| 02_rename_funcion | Rename | utils.create_env_with_context -> create_jinja_env (usada en 3 módulos y en tests) | aplicada | 0.334 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 03_rename_funcion_importada | Rename | repository.expand_abbreviations -> expand_template_abbreviations (también importada por los tests) | aplicada | 0.069 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 04_rename_metodo | Rename | ExtensionLoaderMixin._read_extensions -> _extensions_from_context | aplicada | 0.039 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 05_rename_clase | Rename | exceptions.CookiecutterException -> CookiecutterError (clase base de 17 subclases) | aplicada | 0.244 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 06_rename_parametro | Rename | parámetro cwd de hooks.run_script -> working_dir | aplicada | 0.063 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 07_extract_newline | Extract Method | bloque de detección de fin de línea de generate_file -> _detect_newline | aplicada | 0.041 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 08_extract_contexto | Extract Method | bloque if/else que arma el contexto en main.cookiecutter -> _build_context (2 valores de salida) | aplicada | 0.113 | 333 / 46 / 0 | **ROMPE TESTS** |
| 09_extract_con_continue | Extract Method | bloque que termina en `continue` dentro del for de generate_files -> _copy_file_without_rendering (caso límite) | error: RefactoringError: A break/continue without having a matching for/while loop. | 0.003 | — | **RECHAZADA POR ROPE** |
| 10_extract_bucle | Extract Method | bucle de copia de directorios de generate_files -> _copy_dirs_without_rendering | aplicada | 0.338 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 11_inline_funcion | Inline | inline de config._expand_path en get_config (2 llamadas) | aplicada | 0.125 | 378 / 1 / 0 | **ROMPE TESTS** |
| 12_move_funcion | Move | mover utils.make_executable a hooks | aplicada | 0.391 | 379 / 0 / 0 | **COMPORTAMIENTO PRESERVADO** |
| 13_rename_parcheada | Rename | vcs.is_vcs_installed -> is_vcs_available (los tests la parchean con mocker.patch('cookiecutter.vcs.is_vcs_installed')) | aplicada | 0.094 | 370 / 9 / 0 | **ROMPE TESTS** |
| 14_rename_parcheada_docs | Rename | igual que 13 pero con docs=True (renombra también en strings y comentarios) | aplicada | 0.093 | 370 / 9 / 0 | **ROMPE TESTS** |
| 15_rename_espiada | Rename | replay.get_file_name -> get_replay_file_path (los tests usan mocker.spy(replay, 'get_file_name')) | aplicada | 0.375 | 377 / 2 / 0 | **ROMPE TESTS** |
