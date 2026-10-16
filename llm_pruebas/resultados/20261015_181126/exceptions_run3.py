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
