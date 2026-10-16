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
    :raises: `UnknownRepoType` if the repo type cannot be determined.
    """
    url_parts = repo_url.split('+')
    if len(url_parts) == 2:
        repo_type, url_without_prefix = url_parts
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


def _ensure_vcs_installed(repo_type: str) -> None:
    """Raise `VCSNotInstalled` if the VCS for `repo_type` is not available."""
    if not is_vcs_installed(repo_type):
        msg = f"'{repo_type}' is not installed."
        raise VCSNotInstalled(msg)


def _build_repo_dir(repo_type: str, repo_url: str, clone_to_dir: Path) -> str:
    """Return the local directory where `repo_url` will be cloned.

    For git repositories, the ``user@host:`` prefix and the ``.git`` suffix
    are stripped from the repository name.

    :param repo_type: 'git' or 'hg', as returned by `identify_repo`.
    :param repo_url: Repo URL without trailing slashes.
    :param clone_to_dir: The directory to clone to.
    """
    repo_name = os.path.split(repo_url)[1]
    if repo_type == 'git':
        repo_name = repo_name.split(':')[-1].rsplit('.git')[0]
    return os.path.normpath(os.path.join(clone_to_dir, repo_name))


def _should_clone(repo_dir: str, no_input: bool) -> bool:
    """Decide whether the repository must be (re)cloned into `repo_dir`.

    If `repo_dir` already exists, ask the user whether it may be deleted.
    """
    if os.path.isdir(repo_dir):
        return prompt_and_delete(repo_dir, no_input=no_input)
    return True


def _run_clone(repo_type: str, repo_url: str, clone_to_dir: Path) -> None:
    """Run the VCS clone command inside `clone_to_dir`."""
    subprocess.check_output(
        [repo_type, 'clone', repo_url],
        cwd=clone_to_dir,
        stderr=subprocess.STDOUT,
    )


def _run_checkout(repo_type: str, checkout: str, repo_dir: str) -> None:
    """Run the VCS checkout command inside `repo_dir`."""
    # Avoid Mercurial "--config" and "--debugger" injection vulnerability
    checkout_params = ['--', checkout] if repo_type == 'hg' else [checkout]
    subprocess.check_output(
        [repo_type, 'checkout', *checkout_params],
        cwd=repo_dir,
        stderr=subprocess.STDOUT,
    )


def _raise_if_known_clone_error(
    output: str,
    repo_url: str,
    checkout: str | None,
    clone_error: subprocess.CalledProcessError,
) -> None:
    """Translate recognised VCS failures into Cookiecutter exceptions.

    Returns normally if the failure is not recognised, so that the caller
    can log it and re-raise the original error.
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
    clone_to_dir = Path(clone_to_dir).expanduser()
    make_sure_path_exists(clone_to_dir)

    repo_type, repo_url = identify_repo(repo_url)
    _ensure_vcs_installed(repo_type)

    repo_url = repo_url.rstrip('/')
    repo_dir = _build_repo_dir(repo_type, repo_url, clone_to_dir)
    logger.debug('repo_dir is %s', repo_dir)

    if _should_clone(repo_dir, no_input):
        try:
            _run_clone(repo_type, repo_url, clone_to_dir)
            if checkout is not None:
                _run_checkout(repo_type, checkout, repo_dir)
        except subprocess.CalledProcessError as clone_error:
            output = clone_error.output.decode('utf-8')
            _raise_if_known_clone_error(output, repo_url, checkout, clone_error)
            logger.exception('git clone failed with error: %s', output)
            raise

    return repo_dir
```

## Refactorizaciones aplicadas

- **Extract Function** – `_ensure_vcs_installed` (desde `clone`).
  - Motivo: aísla la precondición "el VCS está instalado" y deja `clone` como una secuencia de pasos con nombre propio.
  - Sigue llamando a `is_vcs_installed` a través del módulo, así que los *mocks* de los tests siguen funcionando.

- **Extract Function + Consolidate Duplicate Conditional Fragments** – `_build_repo_dir` (desde `clone`).
  - Motivo: el original calculaba `repo_dir = os.path.normpath(os.path.join(...))` dos veces, en dos `if` separados para `git` y `hg`. Ahora solo el ajuste del nombre es específico de git, y la construcción de la ruta es común.
  - Se conserva literalmente la expresión `repo_name.split(':')[-1].rsplit('.git')[0]`.
  - Como `identify_repo` solo devuelve `'git'` o `'hg'`, el resultado es idéntico.

- **Extract Function** – `_should_clone` (desde `clone`).
  - Motivo: encapsula la decisión "¿hay que clonar?", incluida la pregunta al usuario mediante `prompt_and_delete`.

- **Rename Variable** – la variable local `clone` desaparece y su papel lo cumple `_should_clone(...)`.
  - Motivo: el original sombreaba el nombre de la propia función `clone`, lo que confundía al lector.

- **Extract Function** – `_run_clone` y `_run_checkout` (desde `clone`).
  - Motivo: separan las invocaciones a `subprocess` del flujo principal.
  - Los argumentos de `subprocess.check_output` son exactamente los mismos: lista posicional, `cwd` y `stderr`.

- **Replace Mutation with Expression** (variante de *Split Variable / Remove Mutation*) – `checkout_params` en `_run_checkout`.
  - Motivo: el `insert(0, "--")` condicional se sustituye por una expresión condicional que produce la misma lista: `['--', checkout]` para hg y `[checkout]` para git.
  - Se mantiene el comentario de seguridad sobre la inyección en Mercurial.

- **Extract Function** – `_raise_if_known_clone_error` (desde el bloque `except` de `clone`).
  - Motivo: la traducción de errores del VCS a excepciones de Cookiecutter queda aislada.
  - El `logger.exception(...)` y el `raise` desnudo se quedan en el bloque `except` original. Así se conservan el traceback y la excepción relanzada.
  - Los mensajes de error se mantienen literalmente, incluida la errata "could not found", para no alterar la salida observable.

- **Replace Magic Literal** – nueva constante `_SUPPORTED_REPO_TYPES` en `identify_repo`.
  - Motivo: da nombre a la lista de tipos soportados. La comprobación de pertenencia es equivalente.

- **Rename Variable + desempaquetado** – `repo_url_values` pasa a `url_parts`, desempaquetado en `repo_type, url_without_prefix` en `identify_repo`.
  - Motivo: los índices `[0]` y `[1]` se sustituyen por nombres que expresan su significado.

- **Corrección de documentación** – docstring de `identify_repo`.
  - Motivo: indicaba que podía devolver `None`, cuando en realidad lanza `UnknownRepoType`. Solo cambia la documentación.

- **Cambio de formato de log** – `logger.debug(f'repo_dir is {repo_dir}')` pasa a `logger.debug('repo_dir is %s', repo_dir)`.
  - Motivo: formateo perezoso, coherente con el resto del paquete (por ejemplo, `config.py`). El mensaje final que se emite es idéntico.

- **Reordenación de imports**.
  - Motivo: el bloque `if TYPE_CHECKING:` estaba intercalado entre los imports de la librería estándar y los del proyecto. Se ha movido tras todos los imports, sin efecto en tiempo de ejecución.

Las funciones públicas `identify_repo`, `is_vcs_installed` y `clone`, así como la constante `BRANCH_ERRORS`, conservan su nombre y su firma.