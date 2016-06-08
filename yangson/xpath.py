from typing import Any, Callable, List, Optional
from .context import Context
from .instance import InstanceNode
from .parser import Parser, ParserException, EndOfInput
from .typealiases import *

# Type aliases

NodeExpr = Callable[[InstanceNode], List[InstanceNode]]
XPathExpr = Callable[[InstanceNode, InstanceNode], bool]

def comparison(meth):
    def wrap(self, arg):
        if isinstance(arg, NodeSet):
            for n in arg:
                if meth(self, str(n.value)): return True
            return False
        return meth(self, arg)
    return wrap

class NodeSet(list):

    @staticmethod
    def union(nss: List[List[InstanceNode]]) -> List[InstanceNode]:
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
        return res

    def sort(self, reverse: bool = False):
        super().sort(key=InstanceNode.path, reverse=reverse)

    def bind(self, f: NodeExpr) -> "NodeSet":
        return NodeSet(self.union([ f(x) for x in self ]))

    def as_float(self) -> float:
        return float(self[0].value)

    def __str__(self) -> str:
        return str(self[0].value) if self else ""

    @comparison
    def __eq__(self, val) -> bool:
        for n in self:
            if (str(n.value) if isinstance(val, str) else n.value) == val:
                return True
        return False

    @comparison
    def __ne__(self, val) -> bool:
        for n in self:
            if (str(n.value) if isinstance(val, str) else n.value) != val:
                return True
        return False

    @comparison
    def __gt__(self, val) -> bool:
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
    def __lt__(self, val) -> bool:
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
    def __ge__(self, val) -> bool:
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
    def __le__(self, val) -> bool:
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

class XPathParser(Parser):
    """Parser for XPath expressions."""

    def __init__(self, mid: ModuleId) -> None:
        """Initialize the parser instance.

        :param mid: id of the context module
        """
        self.mid = mid

    def parse(self, xpath: str) -> XPathExpr:
        """Parse an XPath 1.0 expression."""
        super().parse(xpath)
        self.skip_ws()
        return lambda node: self._or_expr(node, node)

    def _or_expr(self, cnode: InstanceNode, origin: InstanceNode):
        op1 = self._and_expr(cnode, origin)
        while self.test_string("or"):
            self.skip_ws()
            op2 = self._and_expr(cnode, origin)
            op1 = bool(op1) or bool(op2)
        return op1

    def _and_expr(self, cnode: InstanceNode, origin: InstanceNode):
        op1 = self._equality_expr(cnode, origin)
        while self.test_string("and"):
            self.skip_ws()
            op2 = self._equality_expr(cnode, origin)
            op1 = bool(op1) and bool(op2)
        return op1

    def _equality_expr(self, cnode: InstanceNode, origin: InstanceNode):
        op1 = self._relational_expr(cnode, origin)
        while True:
            negate = False
            try:
                next = self.peek()
            except EndOfInput:
                return op1
            if next == "!":
                self.offset += 1
                negate = True
                try:
                    next = self.peek()
                except EndOfInput:
                    raise InvalidXPath(self, "EqualityExpr")
            if next != "=":
                if negate:
                    raise InvalidXPath(self, "EqualityExpr")
                return op1
            self.adv_skip_ws()
            op2 = self._relational_expr(cnode, origin)
            op1 = op1 != op2 if negate else op1 == op2

    def _relational_expr(self, cnode: InstanceNode, origin: InstanceNode):
        op1 = self._additive_expr(cnode, origin)
        while True:
            try:
                rel = self.peek()
            except EndOfInput:
                return op1
            if rel not in "<>": return op1
            self.offset += 1
            eq = self.test_string("=")
            self.skip_ws()
            op2 = self._additive_expr(cnode, origin)
            if rel == "<":
                op1 = op1 <= op2 if eq else op1 < op2
            else:
                op1 = op1 >= op2 if eq else op1 > op2

    def _additive_expr(self, cnode: InstanceNode, origin: InstanceNode):
        op1 = self._multiplicative_expr(cnode, origin)
        while True:
            try:
                pm = self.peek()
            except EndOfInput:
                return op1
            if pm not in "+-": return op1
            self.adv_skip_ws()
            op2 = self._multiplicative_expr(cnode, origin)
            op1 = op1 + op2 if pm == "+" else op1 - op2

    def _multiplicative_expr(self, cnode: InstanceNode, origin: InstanceNode):
        op1 = self._unary_expr(cnode, origin)
        while True:
            if self.test_string("*"):
                mulop = 1
            elif self.test_string("div"):
                mulop = 2
            elif self.test_string("mod"):
                mulop = 3
            else:
                return op1
            self.skip_ws()
            op2 = self._unary_expr(cnode, origin)
            if mulop == 1:
                op1 *= op2
            elif mulop == 2:
                op1 /= op2
            else:
                op1 %= op2

    def _unary_expr(self, cnode: InstanceNode, origin: InstanceNode):
        negate = None
        while self.test_string("-"):
            negate = not negate
        expr = self._primary_expr(cnode, origin)
        if negate is None: return expr
        if isinstance(expr, NodeSet):
            return -expr.as_float() if negate else expr.as_float()
        return -float(expr) if negate else float(expr)

    def _primary_expr(self, cnode: InstanceNode, origin: InstanceNode):
        next = self.peek()
        if next == "(":
            self.adv_skip_ws()
            res = self._or_expr(cnode, origin)
            self.char(")")
            self.skip_ws()
            return res
        if next in "'\"":
            self.offset += 1
            res = self.up_to(next)
            self.skip_ws()
            return res
        if next in "0123456789":
            res = self.float()
            self.skip_ws()
            return res
        if next == ".":
            self.offset += 1
            next = self.peek()
            if next in "0123456789":
                self.offset -= 1
                res = self.float()
                self.skip_ws()
                return res
        raise InvalidXPath(self, "PrimaryExpr")

    def _resolve_step(self, axis: str, qn: QualName) -> NodeExpr:
        try:
            return { "child": lambda n: n.children(qn),
                     "ancestor-or-self": lambda n: n.ancestors_or_self(qn),
                     "descendant": lambda n: n.descendants(qn) }[axis]
        except KeyError:
            raise InvalidXPath(self, "AxisName")

    def relative_location_path(self, cnode: InstanceNode, origin: InstanceNode,
                               token: str = None) -> NodeSet:
        """Parse ``RelativeLocationPath `` (production rule 3)."""
        if token is None:
            try:
                token = self.peek()
            except EndOfInput:
                return NodeSet([cnode])
            if token in "*/":
                self.adv_skip_ws()
            else:
                token = self.yang_identifier()
        ns = NodeSet([cnode])
        while True:
            ns = ns.bind(self.step(token))
            self.skip_ws()
            try:
                next = self.peek()
            except EndOfInput:
                break
            if next != "/": break
            self.adv_skip_ws()
        return ns

    def step(self, token: str) -> NodeExpr:
        """Parse ``Step`` (production rule 4)."""
        if token == "*": return lambda n: n.children()
        if token == "/": return lambda n: n.descendants(with_self=True)
        ws = self.skip_ws()
        try:
            next = self.peek()
        except EndOfInput:
            return self._resolve_step("child", (token, self.mid[0]))
        if next == ":":
            self.offset += 1
            next = self.peek()
            if next == ":":
                self.adv_skip_ws()
                return self._resolve_step(token, self.qname())
            if ws:
                raise InvalidXPath(self, "Step")
            return self._resolve_step("child", (self.yang_identifier(), token))
        return self._resolve_step("child", (token, self.mid[0]))

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
