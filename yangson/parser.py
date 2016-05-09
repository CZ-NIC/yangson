"""Simple parser class."""

import re
from typing import Callable, List, Mapping, Optional, Tuple
from .constants import ident_re, YangsonException

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

    def __init__(self, inp: str) -> None:
        """Initialize the class instance.

        :param inp: input string
        """
        self.input = inp # type: str
        self.offset = 0 # type: int

    def peek(self) -> str:
        """Peek at the next character.

        :raises EndOfInput: if past the end of `self.input`
        """
        try:
            return self.input[self.offset]
        except IndexError:
            raise EndOfInput(self)

    def scan(self, ptab: ParseTable) -> None:
        """Simple stateful scanner.

        :param ptab: transition table (DFA with possible side-effects).
        :raises EndOfInput: if past the end of `self.input`
        """
        state = 0 # type: State
        while True:
            (owise, disp) = ptab[state]
            ch = self.peek()
            state = disp[ch]() if ch in disp else owise(ch)
            if state < 0:
                break
            self.offset += 1

    def line_column(self) -> Tuple[int, int]:
        """Return line and column coordinates corresponding to `self.offset`."""
        l = self.input.count("\n", 0, self.offset)
        c = (self.offset if l == 0 else
             self.offset - self.input.rfind("\n", 0, self.offset) - 1)
        return (l + 1, c)
        
    def yang_identifier(self) -> str:
        """Parse YANG identifier.

        :raises UnexpectedInput: if no syntactically correct keyword is found
        """
        mo = ident_re.match(self.input, self.offset)
        if mo is None:
            raise UnexpectedInput(self, "YANG identifier")
        self.offset = mo.end()
        return mo.group()

class ParserException(YangsonException):
    """Base exception class for the parser of YANG modules."""

    def __init__(self, p: Parser) -> None:
        self.parser = p

    def __str__(self) -> str:
        """Print line and column number.
        """
        return "line {0}, column {1}".format(*self.parser.line_column())

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
