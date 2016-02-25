"""Regular expressions."""

import re

_ident = "[a-zA-Z_][a-zA-Z_.-]*"
_qname = "((?P<prf>{}):)?(?P<loc>{})".format(_ident, _ident)
qname_re = re.compile(_qname)
_rhs = """("(?P<drhs>[^"]*)"|'(?P<srhs>[^']*)')"""
pred_re = re.compile(
    r"\[\s*(({}|\.)\s*=\s*{}|(?P<pos>\d*))\s*\]".format(_qname, _rhs))
