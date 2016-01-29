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
        """Initialize the instance."""
        self.prefix = pref
        self.keyword = kw
        self.argument = arg
        self.substatements = sub

    def __str__(self) -> str:
        kw = (self.keyword if self.prefix is None
              else self.prefix + ":" + self.keyword)
        arg = ("" if self.argument is None
               else ' "' + self.argument.translate(self.escape_table) + '"')
        rest = " { ... }" if self.substatements else ";"
        return kw + arg + rest
