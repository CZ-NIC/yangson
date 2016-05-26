"""Simple parser class."""

from typing import Any, Callable, List, Mapping, Optional, Tuple
from .constants import ident_re, ws_re, YangsonException
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

    def parse(self, inp: str) -> Any:
        """Initialize the class instance.

        :param inp: input string
        """
        self.input = inp # type: str
        self.offset = 0 # type: int

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

        :raises EndOfInput: if past the end of `self.input`
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

        :param ptab: transition table (DFA with possible side-effects).
        :param init: initial state
        :raises EndOfInput: if past the end of `self.input`
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

        :param regex: compiled regular expression object
        :param required: this parameter determines what happens if `regex`
                         doesn't match: if it is ``False`` (which is the
                         default), then ``None`` is returned, otherwise
                         an exception is raised
        :param meaning: meaning of `regex` (for use in error messages)
        :raises UnexpectedInput: if no syntactically correct keyword is found
        """
        mo = regex.match(self.input, self.offset)
        if mo:
            self.offset = mo.end()
            return mo.group()
        if required:
            raise UnexpectedInput(self, meaning)
        
    def yang_identifier(self) -> YangIdentifier:
        """Parse YANG identifier.

        :raises UnexpectedInput: if no syntactically correct keyword is found
        """
        return self.match_regex(ident_re, True, "YANG identifier")

    def instance_name(self) -> QualName:
        """Parse instance name."""
        i1 = self.yang_identifier()
        try:
            next = self.peek()
        except EndOfInput:
            return (i1, None)
        if next != ":": return (i1, None)
        self.offset += 1
        return (self.yang_identifier(), i1)

    def skip_ws(self) -> None:
        """Skip optional whitespace."""
        self.match_regex(ws_re)

class ParserException(YangsonException):
    """Base exception class for the parser of YANG modules."""

    def __init__(self, p: Parser) -> None:
        self.parser = p

    def __str__(self) -> str:
        """Print line and column number.
        """
        if "\n" in self.parser.input:
            return "line {0}, column {1}".format(*self.parser.line_column())
        return "position " + str(self.parser.offset)

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
