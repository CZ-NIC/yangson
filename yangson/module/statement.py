from typing import List, Optional

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
                 kw: str,
                 arg: Optional[str],
                 sub: List["Statement"] = [],
                 pref: Optional[str] = None) -> None:
        """Initialize the instance.
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

    def find1(self, kw: str, arg: str = None) -> Optional["Statement"]:
        """Find the first substatement with the given keyword (and argument).
        """
        for sub in self.substatements:
            if sub.keyword == kw and (arg is None or sub.argument == arg):
                return sub

    def find_all(self, kw: str) -> List["Statement"]:
        """Find all substatements with the given keyword.
        """
        return [c for c in self.substatements if c.keyword == kw]
