```python
"""All exceptions used in the Cookiecutter code base are defined here.

Every exception inherits from :class:`CookiecutterException`, so callers can
catch any Cookiecutter-specific error with a single ``except`` clause.

The exceptions are grouped by the stage of the workflow in which they are
raised:

* configuration loading,
* repository location (abbreviations, VCS, zip archives),
* template context and rendering,
* invocation and project generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import TemplateError


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
# Repository location: abbreviations, version control and zip archives
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
# Template context and rendering
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
    """

    # Not raised anywhere inside Cookiecutter itself; kept as part of the
    # public API for backwards compatibility.


class ContextDecodingException(CookiecutterException):
    """Exception for failed JSON decoding.

    Raised when a project's JSON context file can not be decoded.
    """


class UndefinedVariableInTemplate(CookiecutterException):
    """Exception for out-of-scope variables.

    Raised when a template uses a variable which is not defined in the
    context.
    """

    def __init__(
        self, message: str, error: TemplateError, context: dict[str, Any]
    ) -> None:
        """Store the message, the original Jinja2 error and the render context.

        :param message: Human readable description of what failed to render.
        :param error: The Jinja2 error raised while rendering.
        :param context: The context that was used for rendering.
        """
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
# Invocation and project generation
# ---------------------------------------------------------------------------


class InvalidModeException(CookiecutterException):
    """Exception for incompatible modes.

    Raised when cookiecutter is called with ``replay`` together with
    ``no_input`` or ``extra_context`` at the same time.
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
    """

    # Not raised anywhere inside Cookiecutter itself; kept as part of the
    # public API for backwards compatibility.


class FailedHookException(CookiecutterException):
    """Exception for hook failures.

    Raised when a hook script fails.
    """
```

## Refactorizaciones aplicadas

- **Slide Statements (reordenar declaraciones) + comentarios de sección**
  - *Elementos afectados:* todas las clases de excepción, que ahora están agrupadas en cuatro bloques: configuración, localización del repositorio, contexto/renderizado e invocación/generación.
  - *Motivo:* el orden original era arbitrario. Por ejemplo, `RepositoryNotFound` e `InvalidZipRepository` aparecían al final, lejos de `UnknownRepoType` y `VCSNotInstalled`. Con la agrupación es más fácil localizar una excepción y decidir dónde añadir una nueva.
  - *Por qué no cambia el comportamiento:* las clases no dependen entre sí salvo de la base `CookiecutterException`, que sigue definiéndose primero. La jerarquía, los nombres y el MRO son idénticos.

- **Docstring de módulo ampliado**
  - *Elementos afectados:* docstring de `cookiecutter/exceptions.py`.
  - *Motivo:* documenta que todas heredan de `CookiecutterException` y explica el criterio de agrupación, de modo que sirve como índice del archivo.

- **Normalización del formato de docstrings (PEP 257)**
  - *Elementos afectados:* todas las clases cuyo resumen empezaba en la segunda línea (`"""\n    Base exception class.`).
  - *Motivo:* ahora el resumen va en la primera línea, igual que en el resto del paquete (`config.py`, `generate.py`, `hooks.py`…). Así el estilo es uniforme.

- **Corrección de documentación**
  - *`EmptyDirNameException`:* se corrige la errata "a empty" → "an empty".
  - *`InvalidModeException`:* la docstring no describía la condición real. `main.cookiecutter` lanza la excepción cuando se combina `replay` con `no_input` **o** con `extra_context`, y no solo con `no_input==True`.
  - *`UndefinedVariableInTemplate.__init__`:* su docstring repetía la de la clase. Ahora describe los tres parámetros que almacena.

- **Comentarios aclaratorios**
  - *Elementos afectados:* `UnknownTemplateDirException` y `MissingProjectDir`.
  - *Motivo:* el comentario `# unused locally` era ambiguo. Se sustituye por uno que explica que esas excepciones no se lanzan dentro de Cookiecutter, pero se conservan como API pública por compatibilidad. Así se evita que alguien las elimine creyendo que son código muerto.

**Cambios descartados deliberadamente para preservar el comportamiento observable:**

- **No se añadió `super().__init__(message)` en `UndefinedVariableInTemplate`.** Hoy `e.args` vale `(message, error, context)`, porque `BaseException.__new__` guarda todos los argumentos posicionales. Llamar a `super().__init__(message)` lo cambiaría a `(message,)` y afectaría a quien inspeccione `args` o serialice la excepción con `pickle`.
- **No se introdujeron clases base intermedias por categoría.** Alterarían el MRO y añadirían API pública nueva.
- **No se añadió `__all__`.** Modificaría lo que exporta `from cookiecutter.exceptions import *`.