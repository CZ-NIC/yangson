"""YANG statements."""

from typing import List, Optional, Tuple
from .constants import YangsonException
from .parser import EndOfInput, Parser, UnexpectedInput
from .typealiases import YangIdentifier

class Statement:

    """This class represents a YANG statement.

    Instance variables:

    * keyword: statement keyword,
    * prefix: optional keyword prefix (for extensions),
    * argument: statement argument,
    * superstmt: parent statement,
    * substatements: list of substatements.
    """

    _escape_table = str.maketrans({ '"': '\\"', '\\': '\\\\'})
    """Table for translating characters to their escaped form."""

    def __init__(self,
                 kw: YangIdentifier,
                 arg: Optional[str],
                 sup: "Statement" = None,
                 sub: List["Statement"] = [],
                 pref: YangIdentifier = None) -> None:
        """Initialize the class instance.

        :param kw: keyword
        :param arg: argument
        :param sup: parent statement
        :param sub: list of substatements
        :param pref: keyword prefix (``None`` for built-in statements)
        """
        self.prefix = pref
        self.keyword = kw
        self.argument = arg
        self.superstmt = sup
        self.substatements = sub

    def __str__(self) -> str:
        """Return string representation of the receiver.
        """
        kw = (self.keyword if self.prefix is None
              else self.prefix + ":" + self.keyword)
        arg = ("" if self.argument is None
               else ' "' + self.argument.translate(self._escape_table) + '"')
        rest = " { ... }" if self.substatements else ";"
        return kw + arg + rest

    def find1(self, kw: YangIdentifier, arg: str = None,
              pref: YangIdentifier = None,
              required: bool = False) -> Optional["Statement"]:
        """Return first substatement with the given parameters.

        :param kw: statement keyword (local part for extensions)
        :param arg: argument (all arguments will match if ``None``)
        :param pref: keyword prefix (``None`` for built-in statements)
        :param required: this parameter determines what happens if the
                         statement is not found: if it is ``False``
                         (which is the default), then ``None`` is returned,
                         otherwise an exception is raised
        :raises StatementNotFound: if `required` is ``True`` and the
                                   statement is not found
        """
        for sub in self.substatements:
            if (sub.keyword == kw and sub.prefix == pref and
                (arg is None or sub.argument == arg)):
                return sub
        if required: raise StatementNotFound(self, kw)

    def find_all(self, kw: YangIdentifier,
                 pref: YangIdentifier = None) -> List["Statement"]:
        """Return the list all substatements with the given keyword and prefix.

        :param kw: statement keyword (local part for extensions)
        :param pref: keyword prefix (``None`` for built-in statements)
        """
        return [c for c in self.substatements
                if c.keyword == kw and c.prefix == pref]

    def get_definition(self, name: YangIdentifier,
                       kw: YangIdentifier) -> "Statement":
        """Recursively search ancestor statements for a definition.

        :param name: name of a grouping or datatype (with no prefix)
        :param kw: ``grouping`` or ``typedef``
        :raises DefinitionNotFound: if the definition is not found
        """
        stmt = self.superstmt
        while stmt:
            res = stmt.find1(kw, name)
            if res: return res
            stmt = stmt.superstmt
        raise DefinitionNotFound(kw, name)

class ModuleParser(Parser):
    """Parse YANG modules."""

    unescape_map = { "n" : "\n", "t": "\t", '"': '"',
                     "\\": "\\" } # type: Mapping[str,str]
    """Dictionary for mapping escape sequences to characters."""

    @classmethod
    def unescape(cls, text: str) -> str:
        """Replace escape sequence with corresponding characters.

        :param text: text to unescape
        """
        chop = text.split("\\", 1)
        return (chop[0] if len(chop) == 1
                else chop[0] + cls.unescape_map[chop[1][0]] +
                cls.unescape(chop[1][1:]))

    def opt_separator(self) -> None:
        """Parse an optional separator.

        :raises EndOfInput: if past the end of `self.input`
        """
        def back_break(c):
            self.offset -= 1
            return -1
        self.scan(
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
        i1 = self.yang_identifier()
        if self.peek() == ":":
            self.offset += 1
            i2 = self.yang_identifier()
            return (i1, i2)
        return (None, i1)

    def statement(self) -> Statement:
        """Parse YANG statement.

        :raises EndOfInput: if past the end of `self.input`
        :raises UnexpectedInput: if no syntactically correct statement is found
        """
        pref,kw = self.keyword()
        self.opt_separator()
        next = self.peek()
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
        res = Statement(kw, arg, pref=pref)
        if sub:
            res.substatements = self.substatements()
            for sub in res.substatements:
                sub.superstmt = res
        return res

    def argument(self) -> bool:
        """Parse statement argument.

        Return ``True`` if the argument is followed by block of substatements.
        """
        next = self.peek()
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
        next = self.peek()
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
        self.scan([(lambda c: 0, { "'": lambda: -1 })])
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
        self.scan([(lambda c: 0, { '"': lambda: -1,
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
        self.scan([(lambda c: 0, { ";": lambda: -1,
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
        while self.peek() != "}":
            res.append(self.statement())
            self.opt_separator()
        self.offset += 1
        return res

    def parse(self, mtext) -> Statement:
        """Parse a complete YANG module or submodule.

        :param mtext: YANG module text
        :raises EndOfInput: if past the end of `self.input`
        :raises UnexpectedInput: if top-level statement isn't ``(sub)module``
        """
        super().parse(mtext)
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

class StatementNotFound(YangsonException):
    """Exception to raise when a statement should exist but doesn't."""

    def __init__(self, parent: Statement, kw: YangIdentifier) -> None:
        self.parent = parent
        self.keyword = kw

    def __str__(self) -> str:
        """Print the statement's keyword."""
        return "`{}' in `{}'".format(self.keyword, self.parent)

class DefinitionNotFound(YangsonException):
    """Exception to be raised when a requested definition doesn't exist."""

    def __init__(self, kw: YangIdentifier, name: YangIdentifier) -> None:
        self.keyword = kw
        self.name = name

    def __str__(self) -> str:
        return "{} {} not found".format(self.keyword, self.name)
