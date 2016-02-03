from typing import List, Optional
from yangson.types import YangIdentifier

class Statement(object):

    """This class represents a YANG statement.

    Instance variables:

    * keyword: statement keyword,
    * namespace: `None` or namespace URI (for extensions),
    * prefix: statement argument,
    * substatements: list of substatements.
    """

    escape_table = str.maketrans({ '"': '\\"', '\\': '\\\\'})
    """Table for translating characters to their escaped form."""

    def __init__(self,
                 kw: YangIdentifier,
                 arg: Optional[str],
                 sub: List["Statement"] = [],
                 pref: Optional[YangIdentifier] = None) -> None:
        """Initialize the instance.

        :param kw: keyword
        :param arg: argument
        :param sub: list of substatements
        :param pref: keyword prefix (`None` for built-in statements)
        """
        self.prefix = pref
        self.keyword = kw
        self.argument = arg
        self.substatements = sub

    def __str__(self) -> str:
        """Return a string representation of the receiver.
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
              pref: Optional[YangIdentifier] = None) -> Optional["Statement"]:
        """Find the first substatement with the given parameters.

        :param kw: keyword
        :param arg: argument (all arguments will match if `None`)
        :param pref: keyword prefix (for extensions)
        """
        for sub in self.substatements:
            if (sub.keyword == kw and sub.prefix == pref and
                (arg is None or sub.argument == arg)):
                return sub

    def find_all(self,
                 kw: YangIdentifier,
                 pref: Optional[YangIdentifier] = None) -> List["Statement"]:
        """Find all substatements with the given keyword (and prefix).

        :param kw: keyword
        :param pref: keyword prefix (for extensions)
        """
        return [c for c in self.substatements
                if c.keyword == kw and c.prefix == pref]
