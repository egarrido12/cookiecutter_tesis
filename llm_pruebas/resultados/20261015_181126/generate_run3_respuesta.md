```python
"""Functions for generating a project from a project template."""

from __future__ import annotations

import fnmatch
import json
import logging
import os
import shutil
import warnings
from collections import OrderedDict
from pathlib import Path
from typing import Any

from binaryornot.check import is_binary
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateSyntaxError, UndefinedError
from rich.prompt import InvalidResponse

from cookiecutter.exceptions import (
    ContextDecodingException,
    EmptyDirNameException,
    OutputDirExistsException,
    UndefinedVariableInTemplate,
)
from cookiecutter.find import find_template
from cookiecutter.hooks import run_hook_from_repo_dir
from cookiecutter.prompt import YesNoPrompt
from cookiecutter.utils import (
    create_env_with_context,
    make_sure_path_exists,
    rmtree,
    work_in,
)

logger = logging.getLogger(__name__)


def is_copy_only_path(path: str, context: dict[str, Any]) -> bool:
    """Check whether the given `path` should only be copied and not rendered.

    Returns True if `path` matches a pattern in the given `context` dict,
    otherwise False.

    :param path: A file-system path referring to a file or dir that
        should be rendered or just copied.
    :param context: cookiecutter context.
    """
    try:
        copy_only_patterns = context['cookiecutter']['_copy_without_render']
    except KeyError:
        return False

    return any(fnmatch.fnmatch(path, pattern) for pattern in copy_only_patterns)


def _apply_multichoice_overwrite(
    context: dict[str, Any], variable: str, overwrite: list[Any]
) -> None:
    """Replace a multi-choice variable, validating that all choices are valid."""
    valid_choices = context[variable]
    if not set(overwrite).issubset(set(valid_choices)):
        msg = (
            f"{overwrite} provided for multi-choice variable "
            f"{variable}, but valid choices are {valid_choices}"
        )
        raise ValueError(msg)
    context[variable] = overwrite


def _apply_choice_overwrite(choices: list[Any], variable: str, overwrite: Any) -> None:
    """Make ``overwrite`` the default choice by moving it to the first position.

    By definition the default of a choice variable is the first item of the list,
    see ``cookiecutter.prompt.prompt_choice_for_config``.
    """
    if overwrite not in choices:
        msg = (
            f"{overwrite} provided for choice variable "
            f"{variable}, but the choices are {choices}."
        )
        raise ValueError(msg)
    choices.remove(overwrite)
    choices.insert(0, overwrite)


def _convert_overwrite_to_bool(variable: str, overwrite: str) -> bool:
    """Convert the string ``overwrite`` to its boolean counterpart."""
    try:
        return YesNoPrompt().process_response(overwrite)
    except InvalidResponse as err:
        msg = (
            f"{overwrite} provided for variable "
            f"{variable} could not be converted to a boolean."
        )
        raise ValueError(msg) from err


def apply_overwrites_to_context(
    context: dict[str, Any],
    overwrite_context: dict[str, Any],
    *,
    in_dictionary_variable: bool = False,
) -> None:
    """Modify the given context in place based on the overwrite_context."""
    for variable, overwrite in overwrite_context.items():
        if variable not in context:
            if not in_dictionary_variable:
                # We are dealing with a new variable on first level, ignore
                continue
            # We are dealing with a new dictionary variable in a deeper level
            context[variable] = overwrite

        context_value = context[variable]
        if isinstance(context_value, list):
            if in_dictionary_variable:
                context[variable] = overwrite
            elif isinstance(overwrite, list):
                _apply_multichoice_overwrite(context, variable, overwrite)
            else:
                _apply_choice_overwrite(context_value, variable, overwrite)
        elif isinstance(context_value, dict) and isinstance(overwrite, dict):
            # Partially overwrite some keys in original dict (modified in place)
            apply_overwrites_to_context(
                context_value, overwrite, in_dictionary_variable=True
            )
        elif isinstance(context_value, bool) and isinstance(overwrite, str):
            context[variable] = _convert_overwrite_to_bool(variable, overwrite)
        else:
            # Simply overwrite the value for this variable
            context[variable] = overwrite


def _load_context_file(context_file: str) -> OrderedDict[str, Any]:
    """Load the JSON context file, raising a friendly error if it is invalid."""
    try:
        with open(context_file, encoding='utf-8') as file_handle:
            return json.load(file_handle, object_pairs_hook=OrderedDict)
    except ValueError as e:
        # JSON decoding error.  Let's throw a new exception that is more
        # friendly for the developer or user.
        full_fpath = os.path.abspath(context_file)
        msg = (
            f"JSON decoding error while loading '{full_fpath}'. "
            f"Decoding error details: '{e}'"
        )
        raise ContextDecodingException(msg) from e


def _context_key_from_file_name(context_file: str) -> str:
    """Return the file name of ``context_file`` without directory and extension."""
    file_name = os.path.split(context_file)[1]
    return file_name.split('.')[0]


def generate_context(
    context_file: str = 'cookiecutter.json',
    default_context: dict[str, Any] | None = None,
    extra_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate the context for a Cookiecutter project template.

    Loads the JSON file as a Python object, with key being the JSON filename.

    :param context_file: JSON file containing key/value pairs for populating
        the cookiecutter's variables.
    :param default_context: Dictionary containing config to take into account.
    :param extra_context: Dictionary containing configuration overrides
    """
    context = OrderedDict([])

    template_context = _load_context_file(context_file)
    context[_context_key_from_file_name(context_file)] = template_context

    # Overwrite context variable defaults with the default context from the
    # user's global config, if available
    if default_context:
        try:
            apply_overwrites_to_context(template_context, default_context)
        except ValueError as error:
            warnings.warn(f"Invalid default received: {error}")
    if extra_context:
        apply_overwrites_to_context(template_context, extra_context)

    logger.debug('Context generated is %s', context)
    return context


def _copy_file_with_permissions(source: str, destination: str) -> None:
    """Copy the contents and the permission bits of ``source`` to ``destination``."""
    shutil.copyfile(source, destination)
    shutil.copymode(source, destination)


def _render_template_file(
    env: Environment, infile: str, context: dict[str, Any]
) -> str:
    """Render the contents of the template file ``infile``."""
    # Force fwd slashes on Windows for get_template
    # This is a by-design Jinja issue
    template_name = infile.replace(os.path.sep, '/')

    try:
        template = env.get_template(template_name)
    except TemplateSyntaxError as exception:
        # Disable translated so that printed exception contains verbose
        # information about syntax error location
        exception.translated = False
        raise
    return template.render(**context)


def _determine_newline(infile: str, context: dict[str, Any]) -> str | None:
    """Return the newline to use when writing the rendered ``infile``.

    Use `_new_lines` from context if configured, otherwise detect the newline
    used in the original file.
    """
    configured_newline = context['cookiecutter'].get('_new_lines', False)
    if configured_newline:
        logger.debug('Using configured newline character %s', repr(configured_newline))
        return configured_newline

    # Note that newlines can be a tuple if file contains mixed line endings.
    # In this case, we pick the first line ending we detected.
    with open(infile, encoding='utf-8') as file_handle:
        file_handle.readline()  # Read only the first line to load a 'newlines' value.
    newlines = file_handle.newlines
    newline = newlines[0] if isinstance(newlines, tuple) else newlines
    logger.debug('Using detected newline character %s', repr(newline))
    return newline


def generate_file(
    project_dir: str,
    infile: str,
    context: dict[str, Any],
    env: Environment,
    skip_if_file_exists: bool = False,
) -> None:
    """Render filename of infile as name of outfile, handle infile correctly.

    Dealing with infile appropriately:

        a. If infile is a binary file, copy it over without rendering.
        b. If infile is a text file, render its contents and write the
           rendered infile to outfile.

    Precondition:

        When calling `generate_file()`, the root template dir must be the
        current working directory. Using `utils.work_in()` is the recommended
        way to perform this directory change.

    :param project_dir: Absolute path to the resulting generated project.
    :param infile: Input file to generate the file from. Relative to the root
        template dir.
    :param context: Dict for populating the cookiecutter's variables.
    :param env: Jinja2 template execution environment.
    """
    logger.debug('Processing file %s', infile)

    # Render the path to the output file (not including the root project dir)
    rendered_name = env.from_string(infile).render(**context)
    outfile = os.path.join(project_dir, rendered_name)

    file_name_is_empty = os.path.isdir(outfile)
    if file_name_is_empty:
        logger.debug('The resulting file name is empty: %s', outfile)
        return

    if skip_if_file_exists and os.path.exists(outfile):
        logger.debug('The resulting file already exists: %s', outfile)
        return

    logger.debug('Created file at %s', outfile)

    # Just copy over binary files. Don't render.
    logger.debug("Check %s to see if it's a binary", infile)
    if is_binary(infile):
        logger.debug('Copying binary %s to %s without rendering', infile, outfile)
        _copy_file_with_permissions(infile, outfile)
        return

    rendered_file = _render_template_file(env, infile, context)
    newline = _determine_newline(infile, context)

    logger.debug('Writing contents to file %s', outfile)
    with open(outfile, 'w', encoding='utf-8', newline=newline) as outfile_handle:
        outfile_handle.write(rendered_file)

    # Apply file permissions to output file
    shutil.copymode(infile, outfile)


def render_and_create_dir(
    dirname: str,
    context: dict[str, Any],
    output_dir: Path | str,
    environment: Environment,
    overwrite_if_exists: bool = False,
) -> tuple[Path, bool]:
    """Render name of a directory, create the directory, return its path."""
    if not dirname:
        msg = 'Error: directory name is empty'
        raise EmptyDirNameException(msg)

    rendered_dirname = environment.from_string(dirname).render(**context)
    dir_to_create = Path(output_dir, rendered_dirname)

    logger.debug(
        'Rendered dir %s must exist in output_dir %s', dir_to_create, output_dir
    )

    output_dir_exists = dir_to_create.exists()

    if not output_dir_exists:
        make_sure_path_exists(dir_to_create)
    elif overwrite_if_exists:
        logger.debug(
            'Output directory %s already exists, overwriting it', dir_to_create
        )
    else:
        msg = f'Error: "{dir_to_create}" directory already exists'
        raise OutputDirExistsException(msg)

    return dir_to_create, not output_dir_exists


def _run_hook_from_repo_dir(
    repo_dir: str,
    hook_name: str,
    project_dir: Path | str,
    context: dict[str, Any],
    delete_project_on_failure: bool,
) -> None:
    """Run hook from repo directory, clean project directory if hook fails.

    :param repo_dir: Project template input directory.
    :param hook_name: The hook to execute.
    :param project_dir: The directory to execute the script from.
    :param context: Cookiecutter project context.
    :param delete_project_on_failure: Delete the project directory on hook
        failure?
    """
    warnings.warn(
        "The '_run_hook_from_repo_dir' function is deprecated, "
        "use 'cookiecutter.hooks.run_hook_from_repo_dir' instead",
        DeprecationWarning,
        2,
    )
    run_hook_from_repo_dir(
        repo_dir, hook_name, project_dir, context, delete_project_on_failure
    )


def _create_project_dir(
    template_dir: Path | str,
    context: dict[str, Any],
    output_dir: Path | str,
    env: Environment,
    overwrite_if_exists: bool,
) -> tuple[str, bool]:
    """Render and create the root project directory.

    :return: The absolute path to the project directory and whether it was
        created by this call.
    """
    unrendered_dir = os.path.split(template_dir)[1]
    try:
        project_dir, output_directory_created = render_and_create_dir(
            unrendered_dir, context, output_dir, env, overwrite_if_exists
        )
    except UndefinedError as err:
        msg = f"Unable to create project directory '{unrendered_dir}'"
        raise UndefinedVariableInTemplate(msg, err, context) from err

    return os.path.abspath(project_dir), output_directory_created


def _split_copy_only_dirs(
    root: str, dirnames: list[str], context: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Split ``dirnames`` into directories to copy as-is and directories to render.

    The full path is checked, because that's how it can be specified in the
    ``_copy_without_render`` setting, but only the dir name is returned.
    """
    copy_dirs = []
    render_dirs = []

    for dirname in sorted(dirnames):
        dir_path = os.path.normpath(os.path.join(root, dirname))
        if is_copy_only_path(dir_path, context):
            logger.debug('Found copy only path %s', dirname)
            copy_dirs.append(dirname)
        else:
            render_dirs.append(dirname)

    return copy_dirs, render_dirs


def _copy_dir_without_render(
    root: str,
    dirname: str,
    project_dir: str,
    env: Environment,
    context: dict[str, Any],
) -> None:
    """Copy a copy-only directory into the project without rendering its contents."""
    indir = os.path.normpath(os.path.join(root, dirname))
    outdir = os.path.normpath(os.path.join(project_dir, indir))
    outdir = env.from_string(outdir).render(**context)
    logger.debug('Copying dir %s to %s without rendering', indir, outdir)

    # The outdir is not the root dir, it is the dir which marked as copy
    # only in the config file. If the program hits this line, which means
    # the overwrite_if_exists = True, and root dir exists
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    shutil.copytree(indir, outdir)


def _create_rendered_dir(
    root: str,
    dirname: str,
    *,
    project_dir: str,
    output_dir: Path | str,
    env: Environment,
    context: dict[str, Any],
    overwrite_if_exists: bool,
    delete_project_on_failure: bool,
) -> None:
    """Render the name of a template sub-directory and create it in the project."""
    unrendered_dir = os.path.join(project_dir, root, dirname)
    try:
        render_and_create_dir(
            unrendered_dir, context, output_dir, env, overwrite_if_exists
        )
    except UndefinedError as err:
        if delete_project_on_failure:
            rmtree(project_dir)
        relative_dir = os.path.relpath(unrendered_dir, output_dir)
        msg = f"Unable to create directory '{relative_dir}'"
        raise UndefinedVariableInTemplate(msg, err, context) from err


def _copy_file_without_render(
    infile: str, project_dir: str, env: Environment, context: dict[str, Any]
) -> None:
    """Copy a copy-only file into the project, rendering only its name."""
    outfile_rendered = env.from_string(infile).render(**context)
    outfile = os.path.join(project_dir, outfile_rendered)
    logger.debug('Copying file %s to %s without rendering', infile, outfile)
    _copy_file_with_permissions(infile, outfile)


def _process_template_file(
    root: str,
    filename: str,
    *,
    project_dir: str,
    env: Environment,
    context: dict[str, Any],
    skip_if_file_exists: bool,
    delete_project_on_failure: bool,
) -> None:
    """Copy or render a single template file into the project."""
    infile = os.path.normpath(os.path.join(root, filename))
    if is_copy_only_path(infile, context):
        _copy_file_without_render(infile, project_dir, env, context)
        return

    try:
        generate_file(project_dir, infile, context, env, skip_if_file_exists)
    except UndefinedError as err:
        if delete_project_on_failure:
            rmtree(project_dir)
        msg = f"Unable to create file '{infile}'"
        raise UndefinedVariableInTemplate(msg, err, context) from err


def generate_files(
    repo_dir: Path | str,
    context: dict[str, Any] | None = None,
    output_dir: Path | str = '.',
    overwrite_if_exists: bool = False,
    skip_if_file_exists: bool = False,
    accept_hooks: bool = True,
    keep_project_on_failure: bool = False,
) -> str:
    """Render the templates and saves them to files.

    :param repo_dir: Project template input directory.
    :param context: Dict for populating the template's variables.
    :param output_dir: Where to output the generated project dir into.
    :param overwrite_if_exists: Overwrite the contents of the output directory
        if it exists.
    :param skip_if_file_exists: Skip the files in the corresponding directories
        if they already exist
    :param accept_hooks: Accept pre and post hooks if set to `True`.
    :param keep_project_on_failure: If `True` keep generated project directory even when
        generation fails
    """
    context = context or OrderedDict([])

    env = create_env_with_context(context)

    template_dir = find_template(repo_dir, env)
    logger.debug('Generating project from %s...', template_dir)

    # We want the Jinja path and the OS paths to match. Consequently, we'll:
    #   + CD to the template folder
    #   + Set Jinja's path to '.'
    #
    #  In order to build our files to the correct folder(s), we'll use an
    # absolute path for the target folder (project_dir)
    project_dir, output_directory_created = _create_project_dir(
        template_dir, context, output_dir, env, overwrite_if_exists
    )
    logger.debug('Project directory is %s', project_dir)

    # if we created the output directory, then it's ok to remove it
    # if rendering fails
    delete_project_on_failure = output_directory_created and not keep_project_on_failure

    if accept_hooks:
        run_hook_from_repo_dir(
            repo_dir, 'pre_gen_project', project_dir, context, delete_project_on_failure
        )

    with work_in(template_dir):
        env.loader = FileSystemLoader(['.', '../templates'])

        for root, dirs, files in os.walk('.'):
            # We must separate the two types of dirs into different lists.
            # The reason is that we don't want ``os.walk`` to go through the
            # unrendered directories, since they will just be copied.
            copy_dirs, render_dirs = _split_copy_only_dirs(root, dirs, context)

            for copy_dir in copy_dirs:
                _copy_dir_without_render(root, copy_dir, project_dir, env, context)

            # We mutate ``dirs``, because we only want to go through these dirs
            # recursively
            dirs[:] = render_dirs
            for render_dir in dirs:
                _create_rendered_dir(
                    root,
                    render_dir,
                    project_dir=project_dir,
                    output_dir=output_dir,
                    env=env,
                    context=context,
                    overwrite_if_exists=overwrite_if_exists,
                    delete_project_on_failure=delete_project_on_failure,
                )

            for filename in sorted(files):
                _process_template_file(
                    root,
                    filename,
                    project_dir=project_dir,
                    env=env,
                    context=context,
                    skip_if_file_exists=skip_if_file_exists,
                    delete_project_on_failure=delete_project_on_failure,
                )

    if accept_hooks:
        run_hook_from_repo_dir(
            repo_dir,
            'post_gen_project',
            project_dir,
            context,
            delete_project_on_failure,
        )

    return project_dir
```

## Refactorizaciones aplicadas

- **Replace Loop with Pipeline** (`is_copy_only_path`): el bucle `for` con `return True` anidado dentro de un `try` se sustituyó por `any(...)`. El `try/except KeyError` ahora solo rodea el acceso a `_copy_without_render`, que es de donde puede salir el `KeyError`. Así queda explícito qué se protege y desaparece el `return False` duplicado.

- **Extract Function** (`apply_overwrites_to_context` → `_apply_multichoice_overwrite`, `_apply_choice_overwrite`, `_convert_overwrite_to_bool`): cada tipo de variable (multi-choice, choice y booleana) tiene su propia función con su validación y su mensaje de error. El cuerpo principal queda como un despacho por tipo fácil de seguir. Los mensajes y excepciones (`ValueError`, encadenado desde `InvalidResponse`) se mantienen idénticos.

- **Replace Nested Conditional with Guard Clauses / Consolidate Conditional** (`apply_overwrites_to_context`): la rama `list` usaba `continue` dentro de un `if` seguido de otro `if/else`. Se convirtió en una cadena `if/elif/else` equivalente.

- **Remove Dead Code** (`apply_overwrites_to_context`): se eliminó `context[variable] = context_value` tras la llamada recursiva. `context_value` ya es el mismo objeto almacenado en `context[variable]` y se modifica in situ, así que la reasignación no tenía efecto.

- **Extract Function** (`generate_context` → `_load_context_file`, `_context_key_from_file_name`):
  - La carga del JSON con su traducción a `ContextDecodingException` queda aislada.
  - El cálculo de la clave del contexto también.
  - Se eliminó la variable intermedia `json_exc_message` (**Inline Variable**). `f"{e}"` equivale a `str(e)`.
  - El `warnings.warn` se mantiene en `generate_context` para no alterar la ubicación atribuida al aviso.

- **Rename Variable** (`generate_context`): `obj` pasó a ser `template_context`, que describe su contenido.

- **Extract Function** (`generate_file` → `_render_template_file`, `_determine_newline`):
  - El renderizado con el ajuste de `TemplateSyntaxError.translated` queda en su propia función.
  - La determinación del salto de línea (configurado o detectado) también.
  - `generate_file` se lee ahora como una secuencia de pasos de alto nivel, con el mismo orden de operaciones y los mismos mensajes de log.

- **Extract Function / Remove Duplicated Code** (`_copy_file_with_permissions`): el par `shutil.copyfile` + `shutil.copymode` estaba repetido en `generate_file` (ficheros binarios) y en `generate_files` (ficheros copy-only). Ahora está en una sola función.

- **Rename Variable** (`generate_file`, `generate_files`):
  - `fh` → `outfile_handle`, `rd` → `file_handle`, `tmpl` → `template`.
  - `infile_fwd_slashes` → `template_name`.
  - `d` → `dirname`/`render_dir`, `f` → `filename`.
  - `_dir` → `relative_dir`.
  - En el bucle de subdirectorios ya no se reutiliza `unrendered_dir`, que antes ocultaba la variable del directorio raíz.

- **Simplify Conditional Expression** (`render_and_create_dir`):
  - `if not dirname or dirname == ""` se redujo a `if not dirname`. La segunda condición era redundante.
  - El `if/else` anidado sobre la existencia del directorio se aplanó en `if/elif/else`, con el caso de creación primero.

- **Extract Function** (`generate_files` → `_create_project_dir`, `_split_copy_only_dirs`, `_copy_dir_without_render`, `_create_rendered_dir`, `_copy_file_without_render`, `_process_template_file`):
  - La función original mezclaba varios niveles de abstracción: creación del directorio raíz, clasificación de directorios, copia sin render, creación de subdirectorios y procesado de ficheros.
  - Ahora el cuerpo de `os.walk` delega cada paso en una función con nombre descriptivo.
  - Se conservan las llamadas a `generate_file`, `render_and_create_dir`, `run_hook_from_repo_dir` y `rmtree` con los mismos argumentos posicionales, el mismo orden, los mismos mensajes y el mismo manejo de `UndefinedError`.
  - La mutación `dirs[:] = render_dirs` sigue en el bucle principal, porque es la que controla el recorrido de `os.walk`.

- **Keyword-only parameters en helpers privados** (`_create_rendered_dir`, `_process_template_file`): estas funciones reciben varios flags booleanos del mismo tipo. Al forzar argumentos con nombre se evitan confusiones de orden en las llamadas.

- **Sin cambios** en `_run_hook_from_repo_dir` (envoltorio obsoleto) ni en las firmas públicas: `is_copy_only_path`, `apply_overwrites_to_context`, `generate_context`, `generate_file`, `render_and_create_dir` y `generate_files`. Tampoco cambian los nombres importados a nivel de módulo (`is_binary`, `rmtree`, `find_template`, `run_hook_from_repo_dir`…), de modo que los `mock.patch` existentes en los tests siguen funcionando.