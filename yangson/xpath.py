from math import copysign
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
        paths = set([n.path() for n in self])
        return self.__class__(self + [n for n in ns if n.path() not in paths])

    def bind(self, trans: NodeExpr) -> "NodeSet":
        res = self.__class__([])
        for n in self:
            res = res.union(NodeSet(trans(n)))
        return res

    def as_float(self) -> float:
        return float(self[0].value)

    def __str__(self) -> str:
        return str(self[0]) if self else ""

    @comparison
    def __eq__(self, val: XPathValue) -> bool:
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

    def _eval_float(self, xctx: XPathContext) -> float:
        val = self._eval(xctx)
        return val.as_float() if isinstance(val, NodeSet) else float(val)

    def _eval_string(self, xctx: XPathContext) -> str:
        val = self._eval(xctx)
        if isinstance(val, float):
            try:
                if int(val) == val: return str(int(val))
            except OverflowError:
                return "Infinity" if val > 0 else "-Infinity"
            except ValueError:
                return "NaN"
        if isinstance(val, bool): return str(val).lower()
        return str(val)

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

class UnaryExpr(Expr):
    """Abstract superclass for unary expressions."""

    def __init__(self, expr: Optional[Expr]) -> None:
        self.expr = expr

    def _children_str(self, indent: int):
        return self.expr._tree(indent) if self.expr else ""

class BinaryExpr(Expr):
    """Abstract superclass of binary expressions."""

    def __init__(self, left: Expr, right: Expr) -> None:
        self.left = left
        self.right = right

    def _children_str(self, indent: int):
        return self.left._tree(indent) + self.right._tree(indent)

    def _eval_ops(self, xctx: XPathContext) -> Tuple[XPathValue, XPathValue]:
        return (self.left._eval(xctx), self.right._eval(xctx))

    def _eval_ops_float(self, xctx: XPathContext) -> Tuple[float, float]:
        return (self.left._eval_float(xctx), self.right._eval_float(xctx))

    def _eval_ops_string(self, xctx: XPathContext) -> Tuple[str, str]:
        return (self.left._eval_string(xctx), self.right._eval_string(xctx))

class OrExpr(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops(xctx)
        return lres or rres

class AndExpr(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops(xctx)
        return lres and rres

class EqualityExpr(BinaryExpr):

    def __init__(self, left: Expr, right: Expr, negate: bool) -> None:
        super().__init__(left, right)
        self.negate = negate

    def _properties_str(self):
        return "!=" if self.negate else "="

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops(xctx)
        return lres != rres if self.negate else lres == rres

class RelationalExpr(BinaryExpr):

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

class AdditiveExpr(BinaryExpr):

    def __init__(self, left: Expr, right: Expr, plus: bool) -> None:
        super().__init__(left, right)
        self.plus = plus

    def _properties_str(self):
        return "+" if self.plus else "-"

    def _eval(self, xctx: XPathContext) -> float:
        lres, rres = self._eval_ops_float(xctx)
        return lres + rres if self.plus else lres - rres

class MultiplicativeExpr(BinaryExpr):

    def __init__(self, left: Expr, right: Expr,
                 operator: MultiplicativeOp) -> None:
        super().__init__(left, right)
        self.operator = operator

    def _properties_str(self):
        if self.operator == MultiplicativeOp.multiply: return "*"
        if self.operator == MultiplicativeOp.divide: return "div"
        if self.operator == MultiplicativeOp.modulo: return "mod"

    def _eval(self, xctx: XPathContext) -> float:
        lres, rres = self._eval_ops_float(xctx)
        if self.operator == MultiplicativeOp.multiply:
            return lres * rres
        if self.operator == MultiplicativeOp.divide:
            try:
                return lres / rres
            except ZeroDivisionError:
                return (float("nan") if lres == 0.0
                        else copysign(float('inf'), lres))
        try:
            return copysign(lres % rres, lres)
        except ZeroDivisionError:
            return float('nan')

class UnaryMinusExpr(UnaryExpr):

    def __init__(self, expr: Expr, negate: bool):
        super().__init__(expr)
        self.negate = negate

    def _properties_str(self):
        return "-" if self.negate else "+"

    def _eval(self, xctx: XPathContext) -> float:
        res = self.expr._eval_float(xctx)
        return -res if self.negate else res

class UnionExpr(BinaryExpr):

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
        return float(self.value)

class PathExpr(BinaryExpr):

    def _eval(self, xctx: XPathContext):
        res = self.left._eval(xctx)
        return self.right._eval(xctx.update_cnode(res))

class FilterExpr(Expr):

    def __init__(self, primary: Expr, predicates: List[Expr]) -> None:
        self.primary = primary
        self.predicates = predicates

    def _children_str(self, indent):
        return self.primary._tree(indent) + self._predicates_str(indent)

    def _eval(self, xctx: XPathContext):
        res = self.primary._eval(xctx)
        return self._apply_predicates(res, xctx)

class LocationPath(BinaryExpr):

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
            Axis.ancestor: lambda n, qn=self.qname: n.ancestors(qn),
            Axis.ancestor_or_self:
                lambda n, qn=self.qname: n.ancestors_or_self(qn),
            Axis.child: lambda n, qn=self.qname: n.children(qn),
            Axis.descendant: lambda n, qn=self.qname: n.descendants(qn),
            Axis.descendant_or_self:
                lambda n, qn=self.qname: n.descendants(qn, True),
            Axis.following_sibling:
                lambda n, qn=self.qname: n.following_siblings(qn),
            Axis.parent: (
                lambda n, qn=self.qname: [] if qn and qn != n.parent.qualName
                else [n.up()]),
            Axis.preceding_sibling:
                lambda n, qn=self.qname: n.preceding_siblings(qn),
            Axis.self:
                lambda n, qn=self.qname: [] if qn and qn != n.qualName else [n],
                }[self.axis]

    def _eval(self, xctx: XPathContext):
        ns = NodeSet(self._node_trans()(xctx.cnode))
        return self._apply_predicates(ns, xctx)

class FuncConcat(Expr):

    def __init__(self, parts: List[Expr]) -> None:
        self.parts = parts

    def _children_str(self, indent: int) -> str:
        return "".join([ex._tree(indent) for ex in self.parts])

    def _eval(self, xctx: XPathContext) -> str:
        return "".join([ex._eval_string(xctx) for ex in self.parts])

class FuncContains(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops_string(xctx)
        return lres.find(rres) >= 0

class FuncCount(UnaryExpr):

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
        return float(xctx.size)

class FuncName(UnaryExpr):

    def __init__(self, expr: Optional[Expr], local: bool) -> None:
        super().__init__(expr)
        self.local = local

    def _properties_str(self):
        return "LOC" if self.local else ""

    def _eval(self, xctx: XPathContext) -> str:
        if self.expr is None:
            node = xctx.cnode
        else:
            ns = self.expr._eval(xctx)
            try:
                node = ns[0]
            except TypeError:
                raise XPathTypeError(ns)
            except IndexError:
                return ""
        if node.name is None: return ""
        if self.local:
            p, s, loc = node.name.partition(":")
            return loc if s else p
        return node.name

class FuncNot(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        return not(self.expr._eval(xctx))

class FuncPosition(Expr):

    def _eval(self, xctx: XPathContext) -> int:
        return xctx.position

class FuncStartsWith(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops_string(xctx)
        return lres.startswith(rres)

class FuncString(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> str:
        if self.expr is None:
            return xctx.cnode.schema_node.type.canonical_string(xctx.cnode.value)
        return self.expr._eval_string(xctx)

class FuncSubstring(BinaryExpr):

    def __init__(self, string: Expr, start: Expr,
                 length: Optional[Expr]) -> None:
        super().__init__(string, start)
        self.length = length

    def _eval(self, xctx: XPathContext) -> str:
        string = self.left._eval_string(xctx)
        rres = self.right._eval_float(xctx)
        try:
            start = round(rres) - 1
        except (ValueError, OverflowError):
            return "" if self.length or rres != float("-inf") else string
        if self.length is None:
            return string[max(start, 0):]
        length = self.length._eval_float(xctx)
        try:
            end = start + round(length)
        except (ValueError, OverflowError):
            return string[max(start, 0):] if length == float('inf') else ""
        return string[max(start, 0):end]

class FuncSubstringAfter(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> str:
        lres, rres = self._eval_ops_string(xctx)
        ind = lres.find(rres)
        return lres[ind + len(rres):] if ind >= 0 else ""

class FuncSubstringBefore(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> str:
        lres, rres = self._eval_ops_string(xctx)
        ind = lres.find(rres)
        return lres[:ind] if ind >= 0 else ""

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
        op1 = self._unary_minus_expr()
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
            op2 = self._unary_minus_expr()
            op1 = MultiplicativeExpr(op1, op2, mulop)

    def _unary_minus_expr(self) -> Expr:
        negate = None
        while self.test_string("-"):
            negate = not negate
            self.skip_ws()
        expr = self._union_expr()
        return expr if negate is None else UnaryMinusExpr(expr, negate)

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

    def _axis_qname(self) -> Tuple[Axis, Union[QualName, bool]]:
        next = self.peek()
        if next == "*":
            self.adv_skip_ws()
            return (Axis.child, False)
        if next == "/":
            self.skip_ws()
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
        if next == "(":
            return (Axis.child, _node_type(yid))
        if next == ":":
            self.offset += 1
            next = self.peek()
            if next == ":":
                self.adv_skip_ws()
                try:
                    axis = Axis[yid.replace("-", "_")]
                except KeyError:
                    if yid in ("attribute", "following",
                               "namespace", "preceding"):
                        raise NotImplemented("axis '{}::'".format(yid)) from None
                    raise InvalidXPath(self) from None
                return (axis, self._qname())
            if ws:
                raise InvalidXPath(self)
            nsp = Context.prefix2ns(yid, self.mid)
            loc = self.yang_identifier()
            self.skip_ws()
            return (Axis.child, (loc, nsp))
        return (Axis.child, (yid, self.mid[0]))

    def _node_type(self, typ):
        if typ == "node":
            self.adv_skip_ws()
            self.char(")")
            self.skip_ws()
            return None
        elif typ in ("comment", "processing-instruction", "text"):
            raise NotImplemented("node type '{}()'".format(typ))
        raise InvalidXPath(self)

    def _qname(self) -> Optional[QualName]:
        """Parse XML QName."""
        if self.test_string("*"):
            self.skip_ws()
            return False
        ident = self.yang_identifier()
        ws = self.skip_ws()
        try:
            next = self.peek()
        except EndOfInput:
            return (ident, self.mid[0])
        if next == "(":
            return self._node_type(ident)
        res = ((self.yang_identifier(), Context.prefix2ns(ident, self.mid))
               if not ws and self.test_string(":") else (ident, self.mid[0]))
        self.skip_ws()
        return res

    def _opt_arg(self) -> Optional[Expr]:
        return None if self.peek() == ")" else self.parse()

    def _two_args(self) -> Tuple[Expr]:
        fst = self.parse()
        self.char(",")
        self.skip_ws()
        return (fst, self.parse())

    def _func_concat(self) -> FuncConcat:
        res = [self.parse()]
        while self.test_string(","):
            self.skip_ws()
            res.append(self.parse())
        if len(res) < 2:
            raise InvalidXPath(self)
        return FuncConcat(res)

    def _func_contains(self) -> FuncContains:
        return FuncContains(*self._two_args())

    def _func_count(self) -> FuncCount:
        return FuncCount(self.parse())

    def _func_current(self) -> FuncCurrent:
        return FuncCurrent()

    def _func_false(self) -> FuncFalse:
        return FuncFalse()

    def _func_last(self) -> FuncLast:
        return FuncLast()

    def _func_local_name(self) -> FuncName:
        return FuncName(self._opt_arg(), local=True)

    def _func_name(self) -> FuncName:
        return FuncName(self._opt_arg(), local=False)

    def _func_not(self) -> FuncNot:
        return FuncNot(self.parse())

    def _func_position(self) -> FuncPosition:
        return FuncPosition()

    def _func_starts_with(self) -> FuncStartsWith:
        return FuncStartsWith(*self._two_args())

    def _func_string(self) -> FuncString:
        return FuncString(self._opt_arg())

    def _func_substring(self) -> FuncSubstring:
        string, start = self._two_args()
        if self.test_string(","):
            self.skip_ws()
            length = self.parse()
        else:
            length = None
        return FuncSubstring(string, start, length)

    def _func_substring_after(self) -> FuncSubstringAfter:
        return FuncSubstringAfter(*self._two_args())

    def _func_substring_before(self) -> FuncSubstringBefore:
        return FuncSubstringBefore(*self._two_args())

    def _func_true(self) -> FuncTrue:
        return FuncTrue()

    def _function_call(self, fname: str):
        try:
            return { "concat": self._func_concat,
                     "contains": self._func_contains,
                     "count": self._func_count,
                     "current": self._func_current,
                     "false": self._func_false,
                     "last": self._func_last,
                     "local-name": self._func_local_name,
                     "name": self._func_name,
                     "not": self._func_not,
                     "position": self._func_position,
                     "starts-with": self._func_starts_with,
                     "string": self._func_string,
                     "substring": self._func_substring,
                     "substring-after": self._func_substring_after,
                     "substring-before": self._func_substring_before,
                     "true": self._func_true,
                     }[fname]()
        except KeyError:
            if fname in ("id", "namespace-uri"):
                raise NotImplemented("function '{}()'".format(fname)) from None
            raise InvalidXPath(self) from None

class InvalidXPath(ParserException):
    """Exception to be raised for an invalid XPath expression."""

    def __str__(self) -> str:
        return str(self.parser)

class XPathTypeError(ParserException):
    """Exception to be raised for type errors in XPath evaluation."""

    def __init__(self, value: XPathValue) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

class NotImplemented(ParserException):
    """Exception to be raised for unimplemented XPath features."""

    def __init__(self, feature: str) -> None:
        self.feature = feature

    def __str__(self) -> str:
        return str(self.feature)
