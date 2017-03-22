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

"""Simple recursive-descent parser.

This module implements the following class:

* Parser: Recursive-descent parser.
"""

import re
from typing import Any, Callable, List, Dict, Optional, Tuple
from typing.re import Pattern
from .exceptions import EndOfInput, UnexpectedInput
from .typealiases import *

# Local type aliases
TransitionTable = List[Dict[str, Callable[[], int]]]
"""Transition table for a DFA."""

class Parser:

    """Recursive-descent parser with support for YANG syntactic elements."""

    # Regular expressions

    ident_re = re.compile("[a-zA-Z_][a-zA-Z0-9_.-]*")
    """Regular expression for YANG identifier."""

    ws_re = re.compile(r"[ \n\t\r]*")
    """Regular expression for whitespace."""

    _uint = "[0-9]+"
    uint_re = re.compile(_uint)
    """Regular expression for unsigned integer."""

    ufloat_re = re.compile(r"{}(\.{})?|\.{}".format(_uint, _uint, _uint))
    """Regular expression for unsigned float."""

    def __init__(self, text: str):
        """Initialize the class instance.

        Args:
            text: Input text.
        """
        self.input = text
        """Input text for the parser."""
        self.offset = 0 # type: int
        """Current position in the input text."""

    def __str__(self) -> str:
        """Return string representation of the receiver's input text and state."""
        return self.input[:self.offset] + "§" + self.input[self.offset:]

    def adv_skip_ws(self) -> bool:
        """Advance offset and skip optional whitespace."""
        self.offset += 1
        return self.skip_ws()

    def at_end(self) -> bool:
        """Return ``True`` if at end of input."""
        return self.offset >= len(self.input)

    def char(self, c: str) -> None:
        """Parse the specified character.

        Args:
            c: One-character string.

        Raises:
            EndOfInput: If past the end of `self.input`.
            UnexpectedInput: If the next character is different from `c`.
        """
        if self.peek() == c:
            self.offset += 1
        else:
            raise UnexpectedInput(self, "char " + c)

    def dfa(self, ttab: TransitionTable, init: int = 0) -> int:
        """Run a DFA and return the final (negative) state.

        Args:
            ttab: Transition table (with possible side-effects).
            init: Initial state.

        Raises:
            EndOfInput: If past the end of `self.input`.
        """
        state = init
        while True:
            disp = ttab[state]
            ch = self.peek()
            state = disp.get(ch, disp[""])()
            if state < 0:
                return state
            self.offset += 1

    def line_column(self) -> Tuple[int, int]:
        """Return line and column coordinates."""
        l = self.input.count("\n", 0, self.offset)
        c = (self.offset if l == 0 else
             self.offset - self.input.rfind("\n", 0, self.offset) - 1)
        return (l + 1, c)

    def match_regex(self, regex: Pattern, required: bool = False,
                    meaning: str = "") -> str:
        """Parse input based on a regular expression .

        Args:
            regex: Compiled regular expression object.
            required: Should the exception be raised on unexpected input? 
            meaning: Meaning of `regex` (for use in error messages).

        Raises:
            UnexpectedInput: If no syntactically correct keyword is found.
        """
        mo = regex.match(self.input, self.offset)
        if mo:
            self.offset = mo.end()
            return mo.group()
        if required:
            raise UnexpectedInput(self, meaning)

    def one_of(self, chset: str) -> str:
        """Parse one character form the specified set.

        Args:
            chset: string of characters to try as alternatives.

        Returns:
            The character that was actually matched.

        Raises:
            UnexpectedInput: If the next character is not in `chset`.
        """
        res = self.peek()
        if res in chset:
            self.offset += 1
            return res
        raise UnexpectedInput(self, "one of " + chset)

    def peek(self) -> str:
        """Return the next character without advancing offset.

        Raises:
            EndOfInput: If past the end of `self.input`.
        """
        try:
            return self.input[self.offset]
        except IndexError:
            raise EndOfInput(self)

    def prefixed_name(self) -> Tuple[YangIdentifier, Optional[YangIdentifier]]:
        """Parse identifier with an optional colon-separated prefix."""
        i1 = self.yang_identifier()
        try:
            next = self.peek()
        except EndOfInput:
            return (i1, None)
        if next != ":": return (i1, None)
        self.offset += 1
        return (self.yang_identifier(), i1)

    def remaining(self) -> str:
        """Return the remaining part of the input string."""
        res = self.input[self.offset:]
        self.offset = len(self.input)
        return res

    def skip_ws(self) -> bool:
        """Skip optional whitespace."""
        return len(self.match_regex(self.ws_re)) > 0

    def test_string(self, string: str) -> bool:
        """If `string` comes next, return ``True`` and advance offset.

        Args:
            string: string to test
        """
        if self.input.startswith(string, self.offset):
            self.offset += len(string)
            return True
        return False

    def unsigned_integer(self) -> int:
        """Parse and return an unsigned integer."""
        return int(self.match_regex(self.uint_re, True, "unsigned integer"))

    def unsigned_float(self) -> float:
        """Parse and return unsigned floating-point number."""
        return float(self.match_regex(self.ufloat_re, True, "unsigned float"))

    def up_to(self, term: str) -> str:
        """Parse and return segment terminated by the first occurence of a string.

        Args:
            term: Terminating string.

        Raises:
            EndOfInput: If `term` does not occur in the rest of the input text.
        """
        end = self.input.find(term, self.offset)
        if end < 0:
            raise EndOfInput(self)
        res = self.input[self.offset:end]
        self.offset = end + 1
        return res

    def yang_identifier(self) -> YangIdentifier:
        """Parse and return YANG identifier.

        Raises:
            UnexpectedInput: If no syntactically correct keyword is found.
        """
        return self.match_regex(self.ident_re, True, "YANG identifier")
