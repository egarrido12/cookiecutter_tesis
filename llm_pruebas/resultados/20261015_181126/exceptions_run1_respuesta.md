```python
"""All exceptions used in the Cookiecutter code base are defined here."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import TemplateError


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------


class CookiecutterException(Exception):
    """
    Base exception class.

    All Cookiecutter-specific exceptions should subclass this class.
    """


# ---------------------------------------------------------------------------
# User configuration
# ---------------------------------------------------------------------------


class ConfigDoesNotExistException(CookiecutterException):
    """
    Exception for missing config file.

    Raised when get_config() is passed a path to a config file, but no file
    is found at that path.
    """


class InvalidConfiguration(CookiecutterException):
    """
    Exception for invalid configuration file.

    Raised if the global configuration file is not valid YAML or is
    badly constructed.
    """


# ---------------------------------------------------------------------------
# Repositories: version control systems and zip archives
# ---------------------------------------------------------------------------


class UnknownRepoType(CookiecutterException):
    """
    Exception for unknown repo types.

    Raised if a repo's type cannot be determined.
    """


class VCSNotInstalled(CookiecutterException):
    """
    Exception when version control is unavailable.

    Raised if the version control system (git or hg) is not installed.
    """


class RepositoryNotFound(CookiecutterException):
    """
    Exception for missing repo.

    Raised when the specified cookiecutter repository doesn't exist.
    """


class RepositoryCloneFailed(CookiecutterException):
    """
    Exception for un-cloneable repo.

    Raised when a cookiecutter template can't be cloned.
    """


class InvalidZipRepository(CookiecutterException):
    """
    Exception for bad zip repo.

    Raised when the specified cookiecutter repository isn't a valid
    Zip archive.
    """


# ---------------------------------------------------------------------------
# Templates, context and Jinja2 environment
# ---------------------------------------------------------------------------


class NonTemplatedInputDirException(CookiecutterException):
    """
    Exception for when a project's input dir is not templated.

    The name of the input directory should always contain a string that is
    rendered to something else, so that input_dir != output_dir.
    """


class UnknownTemplateDirException(CookiecutterException):
    """
    Exception for ambiguous project template directory.

    Raised when Cookiecutter cannot determine which directory is the project
    template, e.g. more than one dir appears to be a template dir.
    """

    # Not raised anywhere inside this package; kept as part of the public API
    # for backwards compatibility with code that imports or catches it.


class ContextDecodingException(CookiecutterException):
    """
    Exception for failed JSON decoding.

    Raised when a project's JSON context file can not be decoded.
    """


class UndefinedVariableInTemplate(CookiecutterException):
    """
    Exception for out-of-scope variables.

    Raised when a template uses a variable which is not defined in the
    context.
    """

    def __init__(
        self, message: str, error: TemplateError, context: dict[str, Any]
    ) -> None:
        """Exception for out-of-scope variables."""
        # ``Exception.__init__`` is intentionally not called: the textual
        # representation is built by ``__str__`` from these attributes.
        self.message = message
        self.error = error
        self.context = context

    def __str__(self) -> str:
        """Text representation of UndefinedVariableInTemplate."""
        return (
            f"{self.message}. "
            f"Error message: {self.error.message}. "
            f"Context: {self.context}"
        )


class UnknownExtension(CookiecutterException):
    """
    Exception for un-importable extension.

    Raised when an environment is unable to import a required extension.
    """


# ---------------------------------------------------------------------------
# Execution modes, project generation and hooks
# ---------------------------------------------------------------------------


class InvalidModeException(CookiecutterException):
    """
    Exception for incompatible modes.

    Raised when cookiecutter is called with both `no_input==True` and
    `replay==True` at the same time.
    """


class OutputDirExistsException(CookiecutterException):
    """
    Exception for existing output directory.

    Raised when the output directory of the project exists already.
    """


class EmptyDirNameException(CookiecutterException):
    """
    Exception for a empty directory name.

    Raised when the directory name provided is empty.
    """


class MissingProjectDir(CookiecutterException):
    """
    Exception for missing generated project directory.

    Raised during cleanup when remove_repo() can't find a generated project
    directory inside of a repo.
    """

    # Not raised anywhere inside this package; kept as part of the public API
    # for backwards compatibility with code that imports or catches it.


class FailedHookException(CookiecutterException):
    """
    Exception for hook failures.

    Raised when a hook script fails.
    """
```

## Refactorizaciones aplicadas

El módulo ya era sencillo: una clase base y subclases vacías, salvo `UndefinedVariableInTemplate`. Por eso los cambios se limitan a organización y documentación interna. Se descartaron a propósito varias transformaciones que habrían alterado el comportamiento observable.

- **Slide Statements / reorganización del módulo por cohesión**
  - *Elementos afectados:* todas las clases de excepción. Se agrupan en secciones temáticas con comentarios separadores:
    - base;
    - configuración de usuario;
    - repositorios (VCS y zip);
    - plantillas, contexto y entorno Jinja2;
    - modos de ejecución, generación y hooks.
  - *Motivo:* antes, las excepciones de un mismo dominio estaban dispersas. Por ejemplo, `RepositoryNotFound` y `RepositoryCloneFailed` aparecían al final, lejos de `UnknownRepoType` y `VCSNotInstalled`. Ahora quien mantiene `vcs.py`, `zipfile.py` o `config.py` encuentra juntas las excepciones que le conciernen.
  - *Comportamiento:* `CookiecutterException` sigue definida primero, porque las demás dependen de ella. Ninguna otra clase depende de la posición de otra, así que el orden no altera nada.

- **Sustitución de comentarios crípticos por comentarios explicativos**
  - *Elementos afectados:* `UnknownTemplateDirException` y `MissingProjectDir`.
  - *Motivo:* el comentario `# unused locally` no explicaba por qué seguían existiendo estas clases, y podía invitar a borrarlas. Ahora se indica que no se lanzan dentro del paquete, pero forman parte de la API pública y se conservan por retrocompatibilidad.

- **Comentario explicativo de una decisión no obvia**
  - *Elemento afectado:* `UndefinedVariableInTemplate.__init__`.
  - *Motivo:* el constructor no llama a `Exception.__init__`, por lo que `args` queda vacío y la representación textual depende solo de `__str__`. Se documenta que es intencional, para que nadie lo "corrija" sin darse cuenta de que cambiaría `args`, `repr()` y el comportamiento al serializar con pickle.

### Cambios descartados a propósito (para no alterar el comportamiento)

- **No se aplicó Extract Superclass** (por ejemplo, una base común para las excepciones de repositorio). Cambiaría `__bases__`/`__mro__` y el resultado de `isinstance`/`except` en código de terceros.
- **No se añadió `__all__`.** Modificaría lo que exporta `from cookiecutter.exceptions import *`.
- **No se añadió `super().__init__(...)` en `UndefinedVariableInTemplate`.** Cambiaría `args`, `repr()` y la serialización con pickle.
- **No se modificó el texto de ningún docstring.** Forman parte de `__doc__` y de la documentación generada. Quedan como mejoras sugeridas para un cambio aparte, por ser modificaciones de documentación:
  - la errata "a empty" en `EmptyDirNameException`;
  - la referencia obsoleta a `remove_repo()` en `MissingProjectDir`.