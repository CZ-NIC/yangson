from typing import Any, Callable, List, Optional, Tuple
from .constants import Axis, MultiplicativeOp
from .context import Context
from .instance import InstanceNode
from .parser import Parser, ParserException, EndOfInput, UnexpectedInput
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

    def union(self, ns: "NodeSet") -> "NodeSet":
        elems = {n.path():n for n in self}
        elems.update({n.path():n for n in ns})
        return self.__class__(elems.values())

    def sort(self, reverse: bool = False):
        super().sort(key=InstanceNode.path, reverse=reverse)

    def bind(self, trans: NodeExpr) -> "NodeSet":
        res = self.__class__([])
        for n in self:
            res = res.union(NodeSet(trans(n)))
        return res

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

class Expr:
    """Abstract class for XPath expressions."""

    indent = 2

    def __str__(self):
        return self._tree()

    def _tree(self, indent: int = 0):
        node_name = self.__class__.__name__
        attr = self._attribs()
        attr_str  = " (" + attr + ")\n" if attr else "\n"
        return (" " * indent + node_name + attr_str +
                self._children(indent + self.indent))

    def _attribs(self):
        return ""

    def _children(self, indent):
        return ""

    def _predicates(self, indent):
        if not self.predicates: return ""
        res = " " * indent + "-- Predicates:\n"
        newi = indent + 3
        for p in self.predicates:
            res += p._tree(newi)
        return res

class DyadicExpr(Expr):
    """Abstract superclass of dyadic expressions."""

    def __init__(self, left: "Expr", right: "Expr") -> None:
        self.left = left
        self.right = right

    def _children(self, indent: int):
        return self.left._tree(indent) + self.right._tree(indent)

class OrExpr(DyadicExpr):
    pass

class AndExpr(DyadicExpr):
    pass

class EqualityExpr(DyadicExpr):

    def __init__(self, left: Expr, right: Expr, negate: bool) -> None:
        super().__init__(left, right)
        self.negate = negate

    def _attribs(self):
        return "!=" if self.negate else "="

class RelationalExpr(DyadicExpr):

    def __init__(self, left: Expr, right: Expr, less: bool,
                 equal: bool) -> None:
        super().__init__(left, right)
        self.less = less
        self.equal = equal

    def _attribs(self):
        res = "<" if self.less else ">"
        if self.equal: res += "="
        return res

class AdditiveExpr(DyadicExpr):

    def __init__(self, left: Expr, right: Expr, plus: bool) -> None:
        super().__init__(left, right)
        self.plus = plus

    def _attribs(self):
        return "+" if self.plus else "-"

class MultiplicativeExpr(DyadicExpr):

    def __init__(self, left: Expr, right: Expr,
                 operator: MultiplicativeOp) -> None:
        super().__init__(left, right)
        self.operator = operator

    def _attribs(self):
        if self.operator == Axis.multiply: return "*"
        if self.operator == Axis.divide: return "/"
        if self.operator == Axis.modulo: return "mod"

class UnaryExpr(Expr):

    def __init__(self, expr: Expr, negate: bool):
        self.negate = negate

    def _attribs(self):
        return "-" if self.negate else "+"

class UnionExpr(DyadicExpr):
    pass

class Literal(Expr):

    def __init__(self, value: str) -> None:
        self.value = value

    def _attribs(self):
        return self.value

class Number(Expr):

    def __init__(self, value: float) -> None:
        self.value = value

    def _attribs(self):
        return str(self.value)

class PathExpr(Expr):

    def __init__(self, filter: Expr, path: Expr) -> None:
        self.filter = filter
        self.path = path

    def _children(self, indent: int):
        return self.filter._tree(indent) + self.path._tree(indent)

class FilterExpr(Expr):

    def __init__(self, primary: Expr, predicates: List[Expr]) -> None:
        self.primary = primary
        self.predicates = predicates

    def _children(self, indent):
        return self.primary._tree(indent) + self._predicates(indent)

class LocationPath(DyadicExpr):

    def __init__(self, left: Expr, right: Expr, absolute: bool) -> None:
        super().__init__(left, right)
        self.absolute = absolute

    def _attribs(self):
        return "ABS" if self.absolute else "REL"

class Step(Expr):

    def __init__(self, axis: Axis, qname: QualName,
                 predicates: List[Expr]) -> None:
        self.axis = axis
        self.qname = qname
        self.predicates = predicates

    def _attribs(self):
        return "{} {}".format(self.axis.name, self.qname)

    def _children(self, indent):
        return self._predicates(indent)

class FuncTrue(Expr):
    pass

class FuncFalse(Expr):
    pass

class XPathParser(Parser):
    """Parser for XPath expressions."""

    def __init__(self, text: str, mid: ModuleId) -> None:
        """Initialize the parser instance.

        :param mid: id of the context module
        """
        super().__init__(text)
        self.mid = mid

    def parse(self) -> Expr:
        """Parse an XPath 1.0 expression."""
        self.skip_ws()
        return self._or_expr()

    def _or_expr(self) -> Expr:
        op1 = self._and_expr()
        while self.test_string("or"):
            self.skip_ws()
            op2 = self._and_expr()
            op1 = OrExpr(op1, op2)
        return op1

    def _and_expr(self) -> Expr:
        op1 = self._equality_expr()
        while self.test_string("and"):
            self.skip_ws()
            op2 = self._equality_expr()
            op1 = AndExpr(op1, op2)
        return op1

    def _equality_expr(self) -> Expr:
        op1 = self._relational_expr()
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
            op2 = self._relational_expr()
            op1 = EqualityExpr(op1, op2, negate)

    def _relational_expr(self) -> Expr:
        op1 = self._additive_expr()
        while True:
            try:
                rel = self.peek()
            except EndOfInput:
                return op1
            if rel not in "<>": return op1
            self.offset += 1
            eq = self.test_string("=")
            self.skip_ws()
            op2 = self._additive_expr()
            op1 = RelationalExpr(op1, op2, rel == "<", eq)

    def _additive_expr(self) -> Expr:
        op1 = self._multiplicative_expr()
        while True:
            try:
                pm = self.peek()
            except EndOfInput:
                return op1
            if pm not in "+-": return op1
            self.adv_skip_ws()
            op2 = self._multiplicative_expr()
            op1 = AdditiveExpr(op1, op2, pm == "+")

    def _multiplicative_expr(self) -> Expr:
        op1 = self._unary_expr()
        while True:
            if self.test_string("*"):
                mulop = MultiplicativeOp.multiply
            elif self.test_string("div"):
                mulop = MultiplicativeOp.divide
            elif self.test_string("mod"):
                mulop = MultiplicativeOp.modulo
            else:
                return op1
            self.skip_ws()
            op2 = self._unary_expr()
            op1 = MultiplicativeExpr(op1, op2, mulop)

    def _unary_expr(self) -> Expr:
        negate = None
        while self.test_string("-"):
            negate = not negate
            self.skip_ws()
        expr = self._union_expr()
        return expr if negate is None else UnaryExpr(expr, negate)

    def _union_expr(self) -> Expr:
        op1 = self._lit_num_path()
        while self.test_string("|"):
            self.skip_ws()
            op2 = self._lit_num_path()
            op1 = UnionExpr(op1, op2)
        return op1

    def _lit_num_path(self) -> Expr:
        next = self.peek()
        if next == "(":
            self.adv_skip_ws()
            return self._path_expr(None)
        if next in "'\"":
            self.offset += 1
            val = self.up_to(next)
            self.skip_ws()
            return Literal(val)
        if ("0" <= next <= "9" or
            next == "." and "0" <= self.input[self.offset + 1] <= 9):
            val = self.float()
            self.skip_ws()
            return Number(val)
        start = self.offset
        try:
            fname = self.yang_identifier()
        except UnexpectedInput:
            return self._location_path()
        self.skip_ws()
        if self.test_string("("):
            self.skip_ws()
            return self._path_expr(fname)
        self.offset = start
        return self._relative_location_path()

    def _path_expr(self, fname: str) -> Expr:
        fexpr = self._filter_expr(fname)
        if self.test_string("/"):
            return PathExpr(fexpr, self._relative_location_path())
        return fexpr

    def _filter_expr(self, fname: str) -> Expr:
        if fname is None:
            prim = self._or_expr()
        else:
            prim = self._function_call(fname)
        self.char(")")
        self.skip_ws()
        return FilterExpr(prim, self._predicates())

    def _predicates(self) -> List[Expr]:
        res = []
        while self.test_string("["):
            print(self)
            res.append(self.parse())
            print(self)
            self.char("]")
            self.skip_ws()
        return res

    def _location_path(self) -> LocationPath:
        if self.test_string("/"):
            path = self._relative_location_path()
            path.absolute = True
            return path
        return self._relative_location_path()

    def _relative_location_path(self) -> LocationPath:
        op1 = self._step()
        while self.test_string("/"):
            self.skip_ws()
            op2 = self._step()
            op1 = LocationPath(op1, op2)
        return op1

    def _step(self) -> Step:
        return Step(*self._axis_qname(), self._predicates())

    def _axis_qname(self) -> Tuple[Axis, Optional[QualName]]:
        next = self.peek()
        if next == "*":
            self.adv_skip_ws()
            return (Axis.child, None)
        if next == "/":
            self.adv_skip_ws()
            return (Axis.descendant_or_self, None)
        if next == ".":
            self.offset += 1
            res = (Axis.parent if self.test_string(".") else Axis.self, None)
            self.skip_ws()
            return res
        yid = self.yang_identifier()
        ws = self.skip_ws()
        try:
            next = self.peek()
        except EndOfInput:
            return (Axis.child, (yid, self.mid[0]))
        if next == ":":
            self.offset += 1
            next = self.peek()
            if next == ":":
                self.adv_skip_ws()
                return (Axis[yid.replace("-", "_")], self._qname())
            if ws:
                raise InvalidXPath(self, "QName")
            nsp = Context.prefix2ns(yid, self.mid)
            loc = self.yang_identifier()
            self.skip_ws()
            return (Axis.child, (loc, nsp))
        return (Axis.child, (yid, self.mid[0]))

    def _qname(self) -> Optional[QualName]:
        """Parse XML QName."""
        if self.test_string("*"):
            self.skip_ws()
            return None
        ident = self.yang_identifier()
        res = ((self.yang_identifier(), Context.prefix2ns(ident, self.mid))
               if self.test_string(":") else (ident, self.mid[0]))
        self.skip_ws()
        return res

    def _function_call(self, name: str):
        if name == "true":
            res = FuncTrue()
        elif name == "false":
            res = FuncFalse()
        return res

class InvalidXPath(ParserException):
    """Exception to be raised for an invalid XPath expression."""

    def __init__(self, p: XPathParser, rule: str) -> None:
        super().__init__(p)
        self.rule = rule

    def __str__(self) -> str:
        return super().__str__() + ": production rule " + self.rule
