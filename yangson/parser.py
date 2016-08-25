"""Simple parser class."""

import re
from typing import Any, Callable, List, Mapping, Optional, Tuple
from .exceptions import YangsonException
from .typealiases import *

# Local type aliases
State = int
ParseTable = List[
    Tuple[
        Callable[[Optional[str]], State],
        Mapping[str, Callable[[], State]]
    ]
]

class Parser:

    """Simple parser.

    Instance variables:

    * input: input string
    * offset: current position in the input string
    """

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
        self.offset = 0 # type: int

    def __str__(self):
        """Return string representation of the parser state."""
        return self.input[:self.offset] + "§" + self.input[self.offset:]

    def remaining(self) -> str:
        """Return the remaining part of the input string."""
        res = self.input[self.offset:]
        self.offset = len(self.input)
        return res

    def at_end(self) -> bool:
        """Return ``True`` if at end of input."""
        return self.offset >= len(self.input)

    def peek(self) -> str:
        """Peek at the next character.

        Raises:
            EndOfInput: If past the end of `self.input`.
        """
        try:
            return self.input[self.offset]
        except IndexError:
            raise EndOfInput(self)

    def char(self, c: str) -> None:
        """Parse the specified character."""
        if self.peek() == c:
            self.offset += 1
        else:
            raise UnexpectedInput(self, "char " + c)

    def test_string(self, string: str) -> bool:
        """Test whether `string` comes next."""
        if self.input.startswith(string, self.offset):
            self.offset += len(string)
            return True
        return False

    def one_of(self, chset: str) -> str:
        """Parse one character form the specified set."""
        res = self.peek()
        if res in chset:
            self.offset += 1
            return res
        raise UnexpectedInput(self, "one of " + chset)

    def up_to(self, c: str) -> str:
        """Return segment terminated by a character."""
        end = self.input.find(c, self.offset)
        if end < 0:
            raise EndOfInput(self)
        res = self.input[self.offset:end]
        self.offset = end + 1
        return res

    def scan(self, ptab: ParseTable, init: State = 0) -> State:
        """Simple stateful scanner.

        Args:
            ptab: Transition table (DFA with possible side-effects).
            init: Initial state.

        Raises:
            EndOfInput: If past the end of `self.input`.
        """
        state = init
        while True:
            (owise, disp) = ptab[state]
            ch = self.peek()
            state = disp[ch]() if ch in disp else owise(ch)
            if state < 0:
                return state
            self.offset += 1

    def line_column(self) -> Tuple[int, int]:
        """Return line and column coordinates."""
        l = self.input.count("\n", 0, self.offset)
        c = (self.offset if l == 0 else
             self.offset - self.input.rfind("\n", 0, self.offset) - 1)
        return (l + 1, c)

    def match_regex(self, regex, required: bool = False,
                    meaning: str = "") -> str:
        """Match a regular expression and advance the parser.

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

    def unsigned_integer(self) -> int:
        """Parse unsigned integer."""
        return int(self.match_regex(self.uint_re, True, "unsigned integer"))

    def unsigned_float(self) -> float:
        """Parse unsigned number (exponential notation is not permitted)."""
        return float(self.match_regex(self.ufloat_re, True, "unsigned float"))

    def yang_identifier(self) -> YangIdentifier:
        """Parse YANG identifier.

        Raises:
            UnexpectedInput: If no syntactically correct keyword is found.
        """
        return self.match_regex(self.ident_re, True, "YANG identifier")

    def name_opt_prefix(self) -> Tuple[YangIdentifier, Optional[YangIdentifier]]:
        """Parse name with an optional prefix."""
        i1 = self.yang_identifier()
        try:
            next = self.peek()
        except EndOfInput:
            return (i1, None)
        if next != ":": return (i1, None)
        self.offset += 1
        return (self.yang_identifier(), i1)

    def skip_ws(self) -> bool:
        """Skip optional whitespace."""
        return len(self.match_regex(self.ws_re)) > 0

    def adv_skip_ws(self) -> bool:
        """Advance offset and skip optional whitespace."""
        self.offset += 1
        return self.skip_ws()

class ParserException(YangsonException):
    """Base exception class for the parser of YANG modules."""

    def __init__(self, p: Parser) -> None:
        self.parser = p

    def __str__(self) -> str:
        """Print line and column number.
        """
        if "\n" in self.parser.input:
            return "line {0}, column {1}".format(*self.parser.line_column())
        return str(self.parser)

class EndOfInput(ParserException):
    """End of input."""
    pass

class UnexpectedInput(ParserException):
    """Unexpected input."""

    def __init__(self, p: Parser, expected: str = None) -> None:
        super().__init__(p)
        self.expected = expected

    def __str__(self) -> str:
        """Add info about expected input if available."""
        ex = "" if self.expected is None else ": expected " + self.expected
        return super().__str__() + ex
