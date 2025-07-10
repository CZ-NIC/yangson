import decimal
from .exceptions import InvalidArgument
from .xpathast import Expr
from .schemanode import SchemaNode
from typing import Callable, Optional, Union
import typing

Number = Union[int, decimal.Decimal]
Interval = list[Number]

class Constraint:
    error_tag: Optional[str]
    error_message: Optional[str]
    def __init__(self, error_tag: Optional[str], error_message: Optional[str]) -> None: ...

class Intervals(Constraint):
    @staticmethod
    def default_parser(x: str) -> Optional[Number]: ...
    intervals: list[Interval]
    parser: Callable[[str], Optional[Number]]
    def __init__(self, intervals: list[Interval], parser: Optional[Callable[[str], Optional[Number]]] = None, error_tag: Optional[str] = None, error_message: Optional[str] = None) -> None: ...
    def __contains__(self, value: Number) -> bool: ...
    def restrict_with(self, expr: str, error_tag: Optional[str] = None, error_message: Optional[str] = None) -> None: ...

class Pattern(Constraint):
    pattern: str
    invert_match: bool
    regex: typing.Pattern[str]
    def __init__(self, pattern: str, invert_match: bool = False, error_tag: Optional[str] = None, error_message: Optional[str] = None) -> None: ...

class Must(Constraint):
    expression: Expr
    def __init__(self, expression: Expr, error_tag: Optional[str] = None, error_message: Optional[str] = None) -> None: ...
    def check(self, ctx_root: SchemaNode) -> bool: ...
