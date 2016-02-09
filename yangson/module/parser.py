from typing import Callable, List, Mapping, Optional, Tuple
from yangson.exception import YangsonException
from .statement import Statement

# Type aliases
Offset = int
State = int
ParseTable = List[
    Tuple[
        Callable[[Optional[str]], State],
        Mapping[str, Callable[[], State]]
    ]
]

class Parser(object):

    """Parser of YANG modules.

    Instance variables:

    * text: input string

    * offset: current position in the input string
    """

    unescape_map = { "n" : "\n", "t": "\t", '"': '"',
                     "\\": "\\" } # type: Mapping[str,str]
    """Map for translating escape sequences to characters."""
    
    def __init__(self, inp: str) -> None:
        """Initialize the instance.

        :param inp: input string
        """
        self.input = inp # type: str
        self.offset = 0 # type: Offset

    @staticmethod
    def unescape(text: str) -> str:
        """Replace escape sequence with corresponding characters.

        :param text: text to unescape
        """
        chop = text.split("\\", 1)
        return (chop[0] if len(chop) == 1
                else chop[0] + Parser.unescape_map[chop[1][0]] +
                Parser.unescape(chop[1][1:]))

    def _peek(self) -> str:
        """Peek at the next character.

        :param move: indicates whether `self.offset` is to be advanced
        :raises EndOfInput: if past the end of `self.input`
        """
        try:
            return self.input[self.offset]
        except IndexError:
            raise EndOfInput(self)

    def _scan(self, ptab: ParseTable) -> None:
        """Simple stateful scanner.

        :param ptab: transition table (DFA with possible side-effects).
        :raises EndOfInput: if past the end of `self.input`
        """
        state = 0 # type: State
        while True:
            (owise, disp) = ptab[state]
            ch = self._peek()
            state = disp[ch]() if ch in disp else owise(ch)
            if state < 0:
                break
            self.offset += 1

    def line_column(self) -> Tuple[int, int]:
        """Return line and column coordinates corresponding to `self.offset`.
        """
        l = self.input.count("\n", 0, self.offset)
        c = (self.offset if l == 0 else
             self.offset - self.input.rfind("\n", 0, self.offset) - 1)
        return (l + 1, c)
        
    def opt_separator(self) -> None:
        """Parse an optional separator.

        :raises EndOfInput: if past the end of `self.input`
        """
        def back_break(c):
            self.offset -= 1
            return -1
        self._scan(
            [(lambda c: -1, { " ": lambda: 0,
                              "\t": lambda: 0,
                              "\n": lambda: 0,
                              "\r": lambda: 1,
                              "/": lambda: 2 }),
             (back_break, { "\n": lambda: 0 }),
             (back_break, { "/": lambda: 3,
                        "*": lambda: 4 }),
             (lambda c: -1 if c is None else 3, { "\n": lambda: 0 }),
             (lambda c: 4, { "*": lambda: 5 }),
             (lambda c: 4, { "/": lambda: 0,
                             "*": lambda: 5 })])

    def separator(self) -> None:
        """Parse a mandatory separator.

        :raises EndOfInput: if past the end of `self.input`
        :raises UnexpectedInput: if no separator is found
        """
        start = self.offset
        self.opt_separator()
        if start == self.offset: raise UnexpectedInput(self, "separator")

    def keyword(self) -> Tuple[Optional[str], str]:
        """Parse a YANG statement keyword.

        :raises EndOfInput: if past the end of `self.input`
        :raises UnexpectedInput: if no syntactically correct keyword is found
        """
        self._extension = False
        fst = lambda c: "a" <= c <= "z" or "A" <= c <= "Z" or c == "_"
        def car(c):
            if fst(c): return 1
            raise UnexpectedInput(self, "ASCII letter or underline")
        def cdr(c):
            if fst(c) or c == "-" or "0" < c < "9" or c == ".":
                return 1
            else:
                return -1
        def colon():
            if self._extension:
                raise UnexpectedInput(self)
            self._extension = True
            return 0
        start = self.offset
        self._scan([(car, {}), (cdr, { ":" : colon })])
        kw = self.input[start:self.offset]
        return kw.split(":") if self._extension else [None, kw]

    def statement(self) -> Statement:
        """Parse YANG statement.

        :raises EndOfInput: if past the end of `self.input`
        :raises UnexpectedInput: if no syntactically correct statement is found
        """
        pref,kw = self.keyword()
        self.opt_separator()
        next = self._peek()
        if next == ";":
            arg = None
            sub = False # type: bool
        elif next == "{":
            arg = None
            sub = True
        else:
            self._arg = ""
            sub = self.argument()
            arg = self._arg
        self.offset += 1
        if sub:
            subst = self.substatements()
            return Statement(kw, arg, subst, pref)
        return Statement(kw, arg, pref=pref)

    def argument(self) -> bool:
        """Parse statement argument.

        Return ``True`` if the argument is followed by block of substatements.
        """
        next = self._peek()
        if next == "'":
            quoted = True
            self.sq_argument()
        elif next == '"':
            quoted = True
            self.dq_argument()
        elif self._arg == "":
            quoted = False
            self.unq_argument()
        else:
            raise UnexpectedInput(self, "single or double quote")
        self.opt_separator()
        next = self._peek()
        if next == ";":
            return False
        if next == "{":
            return True
        elif quoted and next == "+":
            self.offset += 1
            self.opt_separator();
            return self.argument()
        else:
            raise UnexpectedInput(self, "';', '{'" +
                                  (" or '+'" if quoted else ""))

    def sq_argument(self) -> str:
        """Parse single-quoted argument.

        :raises EndOfInput: if past the end of `self.input`
        """
        self.offset += 1
        start = self.offset
        self._scan([(lambda c: 0, { "'": lambda: -1 })])
        self._arg += self.input[start:self.offset]
        self.offset += 1

    def dq_argument(self) -> str:
        """Parse double-quoted argument.

        :raises EndOfInput: if past the end of `self.input`
        """
        def escape():
            self._escape = True
            return 1
        self._escape = False                 # any escaped chars?
        self.offset += 1
        start = self.offset
        self._scan([(lambda c: 0, { '"': lambda: -1,
                                    '\\': escape }),
                    (lambda c: 0, {})])
        self._arg += (self.unescape(self.input[start:self.offset])
                      if self._escape else self.input[start:self.offset])
        self.offset += 1

    def unq_argument(self) -> str:
        """Parse unquoted argument.

        :raises EndOfInput: if past the end of `self.input`
        """
        def comm_start():
            self.offset -= 1
            return -1
        start = self.offset
        self._scan([(lambda c: 0, { ";": lambda: -1,
                                  " ": lambda: -1,
                                  "\t": lambda: -1,
                                  "\r": lambda: -1,
                                  "\n": lambda: -1,
                                  "{": lambda: -1,
                                  '/': lambda: 1 }),
                    (lambda c: 0, { "/": comm_start,
                                    "*": comm_start })])
        self._arg = self.input[start:self.offset]

    def substatements(self) -> List[Statement]:
        """Parse substatements.

        :raises EndOfInput: if past the end of `self.input`
        """
        res = []
        self.opt_separator()
        while self._peek() != "}":
            res.append(self.statement())
            self.opt_separator()
        self.offset += 1
        return res

    def parse_module(self) -> Statement:
        """Parse a complete YANG module or submodule.

        :raises EndOfInput: if past the end of `self.input`
        :raises UnexpectedInput: if top-level statement isn't ``(sub)module``
        """
        self.opt_separator()
        start = self.offset
        res = self.statement()
        if res.keyword not in ["module", "submodule"]:
            self.offset = start
            raise UnexpectedInput(self, "'module' or 'submodule'")
        try:
            self.opt_separator()
        except EndOfInput:
            return res
        raise UnexpectedInput(self, "end of input")

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
        super(UnexpectedInput, self).__init__(p)
        self.expected = expected

    def __str__(self) -> str:
        """Add info about expected input if available."""
        ex = "" if self.expected is None else ": expected " + self.expected
        return super(UnexpectedInput, self).__str__() + ex

def from_file(fp: str) -> Statement:
    """Parse a module or submodule read from a file.

    :param fp: file path
    """
    with open(fp, encoding='utf-8') as infile:
        p = Parser(infile.read())
    return p.parse_module()
