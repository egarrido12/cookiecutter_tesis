```python
"""All exceptions used in the Cookiecutter code base are defined here.

Exceptions are grouped by the area of Cookiecutter that raises them:

* Base exception.
* Configuration.
* Repositories (VCS and zip archives).
* Templates and context.
* Project generation and hooks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import TemplateError


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------


class CookiecutterException(Exception):
    """Base exception class.

    All Cookiecutter-specific exceptions should subclass this class.
    """


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class ConfigDoesNotExistException(CookiecutterException):
    """Exception for missing config file.

    Raised when get_config() is passed a path to a config file, but no file
    is found at that path.
    """


class InvalidConfiguration(CookiecutterException):
    """Exception for invalid configuration file.

    Raised if the global configuration file is not valid YAML or is
    badly constructed.
    """


# ---------------------------------------------------------------------------
# Repositories (VCS and zip archives)
# ---------------------------------------------------------------------------


class UnknownRepoType(CookiecutterException):
    """Exception for unknown repo types.

    Raised if a repo's type cannot be determined.
    """


class VCSNotInstalled(CookiecutterException):
    """Exception when version control is unavailable.

    Raised if the version control system (git or hg) is not installed.
    """


class RepositoryNotFound(CookiecutterException):
    """Exception for missing repo.

    Raised when the specified cookiecutter repository doesn't exist.
    """


class RepositoryCloneFailed(CookiecutterException):
    """Exception for un-cloneable repo.

    Raised when a cookiecutter template can't be cloned.
    """


class InvalidZipRepository(CookiecutterException):
    """Exception for bad zip repo.

    Raised when the specified cookiecutter repository isn't a valid
    Zip archive.
    """


# ---------------------------------------------------------------------------
# Templates and context
# ---------------------------------------------------------------------------


class NonTemplatedInputDirException(CookiecutterException):
    """Exception for when a project's input dir is not templated.

    The name of the input directory should always contain a string that is
    rendered to something else, so that input_dir != output_dir.
    """


class UnknownTemplateDirException(CookiecutterException):
    """Exception for ambiguous project template directory.

    Raised when Cookiecutter cannot determine which directory is the project
    template, e.g. more than one dir appears to be a template dir.

    Not raised by Cookiecutter itself; kept for backwards compatibility.
    """


class ContextDecodingException(CookiecutterException):
    """Exception for failed JSON decoding.

    Raised when a project's JSON context file can not be decoded.
    """


class UndefinedVariableInTemplate(CookiecutterException):
    """Exception for out-of-scope variables.

    Raised when a template uses a variable which is not defined in the
    context.
    """

    message: str
    error: TemplateError
    context: dict[str, Any]

    def __init__(
        self, message: str, error: TemplateError, context: dict[str, Any]
    ) -> None:
        """Exception for out-of-scope variables."""
        # ``Exception.__init__`` is intentionally not called: the textual
        # representation is built by ``__str__`` from the attributes below.
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
    """Exception for un-importable extension.

    Raised when an environment is unable to import a required extension.
    """


# ---------------------------------------------------------------------------
# Project generation and hooks
# ---------------------------------------------------------------------------


class InvalidModeException(CookiecutterException):
    """Exception for incompatible modes.

    Raised when cookiecutter is called with both `no_input==True` and
    `replay==True` at the same time.
    """


class OutputDirExistsException(CookiecutterException):
    """Exception for existing output directory.

    Raised when the output directory of the project exists already.
    """


class EmptyDirNameException(CookiecutterException):
    """Exception for an empty directory name.

    Raised when the directory name provided is empty.
    """


class MissingProjectDir(CookiecutterException):
    """Exception for missing generated project directory.

    Raised during cleanup when remove_repo() can't find a generated project
    directory inside of a repo.

    Not raised by Cookiecutter itself; kept for backwards compatibility.
    """


class FailedHookException(CookiecutterException):
    """Exception for hook failures.

    Raised when a hook script fails.
    """
```

## Refactorizaciones aplicadas

- **Slide Statements (reordenar declaraciones por cohesión)**
  - *Elementos afectados:* todas las clases de excepción del módulo. Se agrupan en secciones con comentarios de cabecera: base, configuración, repositorios, plantillas/contexto y generación/hooks.
  - *Motivo:* antes estaban en un orden casi arbitrario. Por ejemplo, `RepositoryNotFound` e `InvalidZipRepository` quedaban lejos de `UnknownRepoType` y `VCSNotInstalled`. Ahora quien busca "qué puede fallar al clonar" encuentra todo junto.
  - *Por qué no cambia el comportamiento:* ninguna clase depende de otra salvo de `CookiecutterException`, que sigue definida primero. Los nombres y la jerarquía de herencia son idénticos.

- **Replace Comment with Documentation (sustituir comentario por documentación)**
  - *Elementos afectados:* `UnknownTemplateDirException` y `MissingProjectDir`. El comentario suelto `# unused locally` dentro del cuerpo de la clase pasa al docstring como "Not raised by Cookiecutter itself; kept for backwards compatibility."
  - *Motivo:* el comentario era ambiguo, porque daba a entender código muerto que se podría borrar. En realidad son parte de la API pública y no se pueden eliminar sin romper a terceros. Ahora la intención es explícita y visible en la documentación generada.

- **Normalización del formato de docstrings**
  - *Elementos afectados:* los docstrings de todas las excepciones. El resumen pasa a la primera línea, como en el resto del paquete (`config.py`, `utils.py`, etc.).
  - *Motivo:* consistencia de estilo con el resto del proyecto. `inspect.getdoc()` y Sphinx producen el mismo texto limpio.
  - *Corrección de errata:* "a empty" → "an empty" en `EmptyDirNameException`.

- **Declarar los atributos de instancia a nivel de clase**
  - *Elementos afectados:* `UndefinedVariableInTemplate.message`, `.error` y `.context`. Se añaden como anotaciones de clase, sin valor asignado.
  - *Motivo:* el lector y las herramientas de tipado ven de un vistazo qué atributos expone la excepción. `cli.py` los consume directamente (`undefined_err.message`, `undefined_err.error.message`, `undefined_err.context`).
  - *Por qué no cambia el comportamiento:* al no asignarse valor, no se crean atributos de clase. `TemplateError` sigue importándose solo bajo `TYPE_CHECKING`, y no se evalúa gracias a `from __future__ import annotations`.

- **Comentario explicativo**
  - *Elemento afectado:* `UndefinedVariableInTemplate.__init__`.
  - *Motivo:* se documenta que no llamar a `super().__init__()` es intencional. Se mantiene así para no alterar `args`, `repr()` ni el comportamiento al serializar con pickle, y para evitar que un futuro mantenedor lo "arregle" cambiando el comportamiento observable.

**Decisión de no aplicar:** no se convirtió `UndefinedVariableInTemplate` en `dataclass` ni se añadió `__all__`. Lo primero alteraría `__eq__`, `__repr__` y `args`; lo segundo cambiaría el resultado de `from cookiecutter.exceptions import *`. Ambas cosas violarían la regla de comportamiento idéntico.