```python
"""Helper functions for working with version control systems."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from shutil import which
from typing import TYPE_CHECKING

from cookiecutter.exceptions import (
    RepositoryCloneFailed,
    RepositoryNotFound,
    UnknownRepoType,
    VCSNotInstalled,
)
from cookiecutter.prompt import prompt_and_delete
from cookiecutter.utils import make_sure_path_exists

if TYPE_CHECKING:
    from typing import Literal

logger = logging.getLogger(__name__)


BRANCH_ERRORS = [
    'error: pathspec',
    'unknown revision',
]

_SUPPORTED_REPO_TYPES = ('git', 'hg')


def identify_repo(repo_url: str) -> tuple[Literal["git", "hg"], str]:
    """Determine if `repo_url` should be treated as a URL to a git or hg repo.

    Repos can be identified by prepending "hg+" or "git+" to the repo URL.

    :param repo_url: Repo URL of unknown type.
    :returns: ('git', repo_url) or ('hg', repo_url).
    :raises UnknownRepoType: If the repo type cannot be determined.
    """
    repo_url_values = repo_url.split('+')
    if len(repo_url_values) == 2:
        repo_type, url_without_prefix = repo_url_values
        if repo_type in _SUPPORTED_REPO_TYPES:
            return repo_type, url_without_prefix  # type: ignore[return-value]
        raise UnknownRepoType
    if 'git' in repo_url:
        return 'git', repo_url
    if 'bitbucket' in repo_url:
        return 'hg', repo_url
    raise UnknownRepoType


def is_vcs_installed(repo_type: str) -> bool:
    """
    Check if the version control system for a repo type is installed.

    :param repo_type:
    """
    return bool(which(repo_type))


def _get_repo_dir(repo_type: str, repo_url: str, clone_to_dir: Path) -> str:
    """Return the local directory where the repository will be cloned.

    :param repo_type: The VCS of the repository ('git' or 'hg').
    :param repo_url: Repo URL, without trailing slashes.
    :param clone_to_dir: The directory to clone to.
    """
    repo_name = os.path.split(repo_url)[1]
    if repo_type == 'git':
        repo_name = repo_name.split(':')[-1].rsplit('.git')[0]
    return os.path.normpath(os.path.join(clone_to_dir, repo_name))


def _build_checkout_command(repo_type: str, checkout: str) -> list[str]:
    """Return the VCS command used to checkout the given branch, tag or commit."""
    if repo_type == 'hg':
        # Avoid Mercurial "--config" and "--debugger" injection vulnerability
        return [repo_type, 'checkout', '--', checkout]
    return [repo_type, 'checkout', checkout]


def _run_vcs_command(command: list[str], cwd: Path | str) -> None:
    """Run a VCS command in `cwd`, capturing stderr together with stdout."""
    subprocess.check_output(command, cwd=cwd, stderr=subprocess.STDOUT)


def _clone_and_checkout(
    repo_type: str,
    repo_url: str,
    checkout: str | None,
    clone_to_dir: Path,
    repo_dir: str,
) -> None:
    """Clone the repository and, if requested, checkout the given reference."""
    _run_vcs_command([repo_type, 'clone', repo_url], cwd=clone_to_dir)
    if checkout is not None:
        _run_vcs_command(_build_checkout_command(repo_type, checkout), cwd=repo_dir)


def _raise_for_known_clone_error(
    output: str,
    repo_url: str,
    checkout: str | None,
    clone_error: subprocess.CalledProcessError,
) -> None:
    """Translate recognizable VCS failures into Cookiecutter exceptions.

    Returns normally if the error output does not match any known failure.
    """
    if 'not found' in output.lower():
        msg = f'The repository {repo_url} could not be found, have you made a typo?'
        raise RepositoryNotFound(msg) from clone_error
    if any(error in output for error in BRANCH_ERRORS):
        msg = (
            f'The {checkout} branch of repository '
            f'{repo_url} could not found, have you made a typo?'
        )
        raise RepositoryCloneFailed(msg) from clone_error


def clone(
    repo_url: str,
    checkout: str | None = None,
    clone_to_dir: Path | str = ".",
    no_input: bool = False,
) -> str:
    """Clone a repo to the current directory.

    :param repo_url: Repo URL of unknown type.
    :param checkout: The branch, tag or commit ID to checkout after clone.
    :param clone_to_dir: The directory to clone to.
                         Defaults to the current directory.
    :param no_input: Do not prompt for user input and eventually force a refresh of
        cached resources.
    :returns: str with path to the new directory of the repository.
    """
    # Ensure that clone_to_dir exists
    clone_to_dir = Path(clone_to_dir).expanduser()
    make_sure_path_exists(clone_to_dir)

    repo_type, repo_url = identify_repo(repo_url)
    if not is_vcs_installed(repo_type):
        msg = f"'{repo_type}' is not installed."
        raise VCSNotInstalled(msg)

    repo_url = repo_url.rstrip('/')
    repo_dir = _get_repo_dir(repo_type, repo_url, clone_to_dir)
    logger.debug('repo_dir is %s', repo_dir)

    if os.path.isdir(repo_dir):
        should_clone = prompt_and_delete(repo_dir, no_input=no_input)
    else:
        should_clone = True

    if not should_clone:
        return repo_dir

    try:
        _clone_and_checkout(repo_type, repo_url, checkout, clone_to_dir, repo_dir)
    except subprocess.CalledProcessError as clone_error:
        output = clone_error.output.decode('utf-8')
        _raise_for_known_clone_error(output, repo_url, checkout, clone_error)
        logger.exception('git clone failed with error: %s', output)
        raise

    return repo_dir
```

## Refactorizaciones aplicadas

- **Extract Function** → `_get_repo_dir`
  - Cálculo del directorio destino del clon. El original repetía `os.path.normpath(os.path.join(clone_to_dir, repo_name))` en dos ramas `if`: una para git y otra para hg.
  - Ahora la única diferencia, que es el recorte del nombre en git, queda aislada, y la construcción de la ruta se hace una sola vez (**Consolidate Duplicate Conditional Fragments**).
  - Se conserva exactamente la expresión `split(':')[-1].rsplit('.git')[0]`, con su semántica peculiar.
  - Como `identify_repo` solo devuelve `'git'` o `'hg'`, el resultado es idéntico en todos los casos alcanzables.
  - Única diferencia: con un tipo distinto, el original fallaba con `UnboundLocalError`. Ese caso no puede ocurrir desde `clone`.

- **Extract Function** → `_build_checkout_command`
  - Construcción del comando `checkout`. Antes se creaba una lista y se mutaba con `insert(0, "--")`. Ahora se devuelven directamente las dos variantes de la lista, con contenido idéntico.
  - El comentario sobre la vulnerabilidad de inyección en Mercurial queda junto a la rama que la mitiga.

- **Extract Function** → `_run_vcs_command`
  - Las dos llamadas a `subprocess.check_output(..., cwd=..., stderr=subprocess.STDOUT)` eran duplicadas.
  - Se siguen pasando `cwd` y `stderr` como argumentos con nombre, con los mismos valores. Así los tests que hacen *mock* de `subprocess.check_output` ven exactamente las mismas llamadas.

- **Extract Function** → `_clone_and_checkout`
  - Agrupa la secuencia clonar + checkout opcional que estaba anidada dentro del `try`. El bloque `try` queda reducido a una línea que expresa la intención.

- **Extract Function** → `_raise_for_known_clone_error`
  - Traducción de los errores de `CalledProcessError` a `RepositoryNotFound` / `RepositoryCloneFailed`, con los mismos mensajes y el mismo encadenamiento `from clone_error`.
  - El `logger.exception(...)` y el `raise` final se mantienen dentro del bloque `except` de `clone`. Así se re-lanza la excepción original y el log conserva la información de la traza.

- **Rename Variable** → `clone` → `should_clone` (variable local dentro de `clone()`)
  - La variable local tenía el mismo nombre que la función que la contiene. Eso la ocultaba y confundía al leer. El nuevo nombre expresa que es una decisión booleana.

- **Replace Nested Conditional with Guard Clauses** → `clone()`
  - El bloque `if clone:` que envolvía todo el proceso se sustituye por un retorno anticipado `if not should_clone: return repo_dir`. Esto reduce un nivel de anidamiento.

- **Split Variable / Rename Variable** → `identify_repo`
  - Se desempaquetan los dos elementos en `repo_type, url_without_prefix` en lugar de acceder por índice (`repo_url_values[0]`, `repo_url_values[1]`). Solo ocurre cuando `len == 2`, así que el desempaquetado es seguro.
  - La lógica de casos con más de un `+` (que caen en las comprobaciones de `'git'` / `'bitbucket'`) no cambia.

- **Replace Magic Literal** → `_SUPPORTED_REPO_TYPES` en `identify_repo`
  - La lista literal `["git", "hg"]` pasa a una constante privada con nombre descriptivo. La comprobación de pertenencia es equivalente.

- **Llamada de logging con formato diferido** → `logger.debug` en `clone()`
  - Se sustituye la f-string por el formato `%s` del módulo `logging`. El mensaje final (`record.getMessage()`) es idéntico, pero el formateo solo se realiza si el nivel DEBUG está activo. Además, es coherente con el resto de llamadas de log del módulo.

- **Reorganización de imports y docstring** → bloque `TYPE_CHECKING`, docstring de `identify_repo`
  - El bloque `if TYPE_CHECKING:` se movió detrás de todos los imports, en lugar de quedar intercalado entre los de la biblioteca estándar y los del proyecto.
  - Se corrigió el docstring de `identify_repo`, que afirmaba que podía devolver `None`. En realidad lanza `UnknownRepoType`.
  - Ninguno de los dos cambios afecta al comportamiento.

Se mantienen sin cambios los nombres y firmas públicas (`BRANCH_ERRORS`, `identify_repo`, `is_vcs_installed`, `clone`). Todas las dependencias siguen resolviéndose como globales del módulo (`subprocess`, `is_vcs_installed`, `prompt_and_delete`), por lo que los `mocker.patch('cookiecutter.vcs....')` existentes siguen funcionando igual.