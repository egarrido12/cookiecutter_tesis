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


def _validate_multichoice_overwrite(
    variable: str, choices: list[Any], overwrite: list[Any]
) -> None:
    """Ensure every value in ``overwrite`` is a valid choice for ``variable``."""
    if not set(overwrite).issubset(set(choices)):
        msg = (
            f"{overwrite} provided for multi-choice variable "
            f"{variable}, but valid choices are {choices}"
        )
        raise ValueError(msg)


def _set_choice_as_default(variable: str, choices: list[Any], overwrite: Any) -> None:
    """Move ``overwrite`` to the first position of ``choices`` (in place).

    The first item of a choice variable is its default value,
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
                # We are dealing with a multichoice variable
                _validate_multichoice_overwrite(variable, context_value, overwrite)
                context[variable] = overwrite
            else:
                # We are dealing with a choice variable
                _set_choice_as_default(variable, context_value, overwrite)
        elif isinstance(context_value, dict) and isinstance(overwrite, dict):
            # Partially overwrite some keys in original dict
            apply_overwrites_to_context(
                context_value, overwrite, in_dictionary_variable=True
            )
            context[variable] = context_value
        elif isinstance(context_value, bool) and isinstance(overwrite, str):
            # We are dealing with a boolean variable
            context[variable] = _convert_overwrite_to_bool(variable, overwrite)
        else:
            # Simply overwrite the value for this variable
            context[variable] = overwrite


def _load_context_file(context_file: str) -> Any:
    """Load the JSON context file, preserving key order.

    JSON decoding errors are re-raised as a more friendly
    ``ContextDecodingException``.
    """
    try:
        with open(context_file, encoding='utf-8') as file_handle:
            return json.load(file_handle, object_pairs_hook=OrderedDict)
    except ValueError as e:
        full_fpath = os.path.abspath(context_file)
        json_exc_message = str(e)
        our_exc_message = (
            f"JSON decoding error while loading '{full_fpath}'. "
            f"Decoding error details: '{json_exc_message}'"
        )
        raise ContextDecodingException(our_exc_message) from e


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
    template_variables = _load_context_file(context_file)

    # Add the Python object to the context dictionary, keyed by the file stem
    file_name = os.path.split(context_file)[1]
    file_stem = file_name.split('.')[0]
    context[file_stem] = template_variables

    # Overwrite context variable defaults with the default context from the
    # user's global config, if available
    if default_context:
        try:
            apply_overwrites_to_context(template_variables, default_context)
        except ValueError as error:
            warnings.warn(f"Invalid default received: {error}")
    if extra_context:
        apply_overwrites_to_context(template_variables, extra_context)

    logger.debug('Context generated is %s', context)
    return context


def _render_output_path(
    project_dir: str, template_path: str, context: dict[str, Any], env: Environment
) -> str:
    """Render ``template_path`` and join it to ``project_dir``."""
    rendered_path = env.from_string(template_path).render(**context)
    return os.path.join(project_dir, rendered_path)


def _copy_file_with_permissions(source: str, destination: str) -> None:
    """Copy file contents and permission bits from ``source`` to ``destination``."""
    shutil.copyfile(source, destination)
    shutil.copymode(source, destination)


def _get_template(env: Environment, infile: str) -> Any:
    """Load the Jinja template for ``infile`` with verbose syntax errors."""
    # Force fwd slashes on Windows for get_template
    # This is a by-design Jinja issue
    infile_fwd_slashes = infile.replace(os.path.sep, '/')
    try:
        return env.get_template(infile_fwd_slashes)
    except TemplateSyntaxError as exception:
        # Disable translated so that printed exception contains verbose
        # information about syntax error location
        exception.translated = False
        raise


def _get_newline(infile: str, context: dict[str, Any]) -> str | None:
    """Return the newline to write the rendered file with.

    Use `_new_lines` from context, if configured. Otherwise detect the
    newline used by the original file.
    """
    configured_newline = context['cookiecutter'].get('_new_lines', False)
    if configured_newline:
        logger.debug('Using configured newline character %s', repr(configured_newline))
        return configured_newline

    # Note that newlines can be a tuple if file contains mixed line endings.
    # In this case, we pick the first line ending we detected.
    with open(infile, encoding='utf-8') as rd:
        rd.readline()  # Read only the first line to load a 'newlines' value.
    newline = rd.newlines[0] if isinstance(rd.newlines, tuple) else rd.newlines
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
    outfile = _render_output_path(project_dir, infile, context, env)

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

    rendered_file = _get_template(env, infile).render(**context)
    newline = _get_newline(infile, context)

    logger.debug('Writing contents to file %s', outfile)

    with open(outfile, 'w', encoding='utf-8', newline=newline) as fh:
        fh.write(rendered_file)

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
    template_dir: Path,
    context: dict[str, Any],
    output_dir: Path | str,
    env: Environment,
    overwrite_if_exists: bool,
) -> tuple[Path, bool]:
    """Render and create the root project directory from the template dir."""
    unrendered_dir = os.path.split(template_dir)[1]
    try:
        return render_and_create_dir(
            unrendered_dir, context, output_dir, env, overwrite_if_exists
        )
    except UndefinedError as err:
        msg = f"Unable to create project directory '{unrendered_dir}'"
        raise UndefinedVariableInTemplate(msg, err, context) from err


def _split_copy_and_render_dirs(
    root: str, dirs: list[str], context: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Split ``dirs`` into dirs to copy as-is and dirs to render.

    The reason for separating them is that we don't want ``os.walk`` to go
    through the unrendered directories, since they will just be copied.
    """
    copy_dirs = []
    render_dirs = []

    for dirname in sorted(dirs):
        # We check the full path, because that's how it can be
        # specified in the ``_copy_without_render`` setting, but
        # we store just the dir name
        dir_path = os.path.normpath(os.path.join(root, dirname))
        if is_copy_only_path(dir_path, context):
            logger.debug('Found copy only path %s', dirname)
            copy_dirs.append(dirname)
        else:
            render_dirs.append(dirname)

    return copy_dirs, render_dirs


def _copy_dir_without_render(
    root: str,
    copy_dir: str,
    project_dir: str,
    context: dict[str, Any],
    env: Environment,
) -> None:
    """Copy a copy-only directory into the project, rendering only its path."""
    indir = os.path.normpath(os.path.join(root, copy_dir))
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
    project_dir: str,
    context: dict[str, Any],
    output_dir: Path | str,
    env: Environment,
    overwrite_if_exists: bool,
    delete_project_on_failure: bool,
) -> None:
    """Render and create a sub-directory of the project."""
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
    infile: str, project_dir: str, context: dict[str, Any], env: Environment
) -> None:
    """Copy a copy-only file into the project, rendering only its path."""
    outfile = _render_output_path(project_dir, infile, context, env)
    logger.debug('Copying file %s to %s without rendering', infile, outfile)
    _copy_file_with_permissions(infile, outfile)


def _generate_or_copy_file(
    infile: str,
    project_dir: str,
    context: dict[str, Any],
    env: Environment,
    skip_if_file_exists: bool,
    delete_project_on_failure: bool,
) -> None:
    """Copy ``infile`` as-is if it is copy-only, otherwise render it."""
    if is_copy_only_path(infile, context):
        _copy_file_without_render(infile, project_dir, context, env)
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

    created_project_dir, output_directory_created = _create_project_dir(
        template_dir, context, output_dir, env, overwrite_if_exists
    )

    # We want the Jinja path and the OS paths to match. Consequently, we'll:
    #   + CD to the template folder
    #   + Set Jinja's path to '.'
    #
    #  In order to build our files to the correct folder(s), we'll use an
    # absolute path for the target folder (project_dir)
    project_dir = os.path.abspath(created_project_dir)
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
            copy_dirs, render_dirs = _split_copy_and_render_dirs(root, dirs, context)

            for copy_dir in copy_dirs:
                _copy_dir_without_render(root, copy_dir, project_dir, context, env)

            # We mutate ``dirs``, because we only want to go through these dirs
            # recursively
            dirs[:] = render_dirs
            for dirname in dirs:
                _create_rendered_dir(
                    root,
                    dirname,
                    project_dir,
                    context,
                    output_dir,
                    env,
                    overwrite_if_exists,
                    delete_project_on_failure,
                )

            for file_name in sorted(files):
                infile = os.path.normpath(os.path.join(root, file_name))
                _generate_or_copy_file(
                    infile,
                    project_dir,
                    context,
                    env,
                    skip_if_file_exists,
                    delete_project_on_failure,
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

- **Replace Loop with Pipeline** — `is_copy_only_path`: el bucle `for` con `return True` anidado dentro de un `try` pasa a ser `any(...)`. El `try/except KeyError` queda limitado a la lectura de `_copy_without_render`. Así se separa "obtener los patrones" de "comprobar si alguno coincide" y se elimina el `return False` duplicado.

- **Extract Function** — `apply_overwrites_to_context` → `_validate_multichoice_overwrite`, `_set_choice_as_default`, `_convert_overwrite_to_bool`: cada tipo de variable (multichoice, choice, booleana) tiene ahora su propia validación o conversión y su mensaje de error, que se mantiene idéntico.

- **Consolidate Conditional Expression / Replace Nested Conditional with Guard Clauses** — `apply_overwrites_to_context`: la rama de listas sustituye el `continue` intermedio y los `if/else` anidados por una única cadena `if/elif/else`. Las condiciones y los efectos son los mismos, pero el flujo se lee de una vez.

- **Extract Function** — `generate_context` → `_load_context_file`: aísla la lectura del JSON y la traducción de `ValueError` a `ContextDecodingException`, de modo que `generate_context` solo construye y sobrescribe el contexto.

- **Rename Variable** — `obj` → `template_variables` en `generate_context`: el nombre genérico pasa a describir qué contiene.

- **Extract Function** — `generate_file` → `_render_output_path`, `_get_template`, `_get_newline`, `_copy_file_with_permissions`. Cada paso (calcular la ruta de salida, cargar la plantilla con errores de sintaxis detallados, decidir el salto de línea, copiar con permisos) tiene ahora nombre propio. `_render_output_path` y `_copy_file_with_permissions` se reutilizan también al copiar ficheros sin renderizar, lo que elimina código duplicado. Se mantiene el orden original: se renderiza el contenido antes de detectar el salto de línea.

- **Remove Dead Code / Simplify Conditional** — `render_and_create_dir`: `if not dirname or dirname == ""` pasa a `if not dirname`, porque la segunda condición es redundante.

- **Inline Variable** — `name_tmpl` en `render_and_create_dir`: era una variable temporal de un solo uso.

- **Replace Nested Conditional with Guard Clauses** — `render_and_create_dir`: la creación del directorio y los dos casos de "ya existe" quedan en una única cadena `if/elif/else` sin anidamiento.

- **Extract Function** — `generate_files` → `_create_project_dir`, `_split_copy_and_render_dirs`, `_copy_dir_without_render`, `_create_rendered_dir`, `_copy_file_without_render`, `_generate_or_copy_file`. La función original mezclaba en un solo cuerpo la creación del directorio raíz, la clasificación de directorios, la copia, el renderizado y el manejo de errores. Ahora `generate_files` describe el algoritmo a alto nivel. La mutación `dirs[:] = render_dirs`, necesaria para que `os.walk` no descienda a los directorios copiados, permanece en `generate_files`.

- **Split Variable** — `unrendered_dir` y `project_dir` en `generate_files`:
  - `unrendered_dir` se reutilizaba para dos conceptos distintos (el nombre del directorio plantilla y las rutas de subdirectorios). Ahora cada uno vive en su función.
  - `project_dir` cambiaba de tipo (`Path` → `str`). Ahora se distingue `created_project_dir` (el `Path` devuelto) de `project_dir` (la ruta absoluta en `str`).

- **Rename Variable** — `d` → `dirname`, `f` → `file_name`, `d_` → `dir_path`, `_dir` → `relative_dir`: nombres más descriptivos en lugar de identificadores de una letra o con guion bajo.

- **Sin cambios** en `_run_hook_from_repo_dir`, que está obsoleta y debe conservar exactamente su aviso de deprecación (incluido `stacklevel=2`). Tampoco cambian los nombres ni las firmas de ninguna función pública.