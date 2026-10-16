```python
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


_DEFAULT_JSON_INDENT = 4
_DEFAULT_DATETIME_FORMAT = '%Y-%m-%d'


class JsonifyExtension(Extension):
    """Jinja2 extension to convert a Python object to JSON."""

    def __init__(self, environment: Environment) -> None:
        """Initialize the extension with the given environment."""
        super().__init__(environment)

        def jsonify(obj: Any, indent: int = _DEFAULT_JSON_INDENT) -> str:
            return json.dumps(obj, sort_keys=True, indent=indent)

        environment.filters['jsonify'] = jsonify


class RandomStringExtension(Extension):
    """Jinja2 extension to create a random string."""

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension Constructor."""
        super().__init__(environment)

        def random_ascii_string(length: int, punctuation: bool = False) -> str:
            corpus = (
                f'{string.ascii_letters}{string.punctuation}'
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
            # Arguments are passed positionally on purpose: it keeps this
            # wrapper independent of the parameter names used by the
            # installed python-slugify version.
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

    def _resolve_datetime_format(self, datetime_format: str | None) -> str:
        """Return the given format, or the environment default if it is None."""
        if datetime_format is None:
            return self.environment.datetime_format  # type: ignore[attr-defined]
        return datetime_format

    @staticmethod
    def _parse_shift_params(operator: str, offset: str) -> dict[str, float]:
        """Parse an offset like ``'days=1, hours=2'`` into ``arrow`` shift params.

        The operator (``'+'`` or ``'-'``) is applied as the sign of every value.
        """
        shift_params = {}
        for param in offset.split(','):
            interval, value = param.split('=')
            shift_params[interval.strip()] = float(operator + value.strip())
        return shift_params

    def _datetime(
        self,
        timezone: str,
        operator: str,
        offset: str,
        datetime_format: str | None,
    ) -> str:
        current_time = arrow.now(timezone)
        shift_params = self._parse_shift_params(operator, offset)
        shifted_time = current_time.shift(**shift_params)
        return shifted_time.strftime(self._resolve_datetime_format(datetime_format))

    def _now(self, timezone: str, datetime_format: str | None) -> str:
        datetime_format = self._resolve_datetime_format(datetime_format)
        return arrow.now(timezone).strftime(datetime_format)

    @staticmethod
    def _parse_datetime_format(parser: Parser) -> nodes.Expr:
        """Parse the optional ``, '<format>'`` argument of the ``now`` tag."""
        if parser.stream.skip_if('comma'):
            return parser.parse_expression()
        return nodes.Const(None)

    def parse(self, parser: Parser) -> nodes.Output:
        """Parse datetime template and add datetime value."""
        lineno = next(parser.stream).lineno

        node = parser.parse_expression()
        datetime_format = self._parse_datetime_format(parser)

        if isinstance(node, (nodes.Add, nodes.Sub)):
            operator = '+' if isinstance(node, nodes.Add) else '-'
            call_method = self.call_method(
                '_datetime',
                [node.left, nodes.Const(operator), node.right, datetime_format],
                lineno=lineno,
            )
        else:
            call_method = self.call_method(
                '_now',
                [node, datetime_format],
                lineno=lineno,
            )
        return nodes.Output([call_method], lineno=lineno)
```

## Refactorizaciones aplicadas

- **Extract Method** (`TimeExtension._resolve_datetime_format`): la lógica «si `datetime_format` es `None`, usar el formato por defecto del entorno» estaba duplicada en `_datetime` y `_now`. Ahora vive en un único método. En ambos métodos se mantiene el orden original de evaluación: en `_datetime` el formato se resuelve al final y en `_now` al principio.

- **Extract Method** (`TimeExtension._parse_shift_params`): el bucle que convierte el desplazamiento (`'days=1, hours=2'`) en parámetros para `arrow.shift` pasa a un método estático con nombre y docstring propios. Así `_datetime` se lee como una secuencia de pasos: obtener la hora actual, desplazarla y formatearla. Se conservan las mismas excepciones ante desplazamientos mal formados.

- **Extract Method** (`TimeExtension._parse_datetime_format`): el análisis del argumento opcional `, '<formato>'` del tag `now` sale de `parse`, que queda centrado en decidir qué nodo de llamada construir.

- **Consolidate Duplicate Conditional Fragments** (`TimeExtension.parse`): las ramas de `nodes.Add` y `nodes.Sub` eran idénticas salvo por el operador (`'+'` / `'-'`). Se unifican en una sola rama que primero calcula el operador. Se mantiene la comprobación con `isinstance`, con la misma semántica que el original.

- **Rename Variable** (`d` → `current_time` / `shifted_time` en `_datetime`): el nombre de una letra se reasignaba con dos significados distintos. Ahora cada valor tiene un nombre descriptivo.

- **Replace Magic Literal** (`_DEFAULT_DATETIME_FORMAT`, `_DEFAULT_JSON_INDENT`): el formato de fecha por defecto `'%Y-%m-%d'` y la indentación por defecto `4` de `jsonify` pasan a constantes de módulo con nombre. Son privadas (prefijo `_`) para no ampliar la API pública.

- **Substitute Algorithm (simplificación menor)** (`random_ascii_string`): el `if/else` que asignaba `corpus` en dos ramas se sustituye por una expresión condicional equivalente.

- **Sin cambios intencionados**:
  - Los nombres de los métodos `_datetime` y `_now` se conservan, porque `parse` los referencia por cadena mediante `call_method`.
  - Las funciones internas (`jsonify`, `random_ascii_string`, `slugify`, `uuid4`) mantienen sus nombres y se registran con las mismas claves en `filters`/`globals`.
  - En `slugify` se mantiene la llamada posicional a `pyslugify`, porque su primer parámetro no se llama igual que en el wrapper (`text` frente a `value`). Se añade un comentario que explica esta decisión.