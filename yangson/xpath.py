from typing import Any, Callable, List, Optional, Tuple, Union
from .constants import Axis, MultiplicativeOp
from .context import Context
from .instance import InstanceNode
from .parser import Parser, ParserException, EndOfInput, UnexpectedInput
from .typealiases import *

# Type aliases

NodeExpr = Callable[[InstanceNode], List[InstanceNode]]
XPathExpr = Callable[[InstanceNode, InstanceNode], bool]
XPathValue = Union["NodeSet", str, float, bool]

def comparison(meth):
    def wrap(self, arg):
        if isinstance(arg, NodeSet):
            for n in arg:
                if n.is_structured(): continue
                if meth(self, n.schema_node.type.canonical_string(n.value)):
                    return True
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
        is_str = isinstance(val, str)
        for n in self:
            if n.is_structured(): continue
            if is_str:
                if n.schema_node.type.canonical_string(n.value) == val:
                    return True
            elif n.value == val:
                return True
        return False

    @comparison
    def __ne__(self, val) -> bool:
        is_str = isinstance(val, str)
        for n in self:
            if n.is_structured(): continue
            if is_str:
                if n.schema_node.type.canonical_string(n.value) != val:
                    return True
            elif n.value != val:
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

class XPathContext:

    def __init__(self, cnode: InstanceNode, origin: InstanceNode,
                 position: int, size: int):
        self.cnode = cnode
        self.origin = origin
        self.position = position
        self.size = size

    def update_cnode(self, new_cnode: InstanceNode):
        return self.__class__(new_cnode, self.origin, self.position, self.size)

class Expr:
    """Abstract class for XPath expressions."""

    indent = 2

    def __str__(self):
        return self._tree()

    def evaluate(self, node: InstanceNode) -> XPathValue:
        return self._eval(XPathContext(node, node, 1, 1))

    @staticmethod
    def _as_float(val) -> float:
        return val.as_float() if isinstance(val, NodeSet) else float(val)

    def _tree(self, indent: int = 0):
        node_name = self.__class__.__name__
        attr = self._properties_str()
        attr_str  = " (" + attr + ")\n" if attr else "\n"
        return (" " * indent + node_name + attr_str +
                self._children_str(indent + self.indent))

    def _properties_str(self):
        return ""

    def _children_str(self, indent):
        return ""

    def _predicates_str(self, indent):
        if not self.predicates: return ""
        res = " " * indent + "-- Predicates:\n"
        newi = indent + 3
        for p in self.predicates:
            res += p._tree(newi)
        return res

    def _apply_predicates(self, ns: XPathValue,
                          xctx: XPathContext) -> XPathValue:
        for p in self.predicates:
            res = NodeSet([])
            size = len(ns)
            for i in range(size):
                pval = p._eval(XPathContext(ns[i], xctx.origin, i+1, size))
                try:
                    if isinstance(pval, float):
                        res.append(ns[int(pval) - 1])
                        break
                except IndexError:
                    return res
                if pval:
                    res.append(ns[i])
            ns = res
        return ns

class DyadicExpr(Expr):
    """Abstract superclass of dyadic expressions."""

    def __init__(self, left: "Expr", right: "Expr") -> None:
        self.left = left
        self.right = right

    def _children_str(self, indent: int):
        return self.left._tree(indent) + self.right._tree(indent)

    def _eval_ops(self, xctx: XPathContext) -> Tuple[XPathValue, XPathValue]:
        return (self.left._eval(xctx), self.right._eval(xctx))

class OrExpr(DyadicExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops(xctx)
        return lres or rres

class AndExpr(DyadicExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops(xctx)
        return lres and rres

class EqualityExpr(DyadicExpr):

    def __init__(self, left: Expr, right: Expr, negate: bool) -> None:
        super().__init__(left, right)
        self.negate = negate

    def _properties_str(self):
        return "!=" if self.negate else "="

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops(xctx)
        return lres != rres if self.negate else lres == rres

class RelationalExpr(DyadicExpr):

    def __init__(self, left: Expr, right: Expr, less: bool,
                 equal: bool) -> None:
        super().__init__(left, right)
        self.less = less
        self.equal = equal

    def _properties_str(self):
        res = "<" if self.less else ">"
        if self.equal: res += "="
        return res

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops(xctx)
        if self.less:
            return lres <= rres if self.equal else lres < rres
        return lres >= rres if self.equal else lres > rres

class AdditiveExpr(DyadicExpr):

    def __init__(self, left: Expr, right: Expr, plus: bool) -> None:
        super().__init__(left, right)
        self.plus = plus

    def _properties_str(self):
        return "+" if self.plus else "-"

    def _eval(self, xctx: XPathContext) -> float:
        ops = self._eval_ops(xctx)
        lres = self._as_float(ops[0])
        rres = self._as_float(ops[1])
        return lres + rres if self.plus else lres - rres

class MultiplicativeExpr(DyadicExpr):

    def __init__(self, left: Expr, right: Expr,
                 operator: MultiplicativeOp) -> None:
        super().__init__(left, right)
        self.operator = operator

    def _properties_str(self):
        if self.operator == MultiplicativeOp.multiply: return "*"
        if self.operator == MultiplicativeOp.divide: return "/"
        if self.operator == MultiplicativeOp.modulo: return "mod"

    def _eval(self, xctx: XPathContext) -> float:
        ops = self._eval_ops(xctx)
        lres = self._as_float(ops[0])
        rres = self._as_float(ops[1])
        if self.operator == MultiplicativeOp.multiply: return lres * rres
        if self.operator == MultiplicativeOp.divide: return lres / rres
        return lres % rres

class UnaryExpr(Expr):

    def __init__(self, expr: Expr, negate: bool):
        self.expr = expr
        self.negate = negate

    def _properties_str(self):
        return "-" if self.negate else "+"

    def _eval(self, xctx: XPathContext) -> float:
        res = self._as_float(self.expr._eval(xctx))
        return -res if self.negate else res

class UnionExpr(DyadicExpr):

    def _eval(self, xctx: XPathContext) -> NodeSet:
        lres, rres = self._eval_ops(xctx)
        return lres.union(rres)

class Literal(Expr):

    def __init__(self, value: str) -> None:
        self.value = value

    def _properties_str(self):
        return self.value

    def _eval(self, xctx: XPathContext):
        return self.value

class Number(Expr):

    def __init__(self, value: float) -> None:
        self.value = value

    def _properties_str(self):
        return str(self.value)

    def _eval(self, xctx: XPathContext):
        return self.value

class PathExpr(Expr):

    def __init__(self, filter: Expr, path: Expr) -> None:
        self.filter = filter
        self.path = path

    def _children_str(self, indent: int):
        return self.filter._tree(indent) + self.path._tree(indent)

    def _eval(self, xctx: XPathContext):
        res = self.filter._eval(xctx)
        return self.path._eval(xctx.update_cnode(res))

class FilterExpr(Expr):

    def __init__(self, primary: Expr, predicates: List[Expr]) -> None:
        self.primary = primary
        self.predicates = predicates

    def _children_str(self, indent):
        return self.primary._tree(indent) + self._predicates_str(indent)

    def _eval(self, xctx: XPathContext):
        res = self.primary._eval(xctx)
        return self._apply_predicates(res, xctx)

class LocationPath(DyadicExpr):

    def __init__(self, left: Expr, right: Expr, absolute: bool = False) -> None:
        super().__init__(left, right)
        self.absolute = absolute

    def _properties_str(self):
        return "ABS" if self.absolute else "REL"

    def _eval(self, xctx: XPathContext):
        nctx = xctx.update_cnode(xctx.cnode.top()) if self.absolute else xctx
        lres = self.left._eval(nctx)
        ns = lres.bind(self.right._node_trans())
        return self.right._apply_predicates(ns, nctx)

class Step(Expr):

    def __init__(self, axis: Axis, qname: QualName,
                 predicates: List[Expr]) -> None:
        self.axis = axis
        self.qname = qname
        self.predicates = predicates

    def _properties_str(self):
        return "{} {}".format(self.axis.name, self.qname)

    def _children_str(self, indent):
        return self._predicates_str(indent)

    def _node_trans(self) -> NodeExpr:
        return {
            Axis.ancestor_or_self: lambda n: n.ancestors_or_self(self.qname),
            Axis.child: lambda n: n.children(self.qname),
            Axis.descendant: lambda n: n.descendants(self.qname),
            Axis.self: (lambda n: [n] if self.qname is None or
                        self.qname == n.qualName else []),
                        }[self.axis]

    def _eval(self, xctx: XPathContext):
        ns = NodeSet(self._node_trans()(xctx.cnode))
        return self._apply_predicates(ns, xctx)

class FuncCount(Expr):

    def __init__(self, expr: Expr):
        self.expr = expr

    def _children_str(self, indent: int):
        return self.expr._tree(indent)

    def _eval(self, xctx: XPathContext) -> int:
        ns = self.expr._eval(xctx)
        return float(len(ns))

class FuncCurrent(Expr):

    def _eval(self, xctx: XPathContext) -> NodeSet:
        return NodeSet([xctx.origin])

class FuncFalse(Expr):

    def _eval(self, xctx: XPathContext) -> bool:
        return False

class FuncLast(Expr):

    def _eval(self, xctx: XPathContext) -> int:
        return xctx.size

class FuncNot(Expr):

    def __init__(self, expr: Expr) -> None:
        self.expr = expr

    def _children_str(self, indent: int):
        return self.expr._tree(indent)

    def _eval(self, xctx: XPathContext) -> bool:
        return not(self.expr._eval(xctx))

class FuncPosition(Expr):

    def _eval(self, xctx: XPathContext):
        return xctx.position

class FuncTrue(Expr):

    def _eval(self, xctx: XPathContext) -> bool:
        return True

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
                    raise InvalidXPath(self)
            if next != "=":
                if negate:
                    raise InvalidXPath(self)
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
            res.append(self.parse())
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
        try:
            yid = self.yang_identifier()
        except UnexpectedInput:
            raise InvalidXPath(self) from None
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
                raise InvalidXPath(self)
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

    def _func_count(self):
        expr = self.parse()
        return FuncCount(expr)

    def _func_current(self):
        return FuncCurrent()

    def _func_false(self):
        return FuncFalse()

    def _func_last(self):
        return FuncLast()

    def _func_not(self):
        return FuncNot(self.parse())

    def _func_position(self):
        return FuncPosition()

    def _func_true(self):
        return FuncTrue()

    def _function_call(self, fname: str):
        return { "count": self._func_count,
                 "current": self._func_current,
                 "false": self._func_false,
                 "last": self._func_last,
                 "not": self._func_not,
                 "position": self._func_position,
                 "true": self._func_true,
                 }[fname]()

class InvalidXPath(ParserException):
    """Exception to be raised for an invalid XPath expression."""

    def __str__(self) -> str:
        return str(self.parser)
