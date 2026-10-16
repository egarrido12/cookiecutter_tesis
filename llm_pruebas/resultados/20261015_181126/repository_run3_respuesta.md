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
    context_file = os.path.join(repo_directory, _CONTEXT_FILE_NAME)
    return os.path.isdir(repo_directory) and os.path.isfile(context_file)


def _find_repository_candidates(
    template: str,
    clone_to_dir: Path | str,
    checkout: str | None,
    no_input: bool,
    password: str | None,
) -> tuple[list[str], bool]:
    """Return the candidate directories for ``template`` and the cleanup flag.

    Zip files are unpacked into a temporary directory (which must be cleaned
    up afterwards), repository URLs are cloned, and anything else is treated
    as a local path, either as given or relative to ``clone_to_dir``.
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


def _join_directory(candidates: list[str], directory: str | None) -> list[str]:
    """Append ``directory`` to every candidate path, if a directory was given."""
    if not directory:
        return candidates
    return [os.path.join(candidate, directory) for candidate in candidates]


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

    repository_candidates, cleanup = _find_repository_candidates(
        template, clone_to_dir, checkout, no_input, password
    )
    repository_candidates = _join_directory(repository_candidates, directory)

    for repo_candidate in repository_candidates:
        if repository_has_cookiecutter_json(repo_candidate):
            return repo_candidate, cleanup

    searched_locations = '\n'.join(repository_candidates)
    msg = (
        f'A valid repository for "{template}" could not be found in the following '
        f'locations:\n{searched_locations}'
    )
    raise RepositoryNotFound(msg)
```

## Refactorizaciones aplicadas

- **Extract Function** (`_find_repository_candidates`, extraída de `determine_repo_dir`)
  - Aísla la decisión de cómo obtener el repositorio según su tipo: zip, URL o ruta local.
  - Devuelve los candidatos y el indicador de limpieza.
  - Con esto, `determine_repo_dir` queda como una secuencia de pasos de alto nivel: expandir, obtener candidatos, aplicar subdirectorio, buscar y fallar.
  - `unzip` y `clone` se siguen invocando a través de los nombres globales del módulo y con los mismos argumentos por palabra clave. Así se mantiene la compatibilidad con los tests que hacen `mocker.patch('cookiecutter.repository.clone')` / `unzip`.

- **Replace Nested Conditional with Guard Clauses** (en `_find_repository_candidates`)
  - La cadena `if/elif/else`, que asignaba dos variables (`repository_candidates`, `cleanup`) en cada rama, pasa a `return` tempranos.
  - Así se elimina el estado mutable compartido entre ramas y el riesgo de olvidar asignar alguna de las variables.

- **Extract Function** (`_join_directory`, extraída de `determine_repo_dir`)
  - Encapsula la transformación opcional de los candidatos con el subdirectorio `directory`.
  - Elimina el `if` con reasignación dentro de la función principal.

- **Rename Variable** (`s` → `candidate`, en la comprensión de lista que une `directory`)
  - Un nombre de una sola letra no comunicaba que se trata de una ruta candidata.

- **Replace Magic Literal** (`'cookiecutter.json'` → constante privada `_CONTEXT_FILE_NAME`)
  - Da nombre al archivo que identifica una plantilla válida.
  - Es privada para no ampliar la API pública.

- **Inline Variable** (`repo_directory_exists` y `repo_config_exists` en `repository_has_cookiecutter_json`)
  - Se sustituyen por una única expresión booleana, apoyada en la variable explicativa `context_file`.
  - Ambas comprobaciones son consultas puras al sistema de archivos sin efectos secundarios, así que el resultado es idéntico.

- **Substitute Algorithm / Extract Variable** (mensaje de `RepositoryNotFound`)
  - El `str.format` se reemplaza por un f-string, coherente con el resto del paquete.
  - Antes se extrae `searched_locations`, porque una barra invertida (`'\n'.join`) dentro de una expresión de f-string no es válida en Python < 3.12.
  - El texto del mensaje resultante es exactamente el mismo.