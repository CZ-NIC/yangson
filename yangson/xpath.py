from typing import Callable, List, Optional
from .context import Context
from .instance import InstanceNode
from .parser import Parser, ParserException, EndOfInput
from .typealiases import *

# Type aliases

NodeExpr = Callable[[InstanceNode, InstanceNode], List[InstanceNode]]
NodeTrans = Callable[[InstanceNode], List[InstanceNode]]
XPathExpr = Callable[[InstanceNode, InstanceNode], bool]

class NodeSet:

    def __init__(self, expr: NodeExpr) -> None:
        self.eval = expr

    @classmethod
    def pure(cls, node = InstanceNode) -> "NodeSet":
        return cls(lambda x, y: [node])

    def bind(self, f: NodeTrans) -> "NodeSet":
        return NodeSet(lambda cur, orig:
                       [ y for x in self.eval(cur, orig) for y in f(x) ])


class XPathParser(Parser):
    """Parser for XPath expressions.

    Method docstrings refer to production rules in XPath 1.0 grammar
    """

    def __init__(self, mid: ModuleId) -> None:
        """Initialize the parser instance.

        :param mid: id of the context module
        """
        self.mid = mid

    def parse(self, xpath: str) -> XPathExpr:
        """Parse an XPath 1.0 expression."""
        super().parse(xpath)
        start = NodeSet(lambda cur, orig: [cur])
        return start.bind(self.step())

    def _resolve_step(self, axis, qn):
        if axis == "child":
            return lambda n: n.children(qn)
        if axis == "ancestor-or-self":
            return lambda n: n.ancestors_or_self(qn)

    def step(self) -> NodeTrans:
        """Parse ``Step`` (production rule 4)."""
        next = self.peek()
        if next == "*":
            self.offset += 1
            return self._resolve_step("child", None)
        ident = self.yang_identifier()
        ws = self.skip_ws()
        next = self.peek()
        if next == ":":
            self.offset += 1
            next = self.peek()
            if next == ":":
                self.offset += 1
                self.skip_ws()
                return self._resolve_step(ident, self.qname())
            if ws:
                raise InvalidXPath(self, "Step")
            return self._resolve_step("child", (self.yang_identifier(), ident))
        return self._resolve_step("child", (ident, self.mid[0]))

    def qname(self) -> Optional[QualName]:
        """Parse XML QName."""
        next = self.peek()
        if next == "*":
            self.offset += 1
            return None
        ident = self.yang_identifier()
        try:
            next = self.peek()
        except EndOfInput:
            return (ident, self.mid[0])
        if next != ":": return (ident, self.mid[0])
        self.offset += 1
        return (self.yang_identifier(), Context.prefix2ns(ident, self.mid))

class InvalidXPath(ParserException):
    """Exception to be raised for an invalid XPath expression."""

    def __init__(self, p: XPathParser, rule: str) -> None:
        super().__init__(p)
        self.rule = rule

    def __str__(self) -> str:
        return super().__str__() + ": production rule " + self.rule
