"""Functions for prompting the user for project info."""

from __future__ import annotations

import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias

from jinja2.exceptions import UndefinedError
from rich.prompt import Confirm, InvalidResponse, Prompt, PromptBase

from cookiecutter.exceptions import UndefinedVariableInTemplate
from cookiecutter.utils import create_env_with_context, rmtree

if TYPE_CHECKING:
    from jinja2 import Environment


DEFAULT_DISPLAY = 'default'


def _question_for(var_name: str, prompts) -> str:  # type: ignore[no-untyped-def]
    """Return the human-readable question for ``var_name``.

    Falls back to the variable name itself when no (non-empty) prompt
    has been provided for it.
    """
    if prompts and var_name in prompts and prompts[var_name]:
        return prompts[var_name]
    return var_name


def read_user_variable(var_name: str, default_value, prompts=None, prefix: str = ""):
    """Prompt user for variable and return the entered value or given default.

    :param str var_name: Variable of the context to query the user
    :param default_value: Value that will be returned if no input happens
    """
    question = _question_for(var_name, prompts)

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

    Actual parsing done by :class:`YesNoPrompt`; Check this class codebase change
    in case of unexpected behaviour.

    :param str var_name: Variable of the context (or question) to ask the user
    :param default_value: Value that will be returned if no input happens
    """
    question = _question_for(var_name, prompts)
    return YesNoPrompt.ask(f"{prefix}{question}", default=default_value)


def read_repo_password(question: str) -> str:
    """Prompt the user to enter a password.

    :param question: Question to the user
    """
    return Prompt.ask(question, password=True)


def _format_choice_line(index: str, label: Any) -> str:
    """Format a single numbered option of a choice prompt."""
    return f"    [bold magenta]{index}[/] - [bold]{label}[/]"


def _choice_label(option: Any, option_prompts: Any) -> Any:
    """Return the human-readable label of ``option``, or the option itself."""
    if option_prompts is not None and option in option_prompts:
        return option_prompts[option]
    return option


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
    choices = list(choice_map.keys())

    # Handle if human-readable prompt is provided, either as a plain question
    # or as a mapping with an optional question and labels for each option.
    question = f"Select {var_name}"
    option_prompts = None
    if prompts and var_name in prompts:
        if isinstance(prompts[var_name], str):
            question = prompts[var_name]
        else:
            option_prompts = prompts[var_name]
            if "__prompt__" in option_prompts:
                question = option_prompts["__prompt__"]

    choice_lines = (
        _format_choice_line(index, _choice_label(option, option_prompts))
        for index, option in choice_map.items()
    )

    prompt = '\n'.join(
        (
            f"{prefix}{question}",
            "\n".join(choice_lines),
            "    Choose from",
        )
    )

    user_choice = Prompt.ask(prompt, choices=choices, default=choices[0])
    return choice_map[user_choice]


def process_json(user_value: str):
    """Load user-supplied value as a JSON dict.

    :param user_value: User-supplied value to load as a JSON dict
    """
    try:
        user_dict = json.loads(user_value, object_pairs_hook=OrderedDict)
    except Exception as error:
        # Leave it up to the prompt to ask the user again
        msg = 'Unable to decode to JSON.'
        raise InvalidResponse(msg) from error

    if not isinstance(user_dict, dict):
        # Leave it up to the prompt to ask the user again
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

    question = _question_for(var_name, prompts)
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
            render_variable(env, key, cookiecutter_dict): render_variable(
                env, value, cookiecutter_dict
            )
            for key, value in raw.items()
        }
    if isinstance(raw, list):
        return [render_variable(env, value, cookiecutter_dict) for value in raw]
    if not isinstance(raw, str):
        raw = str(raw)

    template = env.from_string(raw)

    return template.render(cookiecutter=cookiecutter_dict)


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
    """Return True for ``_var`` keys: copied verbatim, never rendered nor prompted."""
    return key.startswith('_') and not key.startswith('__')


def _is_render_only_variable(key: str) -> bool:
    """Return True for ``__var`` keys: rendered, but never prompted."""
    return key.startswith('__')


def _count_visible_variables(variables: dict[str, Any]) -> int:
    """Return how many variables are shown to the user (no leading underscore)."""
    return len([key for key in variables if not key.startswith("_")])


def _progress_prefix(count: int, total: int) -> str:
    """Return the ``[count/total]`` prefix displayed before each question."""
    return f"  [dim][{count}/{total}][/] "


def _undefined_variable_error(
    key: str, error: UndefinedError, context: dict[str, Any]
) -> UndefinedVariableInTemplate:
    """Build the exception raised when a variable can not be rendered."""
    msg = f"Unable to render variable '{key}'"
    return UndefinedVariableInTemplate(msg, error, context)


def _prompt_for_simple_variable(
    cookiecutter_dict: dict[str, Any],
    env: Environment,
    key: str,
    raw: Any,
    no_input: bool,
    prompts: Any,
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


def prompt_for_config(
    context: dict[str, Any], no_input: bool = False
) -> OrderedDict[str, Any]:
    """Prompt user to enter a new config.

    :param dict context: Source for field names and sample values.
    :param no_input: Do not prompt for user input and use only values from context.
    """
    cookiecutter_dict = OrderedDict([])
    env = create_env_with_context(context)
    prompts = context['cookiecutter'].pop('__prompts__', {})
    variables = context['cookiecutter']

    count = 0
    total = _count_visible_variables(variables)

    # First pass: Handle simple and raw variables, plus choices.
    # These must be done first because the dictionaries keys and
    # values might refer to them.
    for key, raw in variables.items():
        if _is_private_variable(key):
            cookiecutter_dict[key] = raw
            continue
        if _is_render_only_variable(key):
            # Rendering errors here are intentionally not wrapped.
            cookiecutter_dict[key] = render_variable(env, raw, cookiecutter_dict)
            continue
        if isinstance(raw, dict):
            # Dictionaries are handled in the second pass.
            continue

        count += 1
        prefix = _progress_prefix(count, total)
        try:
            cookiecutter_dict[key] = _prompt_for_simple_variable(
                cookiecutter_dict, env, key, raw, no_input, prompts, prefix
            )
        except UndefinedError as err:
            raise _undefined_variable_error(key, err, context) from err

    # Second pass: handle the dictionaries (including ``__`` ones, which are
    # re-rendered with the complete first-pass values and also advance the
    # progress counter, but are never prompted).
    for key, raw in variables.items():
        if _is_private_variable(key) or not isinstance(raw, dict):
            continue

        count += 1
        prefix = _progress_prefix(count, total)
        try:
            value = render_variable(env, raw, cookiecutter_dict)
            if not no_input and not _is_render_only_variable(key):
                value = read_user_dict(key, value, prompts, prefix)
        except UndefinedError as err:
            raise _undefined_variable_error(key, err, context) from err
        cookiecutter_dict[key] = value

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
        # New style: mapping of template keys to their configuration.
        selected = prompt_choice_for_template("templates", templates, no_input)
        template = templates[selected]["path"]
    else:
        # Old style: list of "Name (path)" strings.
        choices = context['cookiecutter'].get("template", [])
        selected = prompt_choice_for_config(
            OrderedDict([]), env, "template", choices, no_input, prompts, ""
        )
        template = re.search(r'\((.+)\)', selected).group(1)

    if not template or Path(template).is_absolute():
        msg = "Illegal template path"
        raise ValueError(msg)

    template_path = (Path(repo_dir).resolve() / Path(template)).resolve()
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
