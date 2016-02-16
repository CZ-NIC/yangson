"""YANG statements."""

from typing import List, Optional
from .exception import YangsonException
from .typealiases import YangIdentifier

class Statement(object):

    """This class represents a YANG statement.

    Instance variables:

    * keyword: statement keyword,
    * prefix: optional keyword prefix (for extensions),
    * argument: statement argument,
    * superstmt: parent statement,
    * substatements: list of substatements.
    """

    escape_table = str.maketrans({ '"': '\\"', '\\': '\\\\'})
    """Table for translating characters to their escaped form."""

    def __init__(self,
                 kw: YangIdentifier,
                 arg: Optional[str],
                 sup: Optional["Statement"] = None,
                 sub: List["Statement"] = [],
                 pref: Optional[YangIdentifier] = None) -> None:
        """Initialize the instance.

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
               else ' "' + self.argument.translate(self.escape_table) + '"')
        rest = " { ... }" if self.substatements else ";"
        return kw + arg + rest

    def find1(self,
              kw: YangIdentifier,
              arg: Optional[str] = None,
              pref: Optional[YangIdentifier] = None,
              required: bool = False) -> Optional["Statement"]:
        """Return first substatement with the given parameters.

        :param kw: keyword
        :param arg: argument (all arguments will match if `None`)
        :param pref: keyword prefix (for extensions)
        :param required: controls whether exception is raised
        :raises StatementNotFound: if `required` and statement not found
        """
        for sub in self.substatements:
            if (sub.keyword == kw and sub.prefix == pref and
                (arg is None or sub.argument == arg)):
                return sub
        if required: raise StatementNotFound(kw)

    def find_all(self,
                 kw: YangIdentifier,
                 pref: Optional[YangIdentifier] = None) -> List["Statement"]:
        """Find all substatements with the given keyword (and prefix).

        :param kw: keyword
        :param pref: keyword prefix (for extensions)
        """
        return [c for c in self.substatements
                if c.keyword == kw and c.prefix == pref]

    def get_grouping(self, gname: YangIdentifier) -> "Statement":
        """Recursively search ancestor statements for a grouping.

        :param gname: name of the grouping
        """
        stmt = self.superstmt
        while stmt:
            res = stmt.find1("grouping", gname)
            if res: return res
            stmt = stmt.superstmt
        raise GroupingNotFound(gname)

class StatementNotFound(YangsonException):
    """Exception to raise when a statement should exist but doesn't."""

    def __init__(self, kw: YangIdentifier) -> None:
        self.keyword = kw

    def __str__(self) -> str:
        """Print the statement's keyword."""
        return self.keyword

class GroupingNotFound(YangsonException):
    """Exception to be raised when a requested grouping doesn't exist."""

    def __init__(self, gname: YangIdentifier) -> None:
        self.gname = gname

    def __str__(self) -> str:
        return "grouping " + self.gname + " not found"
