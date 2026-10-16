# Análisis estático con Rope 1.15.0

## find_errors (rope.contrib.finderrors)

| Módulo | Errores reportados |
|---|---|
| `cookiecutter/__init__.py` | 0 |
| `cookiecutter/__main__.py` | 0 |
| `cookiecutter/cli.py` | 3 |
| `cookiecutter/config.py` | 0 |
| `cookiecutter/environment.py` | 2 |
| `cookiecutter/exceptions.py` | 0 |
| `cookiecutter/extensions.py` | 0 |
| `cookiecutter/find.py` | 0 |
| `cookiecutter/generate.py` | 5 |
| `cookiecutter/hooks.py` | 2 |
| `cookiecutter/log.py` | 0 |
| `cookiecutter/main.py` | 5 |
| `cookiecutter/prompt.py` | 18 |
| `cookiecutter/replay.py` | 0 |
| `cookiecutter/repository.py` | 3 |
| `cookiecutter/utils.py` | 0 |
| `cookiecutter/vcs.py` | 1 |
| `cookiecutter/zipfile.py` | 0 |

- `cookiecutter/cli.py:41` — Unresolved variable __file__
- `cookiecutter/cli.py:59` — Unresolved variable s
- `cookiecutter/cli.py:76` — Defined later folder
- `cookiecutter/environment.py:28` — Defined later context
- `cookiecutter/environment.py:56` — Unresolved variable ext
- `cookiecutter/generate.py:68` — Unresolved variable in_dictionary_variable
- `cookiecutter/generate.py:76` — Unresolved variable in_dictionary_variable
- `cookiecutter/generate.py:251` — Unresolved attribute newlines
- `cookiecutter/generate.py:251` — Unresolved attribute newlines
- `cookiecutter/generate.py:251` — Unresolved attribute newlines
- `cookiecutter/hooks.py:70` — Defined later hook_file
- `cookiecutter/hooks.py:125` — Unresolved attribute write
- `cookiecutter/main.py:119` — Defined later k
- `cookiecutter/main.py:119` — Defined later v
- `cookiecutter/main.py:137` — Defined later k
- `cookiecutter/main.py:137` — Defined later v
- `cookiecutter/main.py:137` — Defined later k
- `cookiecutter/prompt.py:38` — Unresolved attribute ask
- `cookiecutter/prompt.py:80` — Unresolved attribute ask
- `cookiecutter/prompt.py:88` — Unresolved attribute ask
- `cookiecutter/prompt.py:103` — Defined later i
- `cookiecutter/prompt.py:103` — Defined later value
- `cookiecutter/prompt.py:121` — Defined later p
- `cookiecutter/prompt.py:120` — Defined later i
- `cookiecutter/prompt.py:120` — Defined later p
- `cookiecutter/prompt.py:122` — Defined later i
- `cookiecutter/prompt.py:122` — Defined later p
- `cookiecutter/prompt.py:134` — Unresolved attribute ask
- `cookiecutter/prompt.py:189` — Unresolved attribute ask
- `cookiecutter/prompt.py:224` — Unresolved variable k
- `cookiecutter/prompt.py:225` — Unresolved variable v
- `cookiecutter/prompt.py:230` — Unresolved variable v
- `cookiecutter/prompt.py:275` — Defined later raw
- `cookiecutter/prompt.py:301` — Defined later k
- `cookiecutter/prompt.py:301` — Defined later k
- `cookiecutter/repository.py:24` — Unresolved attribute VERBOSE
- `cookiecutter/repository.py:30` — Unresolved attribute match
- `cookiecutter/repository.py:128` — Defined later s
- `cookiecutter/vcs.py:130` — Defined later error

## find_occurrences (rope.contrib.findit)

### `create_env_with_context` (10 ocurrencias)

- `cookiecutter/generate.py:30`
- `cookiecutter/generate.py:351`
- `tests/test_find.py:10`
- `tests/test_find.py:22`
- `cookiecutter/utils.py:102`
- `cookiecutter/hooks.py:19`
- `cookiecutter/hooks.py:122`
- `cookiecutter/prompt.py:19`
- `cookiecutter/prompt.py:293`
- `cookiecutter/prompt.py:377`

### `expand_abbreviations` (7 ocurrencias)

- `tests/repository/test_abbreviation_expansion.py:6`
- `tests/repository/test_abbreviation_expansion.py:46`
- `tests/repository/test_abbreviation_expansion.py:53`
- `tests/repository/test_is_repo_url.py:6`
- `tests/repository/test_is_repo_url.py:75`
- `cookiecutter/repository.py:38`
- `cookiecutter/repository.py:101`

### `_read_extensions` (2 ocurrencias)

- `cookiecutter/environment.py:37`
- `cookiecutter/environment.py:45`

### `CookiecutterException` (18 ocurrencias)

- `cookiecutter/exceptions.py:11`
- `cookiecutter/exceptions.py:19`
- `cookiecutter/exceptions.py:28`
- `cookiecutter/exceptions.py:39`
- `cookiecutter/exceptions.py:50`
- `cookiecutter/exceptions.py:59`
- `cookiecutter/exceptions.py:68`
- `cookiecutter/exceptions.py:76`
- `cookiecutter/exceptions.py:84`
- `cookiecutter/exceptions.py:92`
- `cookiecutter/exceptions.py:100`
- `cookiecutter/exceptions.py:108`
- `cookiecutter/exceptions.py:117`
- `cookiecutter/exceptions.py:125`
- `cookiecutter/exceptions.py:150`
- `cookiecutter/exceptions.py:158`
- `cookiecutter/exceptions.py:166`
- `cookiecutter/exceptions.py:174`

### `is_vcs_installed` (3 ocurrencias)

- `tests/vcs/test_is_vcs_installed.py:15`
- `cookiecutter/vcs.py:54`
- `cookiecutter/vcs.py:87`

## find_definition (rope.contrib.findit)

Desde `cookiecutter/generate.py` (`create_env_with_context(context)`) Rope resuelve la definición en `cookiecutter/utils.py:102`.
