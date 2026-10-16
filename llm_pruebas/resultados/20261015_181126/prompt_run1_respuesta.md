```python
"""Functions for prompting the user for project info."""

from __future__ import annotations

import json
import os
import re
import sys
from collections import OrderedDict
from collections.abc import Iterator
from itertools import starmap
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias

from jinja2.exceptions import UndefinedError
from rich.prompt import Confirm, InvalidResponse, Prompt, PromptBase

from cookiecutter.exceptions import UndefinedVariableInTemplate
from cookiecutter.utils import create_env_with_context, rmtree

if TYPE_CHECKING:
    from jinja2 import Environment


DEFAULT_DISPLAY = 'default'


def _human_readable_question(var_name: str, prompts: dict[str, Any] | None) -> str:
    """Return the human-readable prompt for ``var_name`` if any, else its name."""
    if prompts and var_name in prompts and prompts[var_name]:
        return prompts[var_name]
    return var_name


def _format_choice_line(index: str, label: Any) -> str:
    """Format one line of the list of options shown to the user."""
    return f"    [bold magenta]{index}[/] - [bold]{label}[/]"


def read_user_variable(var_name: str, default_value, prompts=None, prefix: str = ""):
    """Prompt user for variable and return the entered value or given default.

    :param str var_name: Variable of the context to query the user
    :param default_value: Value that will be returned if no input happens
    """
    question = _human_readable_question(var_name, prompts)

    while True:
        variable = Prompt.ask(f"{prefix}{question}", default=default_value)
        if variable is not None:
            return variable


class YesNoPrompt(Confirm):
    """A prompt that returns a boolean for yes/no questions."""

    yes_choices = ["1", "true", "t", "yes", "y", "on"]
    no_choices = ["0", "false", "f", "no", "n", "off"]

    def process_response(self, value: str) -> bool:
        """Convert choices to a bool."""
        value = value.strip().lower()
        if value in self.yes_choices:
            return True
        if value in self.no_choices:
            return False
        raise InvalidResponse(self.validate_error_message)


def read_user_yes_no(var_name, default_value, prompts=None, prefix: str = ""):
    """Prompt the user to reply with 'yes' or 'no' (or equivalent values).

    - These input values will be converted to ``True``:
      "1", "true", "t", "yes", "y", "on"
    - These input values will be converted to ``False``:
      "0", "false", "f", "no", "n", "off"

    Actual parsing done by :func:`prompt`; Check this function codebase change in
    case of unexpected behaviour.

    :param str question: Question to the user
    :param default_value: Value that will be returned if no input happens
    """
    question = _human_readable_question(var_name, prompts)
    return YesNoPrompt.ask(f"{prefix}{question}", default=default_value)


def read_repo_password(question: str) -> str:
    """Prompt the user to enter a password.

    :param question: Question to the user
    """
    return Prompt.ask(question, password=True)


def read_user_choice(var_name: str, options: list, prompts=None, prefix: str = ""):
    """Prompt the user to choose from several options for the given variable.

    The first item will be returned if no input happens.

    :param var_name: Variable as specified in the context
    :param list options: Sequence of options that are available to select from
    :return: Exactly one item of ``options`` that has been chosen by the user
    """
    if not options:
        raise ValueError

    choice_map = OrderedDict((f'{i}', value) for i, value in enumerate(options, 1))
    choices = choice_map.keys()

    question = f"Select {var_name}"
    choice_lines: Iterator[str] = starmap(_format_choice_line, choice_map.items())

    # Handle if human-readable prompt is provided
    if prompts and var_name in prompts:
        var_prompts = prompts[var_name]
        if isinstance(var_prompts, str):
            question = var_prompts
        else:
            if "__prompt__" in var_prompts:
                question = var_prompts["__prompt__"]
            choice_lines = (
                _format_choice_line(
                    index, var_prompts[option] if option in var_prompts else option
                )
                for index, option in choice_map.items()
            )

    prompt = '\n'.join(
        (
            f"{prefix}{question}",
            "\n".join(choice_lines),
            "    Choose from",
        )
    )

    user_choice = Prompt.ask(prompt, choices=list(choices), default=next(iter(choices)))
    return choice_map[user_choice]


def process_json(user_value: str):
    """Load user-supplied value as a JSON dict.

    :param user_value: User-supplied value to load as a JSON dict
    """
    try:
        user_dict = json.loads(user_value, object_pairs_hook=OrderedDict)
    except Exception as error:
        # Leave it up to click to ask the user again
        msg = 'Unable to decode to JSON.'
        raise InvalidResponse(msg) from error

    if not isinstance(user_dict, dict):
        # Leave it up to click to ask the user again
        msg = 'Requires JSON dict.'
        raise InvalidResponse(msg)

    return user_dict


class JsonPrompt(PromptBase[dict]):
    """A prompt that returns a dict from JSON string."""

    default = None
    response_type = dict
    validate_error_message = "[prompt.invalid]  Please enter a valid JSON string"

    @staticmethod
    def process_response(value: str) -> dict[str, Any]:
        """Convert choices to a dict."""
        return process_json(value)


def read_user_dict(var_name: str, default_value, prompts=None, prefix: str = ""):
    """Prompt the user to provide a dictionary of data.

    :param var_name: Variable as specified in the context
    :param default_value: Value that will be returned if no input is provided
    :return: A Python dictionary to use in the context.
    """
    if not isinstance(default_value, dict):
        raise TypeError

    question = _human_readable_question(var_name, prompts)
    return JsonPrompt.ask(
        f"{prefix}{question} [cyan bold]({DEFAULT_DISPLAY})[/]",
        default=default_value,
        show_default=False,
    )


_Raw: TypeAlias = bool | dict["_Raw", "_Raw"] | list["_Raw"] | str | None


def render_variable(
    env: Environment,
    raw: _Raw,
    cookiecutter_dict: dict[str, Any],
) -> str:
    """Render the next variable to be displayed in the user prompt.

    Inside the prompting taken from the cookiecutter.json file, this renders
    the next variable. For example, if a project_name is "Peanut Butter
    Cookie", the repo_name could be be rendered with:

        `{{ cookiecutter.project_name.replace(" ", "_") }}`.

    This is then presented to the user as the default.

    :param Environment env: A Jinja2 Environment object.
    :param raw: The next value to be prompted for by the user.
    :param dict cookiecutter_dict: The current context as it's gradually
        being populated with variables.
    :return: The rendered value for the default variable.
    """
    if raw is None or isinstance(raw, bool):
        return raw
    if isinstance(raw, dict):
        return {
            render_variable(env, k, cookiecutter_dict): render_variable(
                env, v, cookiecutter_dict
            )
            for k, v in raw.items()
        }
    if isinstance(raw, list):
        return [render_variable(env, v, cookiecutter_dict) for v in raw]
    if not isinstance(raw, str):
        raw = str(raw)

    return env.from_string(raw).render(cookiecutter=cookiecutter_dict)


def _prompts_from_options(options: dict) -> dict:
    """Process template options and return friendly prompt information."""
    prompts = {"__prompt__": "Select a template"}
    for option_key, option_value in options.items():
        title = str(option_value.get("title", option_key))
        description = option_value.get("description", option_key)
        label = title if title == description else f"{title} ({description})"
        prompts[option_key] = label
    return prompts


def prompt_choice_for_template(
    key: str, options: dict, no_input: bool
) -> OrderedDict[str, Any]:
    """Prompt user with a set of options to choose from.

    :param no_input: Do not prompt for user input and return the first available option.
    """
    opts = list(options.keys())
    prompts = {"templates": _prompts_from_options(options)}
    return opts[0] if no_input else read_user_choice(key, opts, prompts, "")


def prompt_choice_for_config(
    cookiecutter_dict: dict[str, Any],
    env: Environment,
    key: str,
    options,
    no_input: bool,
    prompts=None,
    prefix: str = "",
) -> OrderedDict[str, Any] | str:
    """Prompt user with a set of options to choose from.

    :param no_input: Do not prompt for user input and return the first available option.
    """
    rendered_options = [render_variable(env, raw, cookiecutter_dict) for raw in options]
    if no_input:
        if not rendered_options:
            msg = "The list of choices is empty"
            raise ValueError(msg)
        return rendered_options[0]
    return read_user_choice(key, rendered_options, prompts, prefix)


def _is_private_variable(key: str) -> bool:
    """Return True for ``_var`` keys, which are copied as-is (never rendered)."""
    return key.startswith('_') and not key.startswith('__')


def _is_private_rendered_variable(key: str) -> bool:
    """Return True for ``__var`` keys, which are rendered but never prompted."""
    return key.startswith('__')


def _progress_prefix(position: int, total: int) -> str:
    """Return the ``[position/total]`` prefix shown before each question."""
    return f"  [dim][{position}/{total}][/] "


def _undefined_variable_error(
    key: str, error: UndefinedError, context: dict[str, Any]
) -> UndefinedVariableInTemplate:
    """Build the exception raised when a variable cannot be rendered."""
    msg = f"Unable to render variable '{key}'"
    return UndefinedVariableInTemplate(msg, error, context)


def _prompt_for_simple_variable(
    cookiecutter_dict: dict[str, Any],
    env: Environment,
    key: str,
    raw: Any,
    no_input: bool,
    prompts: dict[str, Any],
    prefix: str,
) -> Any:
    """Return the value of a choice, boolean or regular (non-dict) variable."""
    if isinstance(raw, list):
        # We are dealing with a choice variable
        return prompt_choice_for_config(
            cookiecutter_dict, env, key, raw, no_input, prompts, prefix
        )
    if isinstance(raw, bool):
        # We are dealing with a boolean variable
        if no_input:
            return render_variable(env, raw, cookiecutter_dict)
        return read_user_yes_no(key, raw, prompts, prefix)

    # We are dealing with a regular variable
    value = render_variable(env, raw, cookiecutter_dict)
    if not no_input:
        value = read_user_variable(key, value, prompts, prefix)
    return value


def _prompt_for_dict_variable(
    cookiecutter_dict: dict[str, Any],
    env: Environment,
    key: str,
    raw: dict[str, Any],
    no_input: bool,
    prompts: dict[str, Any],
    prefix: str,
) -> Any:
    """Return the value of a dict variable (private rendered ones are not asked)."""
    value = render_variable(env, raw, cookiecutter_dict)
    if not no_input and not _is_private_rendered_variable(key):
        value = read_user_dict(key, value, prompts, prefix)
    return value


def prompt_for_config(
    context: dict[str, Any], no_input: bool = False
) -> OrderedDict[str, Any]:
    """Prompt user to enter a new config.

    :param dict context: Source for field names and sample values.
    :param no_input: Do not prompt for user input and use only values from context.
    """
    cookiecutter_dict = OrderedDict([])
    env = create_env_with_context(context)
    variables = context['cookiecutter']
    prompts = variables.pop('__prompts__', {})

    position = 0
    total = sum(1 for key in variables if not key.startswith('_'))

    # First pass: Handle simple and raw variables, plus choices.
    # These must be done first because the dictionaries keys and
    # values might refer to them.
    for key, raw in variables.items():
        if _is_private_variable(key):
            cookiecutter_dict[key] = raw
            continue
        if _is_private_rendered_variable(key):
            cookiecutter_dict[key] = render_variable(env, raw, cookiecutter_dict)
            continue
        if isinstance(raw, dict):
            # Dictionaries are handled in the second pass
            continue

        position += 1
        prefix = _progress_prefix(position, total)
        try:
            cookiecutter_dict[key] = _prompt_for_simple_variable(
                cookiecutter_dict, env, key, raw, no_input, prompts, prefix
            )
        except UndefinedError as err:
            raise _undefined_variable_error(key, err, context) from err

    # Second pass; handle the dictionaries.
    for key, raw in variables.items():
        # Skip private type dicts not to be rendered.
        if _is_private_variable(key) or not isinstance(raw, dict):
            continue

        position += 1
        prefix = _progress_prefix(position, total)
        try:
            cookiecutter_dict[key] = _prompt_for_dict_variable(
                cookiecutter_dict, env, key, raw, no_input, prompts, prefix
            )
        except UndefinedError as err:
            raise _undefined_variable_error(key, err, context) from err

    return cookiecutter_dict


def choose_nested_template(
    context: dict[str, Any], repo_dir: Path | str, no_input: bool = False
) -> str:
    """Prompt user to select the nested template to use.

    :param context: Source for field names and sample values.
    :param repo_dir: Repository directory.
    :param no_input: Do not prompt for user input and use only values from context.
    :returns: Path to the selected template.
    """
    env = create_env_with_context(context)
    prompts = context['cookiecutter'].pop('__prompts__', {})
    templates = context['cookiecutter'].get("templates", {})

    if templates:
        selected = prompt_choice_for_template("templates", templates, no_input)
        template = templates[selected]["path"]
    else:
        # Old style: list of choices formatted as "Name (relative/path)"
        legacy_choices = context['cookiecutter'].get("template", [])
        selected = prompt_choice_for_config(
            OrderedDict([]), env, "template", legacy_choices, no_input, prompts, ""
        )
        template = re.search(r'\((.+)\)', selected).group(1)

    if not template or Path(template).is_absolute():
        msg = "Illegal template path"
        raise ValueError(msg)

    template_path = (Path(repo_dir).resolve() / template).resolve()
    # Return path as string
    return f"{template_path}"


def _delete_path(path: Path | str) -> None:
    """Delete ``path``, whether it is a directory or a file."""
    if os.path.isdir(path):
        rmtree(path)
    else:
        os.remove(path)


def prompt_and_delete(path: Path | str, no_input: bool = False) -> bool:
    """
    Ask user if it's okay to delete the previously-downloaded file/directory.

    If yes, delete it. If no, checks to see if the old version should be
    reused. If yes, it's reused; otherwise, Cookiecutter exits.

    :param path: Previously downloaded zipfile.
    :param no_input: Suppress prompt to delete repo and just delete it.
    :return: True if the content was deleted
    """
    # Suppress prompt if called via API
    if no_input:
        ok_to_delete = True
    else:
        question = (
            f"You've downloaded {path} before. Is it okay to delete and re-download it?"
        )
        ok_to_delete = read_user_yes_no(question, 'yes')

    if ok_to_delete:
        _delete_path(path)
        return True

    ok_to_reuse = read_user_yes_no("Do you want to re-use the existing version?", 'yes')
    if ok_to_reuse:
        return False

    sys.exit()
```

## Refactorizaciones aplicadas

- **Extract Function** → `_human_readable_question(var_name, prompts)`. La usan `read_user_variable`, `read_user_yes_no` y `read_user_dict`. **Motivo:** la expresión condicional que elige la pregunta legible estaba copiada tres veces. Ahora existe un único punto de verdad.

- **Extract Function** → `_format_choice_line(index, label)`. La usa `read_user_choice`. **Motivo:** el formato Rich de cada opción aparecía dos veces, una como `str.format` en `starmap` y otra como f-string. Ambas producen exactamente la misma cadena. Se mantienen la evaluación perezosa (generador) y la semántica `x[p] if p in x else p`.

- **Extract Variable** → `var_prompts = prompts[var_name]`, en `read_user_choice`. **Motivo:** evita repetir `prompts[var_name]` en cada acceso y aclara de qué estructura se lee.

- **Replace Loop Exit with Return** (variante de *Remove Control Flag*), en `read_user_variable`. **Motivo:** se sustituye `break` + `return` posterior por un `return` dentro del bucle. Es más directo y equivalente.

- **Extract Function** → `_is_private_variable(key)` y `_is_private_rendered_variable(key)`. Las usan `prompt_for_config` y `_prompt_for_dict_variable`. **Motivo:** las condiciones `key.startswith('_') and not key.startswith('__')` y `key.startswith('__')` se repetían y no expresaban su intención: variable copiada tal cual frente a variable renderizada pero no preguntada.

- **Extract Function** → `_progress_prefix(position, total)`. **Motivo:** el prefijo `[n/total]` se construía igual en ambas pasadas.

- **Extract Function** → `_undefined_variable_error(key, err, context)`. **Motivo:** la creación de `UndefinedVariableInTemplate` estaba duplicada. Se conserva `raise ... from err` en el llamador, así que el encadenamiento de excepciones no cambia.

- **Extract Function** (descomposición de función larga) → `_prompt_for_simple_variable` y `_prompt_for_dict_variable`, extraídas de `prompt_for_config`. **Motivo:**
  - La función principal mezclaba el recorrido en dos pasadas con la lógica concreta de cada tipo de variable (elección, booleana, regular, diccionario).
  - Ahora `prompt_for_config` solo orquesta.
  - El bloque `try` sigue cubriendo exactamente las mismas operaciones.
  - El renderizado de las claves `__` en la primera pasada sigue fuera del `try`, como en el original.

- **Replace Nested Conditional with Guard Clauses**, en ambas pasadas de `prompt_for_config`. **Motivo:**
  - En la primera pasada, los diccionarios se saltan con `continue` en lugar de atravesar un `try` que no hacía nada.
  - En la segunda pasada, el filtro `not isinstance(raw, dict)` se adelanta como cláusula de guarda.
  - El conteo de posiciones, incluido el incremento para diccionarios `__`, es idéntico.

- **Rename Variable**, en `prompt_for_config`:
  - `all_prompts` → `variables`
  - `count` → `position`
  - `size` → `total`

  **Motivo:** los nombres originales eran engañosos. `all_prompts` no contenía *prompts*, sino las variables del contexto.

- **Replace Temp with Query / Inline Variable**: `visible_prompts` (lista usada solo para su `len`) pasa a ser `sum(...)`. **Motivo:** elimina una variable intermedia innecesaria. Se sigue calculando después del `pop('__prompts__')`.

- **Simplify Conditional Expression**, en `choose_nested_template`. **Motivo:** `Path(template) if template else None` seguido de `not (template and not template.is_absolute())` pasa a ser `not template or Path(template).is_absolute()`. Es equivalente porque un `Path` siempre es verdadero.

- **Inline Variable / Rename Variable**, en `choose_nested_template`:
  - Se eliminan `cookiecutter_dict`, `prefix` y la reasignación de `key`/`config`.
  - Se usan nombres explícitos (`templates`, `legacy_choices`, `selected`).
  - Se sigue creando el entorno Jinja antes del `pop`, para conservar el orden de los posibles errores.

  **Motivo:** la reutilización de `key`/`config` para dos formatos distintos dificultaba la lectura.

- **Extract Function** → `_delete_path(path)`, en `prompt_and_delete`. **Motivo:** separa el detalle de borrado (directorio o fichero) de la lógica de diálogo con el usuario.

- **Inline Variable** → `template` en `render_variable`. **Motivo:** la variable temporal no aportaba claridad.

- **Slide Statements** → constante `DEFAULT_DISPLAY`. **Motivo:** se mueve al inicio del módulo, junto a las importaciones, para que las constantes públicas sean fáciles de localizar. Su valor y su nombre no cambian.