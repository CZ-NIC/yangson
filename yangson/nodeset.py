"""XPath node-set"""

from typing import List, Callable, Union
from .instance import InstanceNode

# Type aliases

NodeExpr = Callable[[InstanceNode], "NodeSet"]
XPathValue = Union["NodeSet", str, float, bool]

def comparison(meth):
    def wrap(self, arg):
        if isinstance(arg, NodeSet):
            for n in arg:
                if n.is_structured(): continue
                if meth(self, str(n)):
                    return True
            return False
        return meth(self, arg)
    return wrap

class NodeSet(list):

    def union(self, ns: "NodeSet") -> "NodeSet":
        paths = set([n.path() for n in self])
        return self.__class__(self + [n for n in ns if n.path() not in paths])

    def bind(self, trans: NodeExpr) -> "NodeSet":
        res = self.__class__([])
        for n in self:
            res = res.union(trans(n))
        return res

    def __float__(self) -> float:
        return float(self[0].value)

    def __str__(self) -> str:
        return str(self[0]) if self else ""

    @comparison
    def __eq__(self, val: XPathValue) -> bool:
        is_str = isinstance(val, str)
        for n in self:
            if n.is_structured(): continue
            if is_str:
                if str(n) == val:
                    return True
            elif n.value == val:
                return True
        return False

    @comparison
    def __ne__(self, val: XPathValue) -> bool:
        is_str = isinstance(val, str)
        for n in self:
            if n.is_structured(): continue
            if is_str:
                if str(n) != val:
                    return True
            elif n.value != val:
                return True
        return False

    @comparison
    def __gt__(self, val: XPathValue) -> bool:
        try:
            val = float(val)
        except (ValueError, TypeError):
            return False
        for n in self:
            try:
                if float(n.value) > val:
                    return True
            except (ValueError, TypeError):
                continue
        return False

    @comparison
    def __lt__(self, val: XPathValue) -> bool:
        try:
            val = float(val)
        except (ValueError, TypeError):
            return False
        for n in self:
            try:
                if float(n.value) < val:
                    return True
            except (ValueError, TypeError):
                continue
        return False

    @comparison
    def __ge__(self, val: XPathValue) -> bool:
        try:
            val = float(val)
        except (ValueError, TypeError):
            return False
        for n in self:
            try:
                if float(n.value) >= val:
                    return True
            except (ValueError, TypeError):
                continue
        return False

    @comparison
    def __le__(self, val: XPathValue) -> bool:
        try:
            val = float(val)
        except (ValueError, TypeError):
            return False
        for n in self:
            try:
                if float(n.value) <= val:
                    return True
            except (ValueError, TypeError):
                continue
        return False
