# Copyright © 2016, 2017 CZ.NIC, z. s. p. o.
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

"""Classes representing "rich" YANG constraints.
"""

import decimal
import re
from typing import Callable, List, Optional, Tuple, Union
from pyxb.utils.xmlre import XMLToPython

from .exceptions import InvalidArgument
from .typealiases import *
from .xpathast import Expr

# Type aliases
Number = Union[int, decimal.Decimal]
Interval = List[Number]

class Constraint:
    """Abstract class representing "rich" YANG constraints."""

    def __init__(self, error_tag: str = None, error_message: str = None):
        """Initialize the class instance."""
        self.error_tag = error_tag
        self.error_message = error_message

class Intervals(Constraint):
    """Abstract class representing a sequence of intervals."""

    def __init__(self, intervals: List[Interval], parser: Callable[[str], Number],
                     error_tag: str = None, error_message: str = None):
        """Initialize the class instance."""
        super().__init__(error_tag, error_message)
        self.intervals = intervals
        self.parser = parser

    def __contains__(self, value: Number):
        """Return ``True`` if the receiver contains the value."""
        for r in self.intervals:
            if len(r) == 1:
                if r[0] == value: return True
            elif r[0] <= value <= r[1]: return True
        return False

    def parse(self, text: str) -> Number:
        res = self.parser(text)
        if res is None:
            raise ValueError
        return res

    def combine_with(self, expr: str, error_tag: str = None,
                         error_message: str = None) -> None:
        """Combine the receiver with new intervals.

        Args:
            expr: "range" or "length" expression.
            error_tag: error tag of the new expression.
            error_message: error message for the new expression.
        """
        to_num = lambda xs: [ self.parse(x) for x in xs ]
        lo = self.intervals[0][0]
        hi = self.intervals[-1][-1]
        parts = [ p.strip() for p in expr.split("|") ]
        ran = [ [ i.strip() for i in p.split("..") ] for p in parts ]
        if ran[0][0] != "min":
            lo = self.parse(ran[0][0])
        if ran[-1][-1] != "max":
            hi = self.parse(ran[-1][-1])
        self.intervals = (
            [[lo, hi]] if len(ran) == 1 else [[lo, self.parse(ran[0][-1])]] +
            [ to_num(r) for r in ran[1:-1] ] + [[self.parse(ran[-1][0]), hi]])
        if error_tag:
            self.error_tag = error_tag
        if error_message:
            self.error_message = error_message

class Ranges(Intervals):
    """Class representing a sequence of numeric ranges."""
    def __init__(self, intervals: Intervals, parser: Callable[[str], Number],
                     error_tag: str = None, error_message: str = "not in range"):
        """Initialize the class instance."""
        super().__init__(intervals, parser, error_tag, error_message)


class Lengths(Intervals):
    """Class representing a sequence of ranges for string length."""

    def __init__(self, intervals: List[int], parser: Callable[[str], Number] = int,
                     error_tag: str = None, error_message: str = "invalid length"):
        """Initialize the class instance."""
        super().__init__(intervals, parser, error_tag, error_message)

class Pattern(Constraint):
    """Class representing regular expression pattern."""

    def __init__(self, pattern: str, invert_match: bool = False,
                     error_tag: str = None,
                     error_message: str = "pattern not matched"):
        """Initialize the class instance."""
        super().__init__(error_tag, error_message)
        self.invert_match = invert_match
        try:
            self.regex = re.compile(XMLToPython(pattern))
        except:
            raise InvalidArgument(pattern) from None

class Must(Constraint):
    """Class representing the constraint specified by a **must** statement."""

    def __init__(self, expression: Expr, error_tag: str = None,
                     error_message: str = None):
        """Initialize the class instance."""
        super().__init__(
            error_tag if error_tag else "must-violation", error_message)
        self.expression = expression
