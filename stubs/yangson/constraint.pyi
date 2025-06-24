import decimal
from .exceptions import InvalidArgument
from .xpathast import Expr
from _typeshed import Incomplete
from typing import Callable, Optional, Union

Number = Union[int, decimal.Decimal]
Interval = list[Number]

class Constraint:
    error_tag: Incomplete
    error_message: Incomplete
    def __init__(self, error_tag: Optional[str], error_message: Optional[str]) -> None: ...

class Intervals(Constraint):
    @staticmethod
    def default_parser(x: str) -> Optional[Number]: ...
    intervals: Incomplete
    parser: Incomplete
    def __init__(self, intervals: list[Interval], parser: Optional[Callable[[str], Optional[Number]]] = None, error_tag: Optional[str] = None, error_message: Optional[str] = None) -> None: ...
    def __contains__(self, value: Number) -> bool: ...
    error_tag: Incomplete
    error_message: Incomplete
    def restrict_with(self, expr: str, error_tag: Optional[str] = None, error_message: Optional[str] = None) -> None: ...

class Pattern(Constraint):
    pattern: Incomplete
    invert_match: Incomplete
    regex: Incomplete
    def __init__(self, pattern: str, invert_match: bool = False, error_tag: Optional[str] = None, error_message: Optional[str] = None) -> None: ...

class Must(Constraint):
    expression: Incomplete
    def __init__(self, expression: Expr, error_tag: Optional[str] = None, error_message: Optional[str] = None) -> None: ...
