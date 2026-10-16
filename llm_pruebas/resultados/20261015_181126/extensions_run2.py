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


_DEFAULT_DATETIME_FORMAT = '%Y-%m-%d'


class JsonifyExtension(Extension):
    """Jinja2 extension to convert a Python object to JSON."""

    def __init__(self, environment: Environment) -> None:
        """Initialize the extension with the given environment."""
        super().__init__(environment)

        def jsonify(obj: Any, indent: int = 4) -> str:
            return json.dumps(obj, sort_keys=True, indent=indent)

        environment.filters['jsonify'] = jsonify


class RandomStringExtension(Extension):
    """Jinja2 extension to create a random string."""

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension Constructor."""
        super().__init__(environment)

        def random_ascii_string(length: int, punctuation: bool = False) -> str:
            corpus = (
                string.ascii_letters + string.punctuation
                if punctuation
                else string.ascii_letters
            )
            return "".join(choice(corpus) for _ in range(length))

        environment.globals.update(random_ascii_string=random_ascii_string)


class SlugifyExtension(Extension):
    """Jinja2 Extension to slugify string."""

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension constructor."""
        super().__init__(environment)

        def slugify(
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
                entities=entities,
                decimal=decimal,
                hexadecimal=hexadecimal,
                max_length=max_length,
                word_boundary=word_boundary,
                separator=separator,
                save_order=save_order,
                stopwords=stopwords,
                regex_pattern=regex_pattern,
                lowercase=lowercase,
                replacements=replacements,
                allow_unicode=allow_unicode,
            )

        environment.filters['slugify'] = slugify


class UUIDExtension(Extension):
    """Jinja2 Extension to generate uuid4 string."""

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension constructor."""
        super().__init__(environment)

        def uuid4() -> str:
            """Generate UUID4."""
            return str(uuid.uuid4())

        environment.globals.update(uuid4=uuid4)


class TimeExtension(Extension):
    """Jinja2 Extension for dates and times."""

    tags = {'now'}

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension constructor."""
        super().__init__(environment)

        environment.extend(datetime_format=_DEFAULT_DATETIME_FORMAT)

    # --- Runtime callbacks (invoked from the compiled template) ---------------

    def _datetime(
        self,
        timezone: str,
        operator: str,
        offset: str,
        datetime_format: str | None,
    ) -> str:
        now = arrow.now(timezone)
        shifted = now.shift(**self._parse_shift_params(operator, offset))
        return shifted.strftime(self._resolve_datetime_format(datetime_format))

    def _now(self, timezone: str, datetime_format: str | None) -> str:
        datetime_format = self._resolve_datetime_format(datetime_format)
        return arrow.now(timezone).strftime(datetime_format)

    # --- Helpers ---------------------------------------------------------------

    @staticmethod
    def _parse_shift_params(operator: str, offset: str) -> dict[str, float]:
        """Turn an offset like ``'days=1, hours=2'`` into ``arrow.shift`` kwargs.

        The operator (``'+'`` or ``'-'``) is applied as the sign of every value.
        """
        shift_params = {}
        for param in offset.split(','):
            interval, value = param.split('=')
            shift_params[interval.strip()] = float(operator + value.strip())
        return shift_params

    def _resolve_datetime_format(self, datetime_format: str | None) -> str:
        """Return the given format, or the environment's default if it is None."""
        if datetime_format is None:
            return self.environment.datetime_format  # type: ignore[attr-defined]
        return datetime_format

    # --- Template parsing ------------------------------------------------------

    def parse(self, parser: Parser) -> nodes.Output:
        """Parse datetime template and add datetime value."""
        lineno = next(parser.stream).lineno

        node = parser.parse_expression()
        datetime_format = self._parse_datetime_format(parser)

        call_method = self._build_call_method(node, datetime_format, lineno)
        return nodes.Output([call_method], lineno=lineno)

    @staticmethod
    def _parse_datetime_format(parser: Parser) -> nodes.Expr:
        """Parse the optional ``, '<format>'`` argument of the ``now`` tag."""
        if parser.stream.skip_if('comma'):
            return parser.parse_expression()
        return nodes.Const(None)

    def _build_call_method(
        self, node: nodes.Expr, datetime_format: nodes.Expr, lineno: int
    ) -> nodes.Call:
        """Build the call to ``_datetime`` (with offset) or ``_now`` (without)."""
        if isinstance(node, (nodes.Add, nodes.Sub)):
            operator = '+' if isinstance(node, nodes.Add) else '-'
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
