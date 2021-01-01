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

"""YANG statements and a parser for YANG modules.

This module implements the following classes:

* ModuleParser: Recursive-descent parser for YANG modules.
* Statement: YANG statements.
"""

from typing import List, Optional, Tuple
from .exceptions import (
    EndOfInput, StatementNotFound, UnexpectedInput, InvalidArgument,
    ModuleNameMismatch, ModuleRevisionMismatch)
from .parser import Parser
from .typealiases import YangIdentifier


class Statement:

    """YANG statement."""

    _escape_table = str.maketrans({'"': '\\"', '\\': '\\\\'})
    """Table for translating characters to their escaped form."""

    def __init__(self,
                 kw: YangIdentifier,
                 arg: Optional[str],
                 pref: YangIdentifier = None):
        """Initialize the class instance.

        Args:
            kw: Keyword.
            arg: Argument.
            sup: Parent statement.
            sub: List of substatements.
            pref: Keyword prefix (``None`` for built-in statements).
        """
        self.prefix = pref
        self.keyword = kw
        self.argument = arg
        self.superstmt = None
        self.substatements = []

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

        Args:
            kw: Statement keyword (local part for extensions).
            arg: Argument (all arguments will match if ``None``).
            pref: Keyword prefix (``None`` for built-in statements).
            required: Should an exception be raised on failure?

        Raises:
            StatementNotFound: If `required` is ``True`` and the
                statement is not found.
        """
        for sub in self.substatements:
            if (sub.keyword == kw and sub.prefix == pref and
                    (arg is None or sub.argument == arg)):
                return sub
        if required:
            raise StatementNotFound(str(self), kw)

    def find_all(self, kw: YangIdentifier,
                 pref: YangIdentifier = None) -> List["Statement"]:
        """Return the list all substatements with the given keyword and prefix.

        Args:
            kw: Statement keyword (local part for extensions).
            pref: Keyword prefix (``None`` for built-in statements).
        """
        return [c for c in self.substatements
                if c.keyword == kw and c.prefix == pref]

    def get_definition(self, name: YangIdentifier,
                       kw: YangIdentifier) -> Optional["Statement"]:
        """Search ancestor statements for a definition.

        Args:
            name: Name of a grouping or datatype (with no prefix).
            kw: ``grouping`` or ``typedef``.

        Raises:
            DefinitionNotFound: If the definition is not found.
        """
        stmt = self.superstmt
        while stmt:
            res = stmt.find1(kw, name)
            if res:
                return res
            stmt = stmt.superstmt
        return None

    def get_error_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Return receiver's error tag and error message if present."""
        etag = self.find1("error-app-tag")
        emsg = self.find1("error-message")
        return (etag.argument if etag else None, emsg.argument if emsg else None)


class ModuleParser(Parser):
    """Parse YANG modules."""

    unescape_map = {"n": "\n", "t": "\t", '"': '"',
                    "\\": "\\"}  # type: Dict[str,str]
    """Dictionary for mapping escape sequences to characters."""

    def __init__(self, text: str, name: YangIdentifier = None, rev: str = None):
        """Initialize the parser instance.

        Args:
            name: Expected module name.
            rev: Expected revision date.
        """
        super().__init__(text)
        self.name = name
        self.rev = rev

    def parse(self) -> Statement:
        """Parse a complete YANG module or submodule.

        Args:
            mtext: YANG module text.

        Raises:
            EndOfInput: If past the end of input.
            ModuleNameMismatch: If parsed module name doesn't match `self.name`.
            ModuleRevisionMismatch: If parsed revision date doesn't match `self.rev`.
            UnexpectedInput: If top-level statement isn't ``(sub)module``.
        """
        self.opt_separator()
        start = self.offset
        res = self.statement()
        if res.keyword not in ["module", "submodule"]:
            self.offset = start
            raise UnexpectedInput(self, "'module' or 'submodule'")
        if self.name is not None and res.argument != self.name:
            raise ModuleNameMismatch(res.argument, self.name)
        if self.rev:
            revst = res.find1("revision")
            if revst is None or revst.argument != self.rev:
                raise ModuleRevisionMismatch(revst.argument, self.rev)
        try:
            self.opt_separator()
        except EndOfInput:
            return res
        raise UnexpectedInput(self, "end of input")

    def _back_break(self) -> int:
        self.offset -= 1
        return -1

    @classmethod
    def unescape(cls, text: str) -> str:
        """Replace escape sequence with corresponding characters.

        Args:
            text: Text to unescape.
        """
        chop = text.split("\\", 1)
        try:
            return (chop[0] if len(chop) == 1
                    else chop[0] + cls.unescape_map[chop[1][0]] +
                    cls.unescape(chop[1][1:]))
        except KeyError:
            raise InvalidArgument(text) from None

    def opt_separator(self) -> bool:
        """Parse an optional separator and return ``True`` if found.

        Raises:
            EndOfInput: If past the end of input.
        """
        start = self.offset
        self.dfa([
            {  # state 0: whitespace
                "": lambda: -1,
                " ": lambda: 0,
                "\t": lambda: 0,
                "\n": lambda: 0,
                "\r": lambda: 1,
                "/": lambda: 2
            },
            {  # state 1: CR/LF?
                "": self._back_break,
                "\n": lambda: 0
            },
            {  # state 2: start comment?
                "": self._back_break,
                "/": lambda: 3,
                "*": lambda: 4
            },
            {  # state 3: line comment
                "": lambda: 3,
                "\n": lambda: 0
            },
            {  # state 4: block comment
                "": lambda: 4,
                "*": lambda: 5
            },
            {  # state 5: end block comment?
                "": lambda: 4,
                "/": lambda: 0,
                "*": lambda: 5
            }])
        return start < self.offset

    def separator(self) -> None:
        """Parse a mandatory separator.

        Raises:
            EndOfInput: If past the end of input.
            UnexpectedInput: If no separator is found.
        """
        present = self.opt_separator()
        if not present:
            raise UnexpectedInput(self, "separator")

    def keyword(self) -> Tuple[Optional[str], str]:
        """Parse a YANG statement keyword.

        Raises:
            EndOfInput: If past the end of input.
            UnexpectedInput: If no syntactically correct keyword is found.
        """
        i1 = self.yang_identifier()
        if self.peek() == ":":
            self.offset += 1
            i2 = self.yang_identifier()
            return (i1, i2)
        return (None, i1)

    def statement(self) -> Statement:
        """Parse YANG statement.

        Raises:
            EndOfInput: If past the end of input.
            UnexpectedInput: If no syntactically correct statement is found.
        """
        pref, kw = self.keyword()
        pres = self.opt_separator()
        next = self.peek()
        if next == ";":
            arg = None
            sub = False  # type: bool
        elif next == "{":
            arg = None
            sub = True
        elif not pres:
            raise UnexpectedInput(self, "separator")
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
            self.opt_separator()
            return self.argument()
        else:
            raise UnexpectedInput(self, "';', '{'" +
                                  (" or '+'" if quoted else ""))

    def sq_argument(self) -> str:
        """Parse single-quoted argument.

        Raises:
            EndOfInput: If past the end of input.
        """
        self.offset += 1
        self._arg += self.up_to("'")

    def dq_argument(self) -> str:
        """Parse double-quoted argument.

        Raises:
            EndOfInput: If past the end of input.
        """
        def escape():
            self._escape = True
            return 1
        self._escape = False                 # any escaped chars?
        self.offset += 1
        start = self.offset
        self.dfa([
            {  # state 0: argument
                "": lambda: 0,
                '"': lambda: -1,
                "\\": escape
            },
            {  # state 1: after escape
                "": lambda: 0
            }])
        self._arg += (self.unescape(self.input[start:self.offset])
                      if self._escape else self.input[start:self.offset])
        self.offset += 1

    def unq_argument(self) -> str:
        """Parse unquoted argument.

        Raises:
            EndOfInput: If past the end of input.
        """
        start = self.offset
        self.dfa([
            {  # state 0: argument
                "": lambda: 0,
                ";": lambda: -1,
                " ": lambda: -1,
                "\t": lambda: -1,
                "\r": lambda: -1,
                "\n": lambda: -1,
                "{": lambda: -1,
                '/': lambda: 1
            },
            {  # state 1: comment?
                "": lambda: 0,
                "/": self._back_break,
                "*": self._back_break
            }])
        self._arg = self.input[start:self.offset]

    def substatements(self) -> List[Statement]:
        """Parse substatements.

        Raises:
            EndOfInput: If past the end of input.
        """
        res = []
        self.opt_separator()
        while self.peek() != "}":
            res.append(self.statement())
            self.opt_separator()
        self.offset += 1
        return res
