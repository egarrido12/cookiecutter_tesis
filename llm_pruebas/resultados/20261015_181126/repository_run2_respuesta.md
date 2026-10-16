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

_TEMPLATE_CONFIG_FILE = 'cookiecutter.json'


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
        os.path.join(repo_directory, _TEMPLATE_CONFIG_FILE)
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

    Zip archives are unpacked and repository URLs are cloned; any other
    template is treated as a local path, either as given or relative to
    ``clone_to_dir``.

    :return: A tuple containing the list of candidate directories, and a
        boolean describing whether the resulting directory should be cleaned
        up after the template has been instantiated.
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


def _build_repository_not_found_message(template: str, candidates: list[str]) -> str:
    """Build the error message listing every location that was searched."""
    searched_locations = '\n'.join(candidates)
    return (
        f'A valid repository for "{template}" could not be found in the following '
        f'locations:\n{searched_locations}'
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

    if directory:
        repository_candidates = [
            os.path.join(candidate, directory) for candidate in repository_candidates
        ]

    for repo_candidate in repository_candidates:
        if repository_has_cookiecutter_json(repo_candidate):
            return repo_candidate, cleanup

    msg = _build_repository_not_found_message(template, repository_candidates)
    raise RepositoryNotFound(msg)
```

## Refactorizaciones aplicadas

- **Extract Function** – `determine_repo_dir` → nueva función privada `_get_repository_candidates`.
  Motivo: el bloque `if/elif/else` que decide si hay que descomprimir, clonar o usar una ruta local era la parte más larga de `determine_repo_dir` y mezclaba esa decisión con la búsqueda posterior del `cookiecutter.json`. Ahora la función pública se lee como una secuencia de pasos de alto nivel: expandir, obtener candidatos, aplicar subdirectorio, buscar y fallar.
  Se conservan intactos:
  - las llamadas a `unzip` y `clone`, con los mismos argumentos por palabra clave;
  - la resolución de ambos nombres a través del módulo `cookiecutter.repository`, de modo que los *mocks* de los tests siguen funcionando;
  - el orden de evaluación.

- **Replace Nested Conditional with Guard Clauses** – dentro de `_get_repository_candidates`.
  Motivo: cada rama devuelve directamente su resultado (`return [...], cleanup`). Esto elimina las variables temporales `repository_candidates` y `cleanup`, que antes se asignaban en tres ramas distintas.

- **Extract Function** – construcción del mensaje de error → `_build_repository_not_found_message`.
  Motivo: separa el formateo del mensaje de la lógica de control.
  - Se sustituye `str.format` por un f-string, coherente con el resto del proyecto.
  - El `'\n'.join(...)` se calcula antes en la variable `searched_locations`. Así se mantiene la compatibilidad con Python < 3.12, que no admite barras invertidas dentro de las expresiones de un f-string.
  - El texto resultante es idéntico al original.

- **Replace Magic Literal with Symbolic Constant** – `'cookiecutter.json'` → constante privada `_TEMPLATE_CONFIG_FILE`, usada en `repository_has_cookiecutter_json`.
  Motivo: da nombre al significado del literal y centraliza su valor. Es privada para no ampliar la API pública del módulo.

- **Rename Variable** – `s` → `candidate` en la comprensión de lista que añade `directory`.
  Motivo: un nombre de una letra no comunicaba que cada elemento es un directorio candidato.

No se han modificado las firmas ni los nombres públicos: `REPO_REGEX`, `is_repo_url`, `is_zip_file`, `expand_abbreviations`, `repository_has_cookiecutter_json` y `determine_repo_dir`. Tampoco cambian los imports de `clone` y `unzip`, de los que dependen los tests al parchearlos.