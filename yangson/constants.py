"""Common constants."""

from enum import Enum
import re

class YangsonException(Exception):
    """Base class for all Yangson exceptions."""
    pass

# Regular expressions

_ident = "[a-zA-Z_][a-zA-Z_.-]*"
_pname = "((?P<prf>{}):)?(?P<loc>{})".format(_ident, _ident)
pname_re = re.compile(_pname)
_rhs = """("(?P<drhs>[^"]*)"|'(?P<srhs>[^']*)')"""
pred_re = re.compile(
    r"\[\s*(({}|\.)\s*=\s*{}|(?P<pos>\d*))\s*\]".format(_pname, _rhs))

# Enumeration classes

class DefaultDeny(Enum):
    """Enumeration of NACM default deny values."""
    none = 1
    write = 2
    all = 3
