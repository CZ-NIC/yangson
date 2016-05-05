"""YANG statements."""

from typing import List, Optional
from .constants import YangsonException
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
