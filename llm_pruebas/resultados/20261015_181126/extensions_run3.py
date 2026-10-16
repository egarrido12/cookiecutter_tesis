"""Jinja2 extensions."""

from __future__ import annotations

import json
import string
import uuid
from collections.abc import Iterable
from secrets import choice
from typing import TYPE_CHECKING, Any

import arrow
from jinja2 import Environment, nodes
from jinja2.ext import Extension
from slugify import slugify as pyslugify
from slugify.slugify import DEFAULT_SEPARATOR

if TYPE_CHECKING:
    import re

    from jinja2.parser import Parser


DEFAULT_DATETIME_FORMAT = '%Y-%m-%d'

# Binary expressions accepted by the ``{% now %}`` tag to shift the current
# date, paired with the sign applied to the offset values.
_OFFSET_OPERATORS: tuple[tuple[type[nodes.BinExpr], str], ...] = (
    (nodes.Add, '+'),
    (nodes.Sub, '-'),
)


def _jsonify(obj: Any, indent: int = 4) -> str:
    """Serialize ``obj`` to a JSON string with sorted keys."""
    return json.dumps(obj, sort_keys=True, indent=indent)


def _random_ascii_string(length: int, punctuation: bool = False) -> str:
    """Return a random string of ASCII letters, optionally with punctuation."""
    corpus = string.ascii_letters
    if punctuation:
        corpus += string.punctuation
    return "".join(choice(corpus) for _ in range(length))


def _slugify(
    value: str,
    entities: bool = True,
    decimal: bool = True,
    hexadecimal: bool = True,
    max_length: int = 0,
    word_boundary: bool = False,
    separator: str = DEFAULT_SEPARATOR,
    save_order: bool = False,
    stopwords: Iterable[str] = (),
    regex_pattern: re.Pattern[str] | str | None = None,
    lowercase: bool = True,
    replacements: Iterable[Iterable[str]] = (),
    allow_unicode: bool = False,
) -> str:
    """Slugifies the value."""
    return pyslugify(
        value,
        entities,
        decimal,
        hexadecimal,
        max_length,
        word_boundary,
        separator,
        save_order,
        stopwords,
        regex_pattern,
        lowercase,
        replacements,
        allow_unicode,
    )


def _uuid4() -> str:
    """Generate UUID4."""
    return str(uuid.uuid4())


def _parse_shift_params(operator: str, offset: str) -> dict[str, float]:
    """Convert an offset such as ``'days=1, hours=2'`` into ``arrow`` shift params.

    The ``operator`` (``'+'`` or ``'-'``) is prepended to every value so the
    shift goes forwards or backwards in time.
    """
    shift_params = {}
    for param in offset.split(','):
        interval, value = param.split('=')
        shift_params[interval.strip()] = float(operator + value.strip())
    return shift_params


class JsonifyExtension(Extension):
    """Jinja2 extension to convert a Python object to JSON."""

    def __init__(self, environment: Environment) -> None:
        """Initialize the extension with the given environment."""
        super().__init__(environment)
        environment.filters['jsonify'] = _jsonify


class RandomStringExtension(Extension):
    """Jinja2 extension to create a random string."""

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension Constructor."""
        super().__init__(environment)
        environment.globals['random_ascii_string'] = _random_ascii_string


class SlugifyExtension(Extension):
    """Jinja2 Extension to slugify string."""

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension constructor."""
        super().__init__(environment)
        environment.filters['slugify'] = _slugify


class UUIDExtension(Extension):
    """Jinja2 Extension to generate uuid4 string."""

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension constructor."""
        super().__init__(environment)
        environment.globals['uuid4'] = _uuid4


class TimeExtension(Extension):
    """Jinja2 Extension for dates and times."""

    tags = {'now'}

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension constructor."""
        super().__init__(environment)

        environment.extend(datetime_format=DEFAULT_DATETIME_FORMAT)

    def _resolve_datetime_format(self, datetime_format: str | None) -> str:
        """Return ``datetime_format`` or, if missing, the environment's default."""
        if datetime_format is None:
            return self.environment.datetime_format  # type: ignore[attr-defined]
        return datetime_format

    def _datetime(
        self,
        timezone: str,
        operator: str,
        offset: str,
        datetime_format: str | None,
    ) -> str:
        now = arrow.now(timezone)
        shifted = now.shift(**_parse_shift_params(operator, offset))
        return shifted.strftime(self._resolve_datetime_format(datetime_format))

    def _now(self, timezone: str, datetime_format: str | None) -> str:
        datetime_format = self._resolve_datetime_format(datetime_format)
        return arrow.now(timezone).strftime(datetime_format)

    @staticmethod
    def _parse_datetime_format(parser: Parser) -> nodes.Expr:
        """Parse the optional ``, '<format>'`` argument of the ``now`` tag."""
        if parser.stream.skip_if('comma'):
            return parser.parse_expression()
        return nodes.Const(None)

    def _build_call(
        self, node: nodes.Expr, datetime_format: nodes.Expr, lineno: int
    ) -> nodes.Call:
        """Build the call to ``_datetime`` (with offset) or ``_now`` (without)."""
        for node_type, operator in _OFFSET_OPERATORS:
            if isinstance(node, node_type):
                return self.call_method(
                    '_datetime',
                    [node.left, nodes.Const(operator), node.right, datetime_format],
                    lineno=lineno,
                )
        return self.call_method(
            '_now',
            [node, datetime_format],
            lineno=lineno,
        )

    def parse(self, parser: Parser) -> nodes.Output:
        """Parse datetime template and add datetime value."""
        lineno = next(parser.stream).lineno

        node = parser.parse_expression()
        datetime_format = self._parse_datetime_format(parser)

        call_method = self._build_call(node, datetime_format, lineno)
        return nodes.Output([call_method], lineno=lineno)
