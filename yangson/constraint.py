# Copyright © 2016–2023 CZ.NIC, z. s. p. o.
#
# This file is part of Yangson.
#
# Yangson is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Yangson is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with Yangson.  If not, see <http://www.gnu.org/licenses/>.

"""Annotated YANG constraints with custom error tags and error messages.

This module implements the following classes:

* Constraint: Abstract class representing annotated YANG constraints.
* Intervals: Class representing a sequence of numeric intervals.
* Pattern: Class representing regular expression pattern.
* Must: Class representing the constraint specified by a "must" statement.
"""
import decimal
import re
from typing import Callable, Optional, Union
from elementpath import RegexError, translate_pattern

from .exceptions import InvalidArgument
from .xpathast import Expr

# Type aliases
Number = Union[int, decimal.Decimal]
"""Union of numeric classes appearing in interval constraints."""

Interval = list[Number]
"""Numeric interval consisting either of one number or a pair of bounds."""


class Constraint:
    """Abstract class representing annotated YANG constraints."""

    def __init__(self: "Constraint", error_tag: Optional[str], error_message: Optional[str]):
        """Initialize the class instance."""
        self.error_tag = error_tag
        self.error_message = error_message


class Intervals(Constraint):
    """Class representing a sequence of numeric intervals."""

    def __init__(self: "Intervals", intervals: list[Interval],
                 parser: Callable[[str], Optional[Number]] = None,
                 error_tag: str = None, error_message: str = None):
        """Initialize the class instance."""
        def _pint(x):                     # default parser
            try:
                return int(x)
            except ValueError:
                return None
        super().__init__(error_tag, error_message)
        self.intervals = intervals
        self.parser = parser if parser else _pint

    def __contains__(self: "Intervals", value: Number):
        """Return ``True`` if the receiver contains the value."""
        for r in self.intervals:
            if len(r) == 1:
                if r[0] == value:
                    return True
            elif r[0] <= value <= r[1]:
                return True
        return False

    def __str__(self: "Intervals") -> str:
        """Return string representation of the receiver."""
        return " | ".join([f"{r[0]!s}..{r[-1]!s}" if len(r) > 1 else str(r[0])
                           for r in self.intervals])

    def restrict_with(self: "Intervals", expr: str, error_tag: str = None,
                      error_message: str = None) -> None:
        """Combine the receiver with new intervals.

        Args:
            expr: "range" or "length" expression.
            error_tag: error tag of the new expression.
            error_message: error message for the new expression.

        Raises:
            InvalidArgument: If parsing of `expr` fails.
        """
        def parse(x: str) -> Number:
            res = self.parser(x)
            if res is None:
                raise InvalidArgument(expr)
            return res

        def simpl(rng: list[Number]) -> list[Number]:
            return ([rng[0]] if rng[0] == rng[1] else rng)

        def to_num(xs): return [parse(x) for x in xs]
        lo = self.intervals[0][0]
        hi = self.intervals[-1][-1]
        ran = []
        for p in [p.strip() for p in expr.split("|")]:
            r = [i.strip() for i in p.split("..")]
            if len(r) > 2:
                raise InvalidArgument(expr)
            ran.append(r)
        if ran[0][0] != "min":
            lo = parse(ran[0][0])
        if ran[-1][-1] != "max":
            hi = parse(ran[-1][-1])
        self.intervals = (
            [simpl([lo, hi])] if len(ran) == 1 else (
                [simpl([lo, parse(ran[0][-1])])] +
                [to_num(r) for r in ran[1:-1]] +
                [simpl([parse(ran[-1][0]), hi])]))
        if error_tag:
            self.error_tag = error_tag
        if error_message:
            self.error_message = error_message


class Pattern(Constraint):
    """Class representing regular expression pattern."""

    def __init__(self: "Pattern", pattern: str, invert_match: bool = False,
                 error_tag: str = None,
                 error_message: str = None):
        """Initialize the class instance."""
        super().__init__(error_tag,
                         error_message if error_message else f"pattern '{pattern}'")
        self.pattern = pattern
        self.invert_match = invert_match
        try:
            self.regex = re.compile(translate_pattern(
                pattern, back_references=False,
                lazy_quantifiers=False, anchors=False))
        except RegexError:
            raise InvalidArgument(pattern) from None


class Must(Constraint):
    """Class representing the constraint specified by a "must" statement."""

    def __init__(self: "Must", expression: Expr, error_tag: str = None,
                 error_message: str = None):
        """Initialize the class instance."""
        super().__init__(
            error_tag if error_tag else "must-violation", error_message)
        self.expression = expression
