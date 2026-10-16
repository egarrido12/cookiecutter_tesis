```python
"""Cookiecutter repository functions."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from cookiecutter.exceptions import RepositoryNotFound
from cookiecutter.vcs import clone
from cookiecutter.zipfile import unzip

if TYPE_CHECKING:
    from pathlib import Path

REPO_REGEX = re.compile(
    r"""
# something like git:// ssh:// file:// etc.
((((git|hg)\+)?(git|ssh|file|https?):(//)?)
 |                                      # or
 (\w+@[\w\.]+)                          # something like user@...
)
""",
    re.VERBOSE,
)

_CONTEXT_FILE_NAME = 'cookiecutter.json'


def is_repo_url(value: str) -> bool:
    """Return True if value is a repository URL."""
    return bool(REPO_REGEX.match(value))


def is_zip_file(value: str) -> bool:
    """Return True if value is a zip file."""
    return value.lower().endswith('.zip')


def expand_abbreviations(template: str, abbreviations: dict[str, str]) -> str:
    """Expand abbreviations in a template name.

    :param template: The project template name.
    :param abbreviations: Abbreviation definitions.
    """
    if template in abbreviations:
        return abbreviations[template]

    # Split on colon. If there is no colon, rest will be empty
    # and prefix will be the whole template
    prefix, _sep, rest = template.partition(':')
    if prefix in abbreviations:
        return abbreviations[prefix].format(rest)

    return template


def repository_has_cookiecutter_json(repo_directory: str) -> bool:
    """Determine if `repo_directory` contains a `cookiecutter.json` file.

    :param repo_directory: The candidate repository directory.
    :return: True if the `repo_directory` is valid, else False.
    """
    repo_directory_exists = os.path.isdir(repo_directory)
    repo_config_exists = os.path.isfile(
        os.path.join(repo_directory, _CONTEXT_FILE_NAME)
    )
    return repo_directory_exists and repo_config_exists


def _get_repository_candidates(
    template: str,
    clone_to_dir: Path | str,
    checkout: str | None,
    no_input: bool,
    password: str | None,
) -> tuple[list[str], bool]:
    """Obtain the candidate directories for an (already expanded) template.

    Zip archives are unpacked, repository URLs are cloned and anything else
    is treated as a local path, either as-is or relative to ``clone_to_dir``.

    :return: A tuple with the list of candidate directories and a boolean
        telling whether the resulting directory must be cleaned up afterwards.
    """
    if is_zip_file(template):
        unzipped_dir = unzip(
            zip_uri=template,
            is_url=is_repo_url(template),
            clone_to_dir=clone_to_dir,
            no_input=no_input,
            password=password,
        )
        return [unzipped_dir], True

    if is_repo_url(template):
        cloned_repo = clone(
            repo_url=template,
            checkout=checkout,
            clone_to_dir=clone_to_dir,
            no_input=no_input,
        )
        return [cloned_repo], False

    return [template, os.path.join(clone_to_dir, template)], False


def _join_subdirectory(candidates: list[str], directory: str | None) -> list[str]:
    """Point every candidate to ``directory`` inside it, if one is given."""
    if not directory:
        return candidates
    return [os.path.join(candidate, directory) for candidate in candidates]


def _repository_not_found_message(template: str, candidates: list[str]) -> str:
    """Build the error message used when no valid repository is found."""
    locations = '\n'.join(candidates)
    return (
        f'A valid repository for "{template}" could not be found in the following '
        f'locations:\n{locations}'
    )


def determine_repo_dir(
    template: str,
    abbreviations: dict[str, str],
    clone_to_dir: Path | str,
    checkout: str | None,
    no_input: bool,
    password: str | None = None,
    directory: str | None = None,
) -> tuple[str, bool]:
    """
    Locate the repository directory from a template reference.

    Applies repository abbreviations to the template reference.
    If the template refers to a repository URL, clone it.
    If the template is a path to a local repository, use it.

    :param template: A directory containing a project template directory,
        or a URL to a git repository.
    :param abbreviations: A dictionary of repository abbreviation
        definitions.
    :param clone_to_dir: The directory to clone the repository into.
    :param checkout: The branch, tag or commit ID to checkout after clone.
    :param no_input: Do not prompt for user input and eventually force a refresh of
        cached resources.
    :param password: The password to use when extracting the repository.
    :param directory: Directory within repo where cookiecutter.json lives.
    :return: A tuple containing the cookiecutter template directory, and
        a boolean describing whether that directory should be cleaned up
        after the template has been instantiated.
    :raises: `RepositoryNotFound` if a repository directory could not be found.
    """
    template = expand_abbreviations(template, abbreviations)

    repository_candidates, cleanup = _get_repository_candidates(
        template, clone_to_dir, checkout, no_input, password
    )
    repository_candidates = _join_subdirectory(repository_candidates, directory)

    for repo_candidate in repository_candidates:
        if repository_has_cookiecutter_json(repo_candidate):
            return repo_candidate, cleanup

    msg = _repository_not_found_message(template, repository_candidates)
    raise RepositoryNotFound(msg)
```

## Refactorizaciones aplicadas

- **Extract Function**: crea `_get_repository_candidates` a partir de `determine_repo_dir`.
  - Saca el bloque `if/elif/else` que decide si hay que descomprimir, clonar o usar una ruta local.
  - Motivo: `determine_repo_dir` mezclaba la obtención de candidatos con su filtrado y con la gestión del error. Ahora cada parte se lee por separado.
  - Las llamadas a `unzip` y `clone` siguen igual: mismos argumentos por nombre y referencias a nivel de módulo. Así los tests que hacen *mock* de `cookiecutter.repository.unzip` y `cookiecutter.repository.clone` siguen funcionando.

- **Replace Nested Conditional with Guard Clauses**: dentro de `_get_repository_candidates`, cada caso devuelve directamente `(candidatos, cleanup)`.
  - Motivo: se elimina la asignación repetida de `repository_candidates` y `cleanup` en las tres ramas.

- **Extract Function**: crea `_join_subdirectory` para la lógica que añade `directory` a cada candidato.
  - Motivo: el nombre explica la intención y `determine_repo_dir` queda como una secuencia lineal de pasos.

- **Rename Variable**: la variable de la *comprehension* pasa de `s` a `candidate` (en `_join_subdirectory`).
  - Motivo: `s` no comunicaba nada.

- **Extract Function**: crea `_repository_not_found_message` para construir el mensaje de `RepositoryNotFound`.
  - Motivo: separa el formateo del texto del flujo principal.

- **Substitute Algorithm**: dentro de `_repository_not_found_message`, `str.format` se sustituye por un f-string.
  - El `'\n'.join(...)` se calcula antes en la variable `locations`. Así no hay barras invertidas dentro de la expresión del f-string, lo que mantiene la compatibilidad con Python < 3.12.
  - El texto resultante es idéntico al original.

- **Replace Magic Literal with Symbolic Constant**: `'cookiecutter.json'` pasa a la constante privada `_CONTEXT_FILE_NAME`, usada en `repository_has_cookiecutter_json`.
  - Motivo: da nombre al significado del literal y evita repetirlo si se reutiliza en el módulo.

Las funciones públicas y la constante `REPO_REGEX` conservan sus nombres, firmas y comportamiento:

- `is_repo_url`
- `is_zip_file`
- `expand_abbreviations`
- `repository_has_cookiecutter_json`
- `determine_repo_dir`