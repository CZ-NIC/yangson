from typing import Callable, List, Mapping, Optional, Tuple
from .statement import Statement

Offset = int
State = int
ParseTable = List[
    Tuple[
        Callable[[Optional[str]], State],
        Mapping[str, Callable[[], State]]
    ]
]

def _anything(c: str) -> State:
    if c is None:
        raise ValueError("unexpected end of input")
    return 0

class Parser(object):

    """Parser of YANG modules.

    Instance variables:

    * text: input string

    * offset: current position in the input string

    * flag: extra boolean flag passed from parsers
    """

    unescape_map = { "n" : "\n", "t": "\t", '"': '"',
                     "\\": "\\" } # type: Mapping[str,str]
    """Map for translating escaped characters to their native form."""
    
    def __init__(self, inp: str) -> None:
        """Initialize the parser with input string `inp`.
        """
        self.input = inp # type: str
        self.offset = 0 # type: Offset
        self.flag = False # type: bool

    @staticmethod
    def unescape(text: str) -> str:
        """Replace escaped characters in `text` with native characters.
        """
        chop = text.split("\\", 1)
        return (chop[0] if len(chop) == 1
                else chop[0] + Parser.unescape_map[chop[1][0]] +
                Parser.unescape(chop[1][1:]))

    def _peek(self) -> Optional[str]:
        """Peek at the next character.
        """
        try:
            return self.input[self.offset]
        except IndexError:
            raise ValueError("end of input")

    def _scan(self, ptab: ParseTable) -> None:
        """Simple stateful scanner."""
        state = 0 # type: State
        while True:
            (owise, disp) = ptab[state]
            ch = self._peek()
            state = disp[ch]() if ch in disp else owise(ch)
            if state < 0:
                break
            self.offset += 1
        
    def opt_separator(self) -> None:
        """Parse optional separator.

        Return total length of the separator string.
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
             (lambda c: 4, { "/": lambda: 0 })])

    def separator(self) -> None:
        """Parse mandatory separator.
        """
        start = self.offset
        self.opt_separator()
        if start == self.offset: raise ValueError("expected separator")

    def keyword(self) -> List[str]:
        """Parse keyword.
        """
        self.flag = False                 # extension?
        fst = lambda c: "a" <= c <= "z" or "A" <= c <= "Z" or c == "_"
        def car(c):
            if fst(c): return 1
            raise ValueError("expected ASCII letter or underline, got " + c)
        def cdr(c):
            if fst(c) or c == "-" or "0" < c < "9" or c == ".":
                return 1
            else:
                return -1
        def colon():
            if self.flag:
                raise ValueError("unexpected character: ':'")
            self.flag = True
            return 0
        start = self.offset
        self._scan([(car, {}), (cdr, { ":" : colon })])
        kw = self.input[start:self.offset]
        return kw.split(":") if self.flag else [None, kw]

    def statement(self) -> Statement:
        """Parse YANG statement.
        """
        pref,kw = self.keyword()
        self.opt_separator()
        next = self._peek()
        if next == ";" or next == "{":
            arg = None # type: Optional[str]
        elif next == "'":
            arg = self.sq_argument()
        elif next == '"':
            arg = self.dq_argument()
        else:
            arg = self.unq_argument()
        self.opt_separator()
        next = self._peek()
        if next == ";":
            self.offset += 1
            return Statement(kw, arg, pref=pref)
        if next == "{":
            self.offset += 1
            subst = self.substatements()
            return Statement(kw, arg, subst, pref)
        raise ValueError("rubbish: " + next)

    def parse_module(self):
        """Parse a complete YANG module or submodule.
        """
        self.opt_separator()
        res = self.statement()
        if res.keyword not in ["module", "submodule"]:
            raise ValueError("missing 'module' or 'submodule'")
        self.opt_separator()
        if self.offset < len(self.input):
            raise ValueError("trailing garbage")
        return res 

    def sq_argument(self) -> str:
        """Parse single-quoted argument.
        """
        self.offset += 1
        start = self.offset
        self._scan([(_anything, { "'": lambda: -1 })])
        res = self.input[start:self.offset]
        self.offset += 1
        return res

    def dq_argument(self) -> str:
        """Parse double-quoted argument.
        """
        def escape():
            self.flag = True
            return 1
        self.flag = False                 # any escaped chars?
        self.offset += 1
        start = self.offset
        self._scan([(_anything, { '"': lambda: -1,
                                  '\\': escape }),
                    (_anything, {})])
        res = (self.unescape(self.input[start:self.offset]) if self.flag
               else self.input[start:self.offset])
        self.offset += 1
        return res

    def unq_argument(self) -> str:
        """Parse unquoted argument.
        """
        def comm_start():
            self.offset -= 1
            return -1
        start = self.offset
        self._scan([(_anything, { ";": lambda: -1,
                                  " ": lambda: -1,
                                  "\t": lambda: -1,
                                  "\r": lambda: -1,
                                  "\n": lambda: -1,
                                  "{": lambda: -1,
                                  '/': lambda: 1 }),
                    (_anything, { "/": comm_start,
                                  "*": comm_start })])
        return self.input[start:self.offset]

    def substatements(self) -> List[Statement]:
        """Parse substatements.
        """
        res = []
        self.opt_separator()
        while self._peek() != "}":
            res.append(self.statement())
            self.opt_separator()
        self.offset += 1
        return res
