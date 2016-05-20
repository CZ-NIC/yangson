"""XPath parser."""

from typing import Callable, List, Union
from .parser import EndOfInput, Parser, UnexpectedInput
from .instance import InstanceNode
from .typealiases import *

# Type aliases
XPathValue = Union["NodeSet", float, str, bool]
XPathExpr = Callable[[InstanceNode], XPathValue]

class NodeSet(list):
    """This class represents XPath node-set."""

    @staticmethod
    def union(nss: List[List[InstanceNode]]) -> "NodeSet":
        paths = set()
        res = []
        for ns in nss:
            newp = set()
            for i in ns:
                p = i.path()
                if p not in paths:
                    newp.add(p)
                    res.append(i)
            paths |= newp
        return NodeSet(res)
                    
    def sort(self, reverse: bool = False):
        super().sort(key=InstanceNode.path, reverse=reverse)

    def ancestors(self, name: InstanceName = None,
                  with_root: bool = False) -> "NodeSet":
        return self.union([ i.ancestors(name, with_root) for i in self ])

    def ancestors_or_self(self, name: InstanceName = None,
                          with_root: bool = False) -> "NodeSet":
        return self.union(
            [ i.ancestors_or_self(name, with_root) for i in self ])

    def preceding_siblings(self, name: InstanceName = None) -> "NodeSet":
        return self.union([ i.preceding_siblings(name) for i in self ])

    def following_siblings(self, name: InstanceName = None) -> "NodeSet":
        return self.union([ i.following_siblings(name) for i in self ])

    def children(self, name: InstanceName = None) -> "NodeSet":
        return self.union([ i.children(name) for i in self ])

    def descendants(self, name: InstanceName = None) -> "NodeSet":
        return self.union([ i.descendants(name) for i in self ])

class XPathParser(Parser):
    """XPath parser."""
    pass
