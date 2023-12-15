# Copyright © 2016–2023 CZ.NIC, z. s. p. o.
#
# This file is part of Yangson.
#
# Yangson is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Yangson is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Yangson.  If not, see <http://www.gnu.org/licenses/>.

"""Abstract syntax tree for XPath 1.0 expressions with YANG extensions.

This module defines a number of classes that mostly correspond to
variables (non-terminals) of the XPath 1.0 grammar. Only the following
class is intended to be public:

* Expr: XPath 1.0 expression with YANG 1.1 extensions.
"""
import decimal
from math import ceil, copysign, floor, isnan
from elementpath import RegexError, translate_pattern
from xml.sax.saxutils import quoteattr
import re
from typing import Optional
from .schemadata import SchemaContext
from .enumerations import Axis, MultiplicativeOp
from .exceptions import InvalidArgument, XPathTypeError
from .instance import (EntryIndex, EntryKeys, EntryValue, InstanceNode,
                       InstanceRoute, MemberName)
from .nodeset import NodeExpr, NodeSet, XPathValue
from .typealiases import QualName


class XPathContext:

    def __init__(self: "XPathContext", cnode: InstanceNode, origin: InstanceNode,
                 position: int, size: int):
        self.cnode = cnode
        self.origin = origin
        self.position = position
        self.size = size

    def update_cnode(self: "XPathContext", new_cnode: InstanceNode) -> "XPathContext":
        return self.__class__(new_cnode, self.origin, self.position, self.size)


class Expr:
    """Abstract class for nodes of XPath AST."""

    indent = 2
    _precedence = 8

    def __str__(self: "Expr") -> str:
        """Return a string representation of the receiver."""
        raise NotImplementedError

    def evaluate(self: "Expr", node: InstanceNode) -> XPathValue:
        """Evaluate the receiver and return the result.

        Args:
            node: Context node for XPath evaluation.

        Raises:
            XPathTypeError: If a subexpression of the receiver is of a wrong
                type.
        """
        return self._eval(XPathContext(node, node, 1, 1))

    def _eval_float(self: "Expr", xctx: XPathContext) -> float:
        val = self._eval(xctx)
        try:
            return float(val)
        except ValueError:
            return float('nan')

    def _eval_string(self: "Expr", xctx: XPathContext) -> str:
        val = self._eval(xctx)
        if isinstance(val, float):
            try:
                if int(val) == val:
                    return str(int(val))
            except OverflowError:
                return "Infinity" if val > 0 else "-Infinity"
            except ValueError:
                return "NaN"
        if isinstance(val, bool):
            return str(val).lower()
        return str(val)

    def _xfunc_name(self: "Expr") -> str:
        """Return XPath function name based on the class.

        To be used only for functions.
        """
        fn = self.__class__.__name__[4:]
        return fn[0].lower() + "".join(
            [(c if c.islower() else f"-{c.lower()}") for
             c in fn[1:]])

    def syntax_tree(self: "Expr", indent: int = 0) -> str:
        """Print abstract syntax tree of the receiver."""
        node_name = self.__class__.__name__
        attr = self._properties_str()
        attr_str = " (" + attr + ")\n" if attr else "\n"
        return (" " * indent + node_name + attr_str +
                self._children_ast(indent + self.indent))

    def as_instance_route(self: "Expr") -> InstanceRoute:
        """Convert receiver to an InstanceRoute."""
        raise NotImplementedError

    def _properties_str(self: "Expr") -> str:
        return ""

    def _children_ast(self: "Expr", indent) -> str:
        return ""

    def _predicates_str(self: "Expr", indent) -> str:
        if not self.predicates:
            return ""
        res = " " * indent + "-- Predicates:\n"
        newi = indent + 3
        for p in self.predicates:
            res += p.syntax_tree(newi)
        return res

    def _apply_predicates(self: "Expr", ns: XPathValue,
                          xctx: XPathContext) -> XPathValue:
        for p in self.predicates:
            res = NodeSet([])
            size = len(ns)
            for i in range(size):
                pval = p._eval(XPathContext(ns[i], xctx.origin, i + 1, size))
                try:
                    if isinstance(pval, float) and pval > 0:
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

    def __init__(self: "UnaryExpr", expr: Optional[Expr]):
        self.expr = expr

    def __str__(self: "UnaryExpr") -> str:
        """Return string representation of a unary function.

        Non-function subclasses should override this method.
        """
        return f"{self._xfunc_name()}({self.expr if self.expr else ''})"

    def _children_ast(self: "UnaryExpr", indent: int) -> str:
        return self.expr.syntax_tree(indent) if self.expr else ""


class BinaryExpr(Expr):
    """Abstract superclass of binary expressions."""

    def __init__(self: "BinaryExpr", left: Expr, right: Expr):
        self.left = left
        self.right = right

    def __str__(self: "BinaryExpr") -> str:
        """Return string representation of a binary function.

        Non-function subclasses should override this method.
        """
        return f"{self._xfunc_name()}({self.left}, {self.right})"

    def _children_ast(self: "BinaryExpr", indent: int) -> str:
        return self.left.syntax_tree(indent) + self.right.syntax_tree(indent)

    def _eval_ops(self: "BinaryExpr", xctx: XPathContext) -> tuple[XPathValue, XPathValue]:
        return (self.left._eval(xctx), self.right._eval(xctx))

    def _eval_ops_float(self: "BinaryExpr", xctx: XPathContext) -> tuple[float, float]:
        return (self.left._eval_float(xctx), self.right._eval_float(xctx))

    def _eval_ops_string(self: "BinaryExpr", xctx: XPathContext) -> tuple[str, str]:
        return (self.left._eval_string(xctx), self.right._eval_string(xctx))

    def _as_str(self: "BinaryExpr", op: str, spaces=True) -> str:
        lft = str(self.left)
        if self.left._precedence < self._precedence:
            lft = "(" + lft + ")"
        rt = str(self.right)
        if self.right._precedence < self._precedence:
            rt = "(" + rt + ")"
        sop = f" {op} " if spaces else op
        return f"{lft}{sop}{rt}"


class OrExpr(BinaryExpr):

    _precedence = 0

    def __str__(self: "OrExpr") -> str:
        return self._as_str("or")

    def _eval(self: "OrExpr", xctx: XPathContext) -> bool:
        return self.left._eval(xctx) or self.right._eval(xctx)


class AndExpr(BinaryExpr):

    _precedence = 1

    def __str__(self: "AndExpr") -> str:
        return self._as_str("and")

    def _eval(self: "AndExpr", xctx: XPathContext) -> bool:
        return self.left._eval(xctx) and self.right._eval(xctx)


class EqualityExpr(BinaryExpr):

    _precedence = 2

    def __init__(self: "EqualityExpr", left: Expr, right: Expr, negate: bool):
        super().__init__(left, right)
        self.negate = negate

    def __str__(self: "EqualityExpr") -> str:
        return self._as_str("!=" if self.negate else "=")

    def as_instance_route(self: "EqualityExpr") -> InstanceRoute:
        step = self.left

    def _properties_str(self: "EqualityExpr") -> str:
        return "!=" if self.negate else "="

    def _eval(self: "EqualityExpr", xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops(xctx)
        return lres != rres if self.negate else lres == rres


class RelationalExpr(BinaryExpr):

    _precedence = 3

    def __init__(self: "RelationalExpr", left: Expr, right: Expr, less: bool,
                 equal: bool):
        super().__init__(left, right)
        self.less = less
        self.equal = equal

    def __str__(self: "RelationalExpr") -> str:
        lg = "<" if self.less else ">"
        return self._as_str(lg + "=" if self.equal else lg)

    def _properties_str(self: "RelationalExpr") -> str:
        res = "<" if self.less else ">"
        if self.equal:
            res += "="
        return res

    def _eval(self: "RelationalExpr", xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops(xctx)
        if self.less:
            return lres <= rres if self.equal else lres < rres
        return lres >= rres if self.equal else lres > rres


class AdditiveExpr(BinaryExpr):

    _precedence = 4

    def __init__(self: "AdditiveExpr", left: Expr, right: Expr, plus: bool):
        super().__init__(left, right)
        self.plus = plus

    def __str__(self: "AdditiveExpr") -> str:
        return self._as_str("+" if self.plus else "-")

    def _properties_str(self: "AdditiveExpr") -> str:
        return "+" if self.plus else "-"

    def _eval(self: "AdditiveExpr", xctx: XPathContext) -> float:
        lres, rres = self._eval_ops_float(xctx)
        return lres + rres if self.plus else lres - rres


class MultiplicativeExpr(BinaryExpr):

    _precedence = 5

    def __init__(self: "MultiplicativeExpr", left: Expr, right: Expr,
                 operator: MultiplicativeOp):
        super().__init__(left, right)
        self.operator = operator

    def __str__(self: "MultiplicativeExpr") -> str:
        return self._as_str(str(self.operator))

    def _properties_str(self: "MultiplicativeExpr") -> str:
        if self.operator == MultiplicativeOp.multiply:
            return "*"
        if self.operator == MultiplicativeOp.divide:
            return "div"
        if self.operator == MultiplicativeOp.modulo:
            return "mod"

    def _eval(self: "MultiplicativeExpr", xctx: XPathContext) -> float:
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

    _precedence = 6

    def __init__(self: "UnaryMinusExpr", expr: Expr, negate: bool):
        super().__init__(expr)
        self.negate = negate

    def __str__(self: "UnaryMinusExpr") -> str:
        return f"{'-' if self.negate else ''}{self.expr}"

    def _properties_str(self: "UnaryMinusExpr") -> str:
        return "-" if self.negate else "+"

    def _eval(self: "UnaryMinusExpr", xctx: XPathContext) -> float:
        res = self.expr._eval_float(xctx)
        return -res if self.negate else res


class UnionExpr(BinaryExpr):

    _precedence = 7

    def __str__(self: "UnionExpr") -> str:
        return self._as_str("|")

    def _eval(self: "UnionExpr", xctx: XPathContext) -> NodeSet:
        lres, rres = self._eval_ops(xctx)
        return lres.union(rres)


class Literal(Expr):

    def __init__(self: "Literal", value: str):
        self.value = value

    def __str__(self: "Literal") -> str:
        return quoteattr(self.value)

    def _properties_str(self: "Literal") -> str:
        return self.value

    def _eval(self: "Literal", xctx: XPathContext) -> str:
        return self.value


class Number(Expr):

    def __init__(self: "Number", value: float):
        self.value = value

    def __str__(self: "Number") -> str:
        return str(self.value)

    def _properties_str(self: "Number") -> str:
        return str(self.value)

    def _eval(self: "Number", xctx: XPathContext) -> float:
        return float(self.value)


class PathExpr(BinaryExpr):

    def __str__(self: "PathExpr") -> str:
        return self._as_str("/", spaces=False)

    def _eval(self: "PathExpr", xctx: XPathContext) -> XPathValue:
        ns = self.left._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        res = NodeSet([])
        for n in ns:
            res = res.union(self.right._eval(xctx.update_cnode(n)))
        return res


class FilterExpr(Expr):

    def __init__(self: "FilterExpr", primary: Expr, predicates: list[Expr]):
        self.primary = primary
        self.predicates = predicates

    def __str__(self: "FilterExpr") -> str:
        return (str(self.primary) +
                "".join([f"[{p}]" for p in self.predicates]))

    def _children_ast(self: "FilterExpr", indent) -> str:
        return self.primary.syntax_tree(indent) + self._predicates_str(indent)

    def _eval(self: "FilterExpr", xctx: XPathContext) -> XPathValue:
        res = self.primary._eval(xctx)
        return self._apply_predicates(res, xctx)


class LocationPath(BinaryExpr):

    def _eval(self: "LocationPath", xctx: XPathContext) -> XPathValue:
        lres = self.left._eval(xctx)
        ns = lres.bind(self.right._node_trans())
        return self.right._apply_predicates(ns, xctx)

    def __str__(self: "LocationPath") -> str:
        sep = "" if isinstance(self.left, Root) else "/"
        return f"{self.left}{sep}{self.right}"

    def as_instance_route(self: "LocationPath") -> InstanceRoute:
        return InstanceRoute(self.left.as_instance_route() +
                             self.right.as_instance_route())


class Root(Expr):

    _precedence = 8

    def _eval(self: "Root", xctx: XPathContext) -> NodeSet:
        return NodeSet([xctx.cnode.top()])

    def __str__(self: "Root") -> str:
        return "/"

    def as_instance_route(self: "Root") -> InstanceRoute:
        return InstanceRoute([])


class Step(Expr):

    def __init__(self: "Step", axis: Axis, qname: QualName,
                 predicates: list[Expr]):
        self.axis = axis
        self.qname = qname
        self.predicates = predicates

    def __str__(self: "Step") -> str:
        if self.axis == Axis.descendant_or_self and self.qname is None:
            return ""
        if self.axis == Axis.self and self.qname is None:
            return "."
        if self.axis == Axis.parent and self.qname is None:
            return ".."
        if self.qname:
            qn = f"{self.qname[1]}:{self.qname[0]}"
        elif self.qname is None:
            qn = "node()"
        else:
            qn = "*"
        ax = f"{self.axis}::" if self.axis != Axis.child else ""
        prs = "".join([f"[{p}]" for p in self.predicates])
        return ax + qn + prs

    def as_instance_route(self: "Step") -> InstanceRoute:
        m = MemberName(*self.qname)
        if not(self.predicates): return InstanceRoute([m])
        p0 = self.predicates[0]
        if isinstance(p0, Number):  # entry index
            espec = EntryIndex(int(p0.value))
        elif p0.left.axis == Axis.self:  # leaf-list value
            espec = EntryValue(p0.right.value)
        else:                   # list keys
            ks = { p.left.qname: p.right.value for p in self.predicates }
            espec = EntryKeys(ks)
        return InstanceRoute([m, espec])

    def _properties_str(self: "Step") -> str:
        return f"{self.axis.name} {self.qname}"

    def _children_ast(self: "Step", indent) -> str:
        return self._predicates_str(indent)

    def _node_trans(self: "Step") -> NodeExpr:
        return {
            Axis.ancestor: lambda n, qn=self.qname: n._ancestors(qn),
            Axis.ancestor_or_self:
                lambda n, qn=self.qname: n._ancestors_or_self(qn),
            Axis.child: lambda n, qn=self.qname: n._children(qn),
            Axis.descendant: lambda n, qn=self.qname: n._descendants(qn),
            Axis.descendant_or_self:
                lambda n, qn=self.qname: n._descendants(qn, True),
            Axis.following_sibling:
                lambda n, qn=self.qname: n._following_siblings(qn),
            Axis.parent: (
                lambda n, qn=self.qname: [] if qn and qn != n.parent.qual_name
                else n._parent()),
            Axis.preceding_sibling:
                lambda n, qn=self.qname: n._preceding_siblings(qn),
            Axis.self:
                lambda n, qn=self.qname: [] if qn and qn != n.qual_name
                else [n],
        }[self.axis]

    def _eval(self: "Step", xctx: XPathContext) -> XPathValue:
        ns = NodeSet(self._node_trans()(xctx.cnode))
        return self._apply_predicates(ns, xctx)


class FuncBitIsSet(BinaryExpr):

    def _eval(self: "FuncBitIsSet", xctx: XPathContext) -> bool:
        ns = self.left._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        bit = self.right._eval_string(xctx)
        try:
            return bit in ns[0].value
        except (IndexError, TypeError):
            return False


class FuncBoolean(UnaryExpr):

    def _eval(self: "FuncBoolean", xctx: XPathContext) -> bool:
        val = self.expr._eval(xctx)
        if isinstance(val, float) and isnan(val):
            return False
        return bool(val)


class FuncCeiling(UnaryExpr):

    def _eval(self: "FuncCeiling", xctx: XPathContext) -> float:
        return float(ceil(self.expr._eval_float(xctx)))


class FuncConcat(Expr):

    def __init__(self: "FuncConcat", parts: list[Expr]):
        self.parts = parts

    def __str__(self: "FuncConcat") -> str:
        return f"concat({', '.join([str(p) for p in self.parts])})"

    def _children_ast(self: "FuncConcat", indent: int) -> str:
        return "".join([ex.syntax_tree(indent) for ex in self.parts])

    def _eval(self: "FuncConcat", xctx: XPathContext) -> str:
        return "".join([ex._eval_string(xctx) for ex in self.parts])


class FuncContains(BinaryExpr):

    def _eval(self: "FuncContains", xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops_string(xctx)
        return lres.find(rres) >= 0


class FuncCount(UnaryExpr):

    def _eval(self: "FuncCount", xctx: XPathContext) -> int:
        ns = self.expr._eval(xctx)
        if isinstance(ns, NodeSet):
            return float(len(ns))
        raise XPathTypeError(repr(ns))


class FuncCurrent(Expr):

    def _eval(self: "FuncCurrent", xctx: XPathContext) -> NodeSet:
        return NodeSet([xctx.origin])

    def __str__(self: "FuncCurrent") -> str:
        return "current()"


class FuncDeref(UnaryExpr):

    def _eval(self: "FuncDeref", xctx: XPathContext) -> NodeSet:
        ns = self.expr._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        ref = ns[0]
        return NodeSet(ref._deref())


class FuncDerivedFrom(BinaryExpr):

    def __init__(self: "FuncDerivedFrom", left: Expr, right: Expr, or_self: bool,
                 sctx: SchemaContext):
        super().__init__(left, right)
        self.or_self = or_self
        self.sctx = sctx

    def _xfunc_name(self: "FuncDerivedFrom") -> str:
        return ("derived-from-or-self" if self.or_self else "derived-from")

    def _properties_str(self: "FuncDerivedFrom") -> str:
        return ("OR-SELF, " if self.or_self
                else "") + self.sctx.schema_data.namespace(self.mid)

    def _eval(self: "FuncDerivedFrom", xctx: XPathContext) -> bool:
        ns = self.left._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        i = self.sctx.schema_data.translate_pname(
            self.right._eval_string(xctx), self.sctx.text_mid)
        for n in ns:
            if not n.schema_node._is_identityref():
                return False
            if self.or_self and n.value == i:
                return True
            if self.sctx.schema_data.is_derived_from(n.value, i):
                return True
        return False


class FuncEnumValue(UnaryExpr):

    def _eval(self: "FuncEnumValue", xctx: XPathContext) -> float:
        ns = self.expr._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        try:
            node = ns[0]
            return float(node.schema_node.type.enum[node.value])
        except (AttributeError, IndexError, KeyError):
            return float('nan')


class FuncFalse(Expr):

    def __str__(self: "FuncFalse") -> str:
        return "false()"

    def _eval(self: "FuncFalse", xctx: XPathContext) -> bool:
        return False


class FuncFloor(UnaryExpr):

    def _eval(self: "FuncFloor", xctx: XPathContext) -> float:
        return float(floor(self.expr._eval_float(xctx)))


class FuncLast(Expr):

    def __str__(self: "FuncLast") -> str:
        return "last()"

    def _eval(self: "FuncLast", xctx: XPathContext) -> int:
        return float(xctx.size)


class FuncName(UnaryExpr):

    def __init__(self: "FuncName", expr: Optional[Expr], local: bool):
        super().__init__(expr)
        self.local = local

    def __str__(self: "FuncName") -> str:
        fn = "local-name" if self.local else "name"
        return f"{fn}({self.expr if self.expr else ''})"

    def _properties_str(self: "FuncName") -> str:
        return "LOCAL" if self.local else ""

    def _eval(self: "FuncName", xctx: XPathContext) -> str:
        if self.expr is None:
            node = xctx.cnode
        else:
            ns = self.expr._eval(xctx)
            try:
                node = ns[0]
            except TypeError:
                raise XPathTypeError(str(ns))
            except IndexError:
                return ""
        if node.parinst is None:
            return ""
        if self.local:
            p, s, loc = node.name.partition(":")
            return loc if s else p
        return node.name


class FuncNormalizeSpace(UnaryExpr):

    def _eval(self: "FuncNormalizeSpace", xctx: XPathContext) -> str:
        string = self.expr._eval_string(xctx) if self.expr else str(xctx.cnode)
        return " ".join(string.strip().split())


class FuncNot(UnaryExpr):

    def _eval(self: "FuncNot", xctx: XPathContext) -> bool:
        return not(self.expr._eval(xctx))


class FuncNumber(UnaryExpr):

    def _eval(self: "FuncNumber", xctx: XPathContext) -> float:
        if self.expr is None:
            try:
                return float(xctx.cnode.value)
            except ValueError:
                return float('nan')
        return self.expr._eval_float(xctx)


class FuncPosition(Expr):

    def __str__(self: "FuncPosition") -> str:
        return "position()"

    def _eval(self: "FuncPosition", xctx: XPathContext) -> int:
        return xctx.position


class FuncReMatch(BinaryExpr):

    def _eval(self: "FuncReMatch", xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops_string(xctx)
        try:
            return re.match(translate_pattern(
                rres, back_references=False,
                lazy_quantifiers=False, anchors=False), lres) is not None
        except RegexError:
            raise InvalidArgument(rres) from None


class FuncRound(UnaryExpr):

    def _eval(self: "FuncRound", xctx: XPathContext) -> float:
        dec = decimal.Decimal(self.expr._eval_float(xctx))
        try:
            return float(dec.to_integral_value(
                decimal.ROUND_HALF_UP if dec > 0 else decimal.ROUND_HALF_DOWN))
        except decimal.InvalidOperation:
            return float('nan')


class FuncStartsWith(BinaryExpr):

    def _eval(self: "FuncStartsWith", xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops_string(xctx)
        return lres.startswith(rres)


class FuncString(UnaryExpr):

    def _eval(self: "FuncString", xctx: XPathContext) -> str:
        if self.expr is None:
            return str(xctx.cnode)
        return self.expr._eval_string(xctx)


class FuncStringLength(UnaryExpr):

    def _eval(self: "FuncStringLength", xctx: XPathContext) -> str:
        string = self.expr._eval_string(xctx) if self.expr else str(xctx.cnode)
        return float(len(string))


class FuncSubstring(BinaryExpr):

    def __init__(self: "FuncSubstring", string: Expr, start: Expr,
                 length: Optional[Expr]):
        super().__init__(string, start)
        self.length = length

    def __str__(self: "FuncSubstring") -> str:
        res = f"{self._xfunc_name()}({self.left}, {self.right}"
        if self.length:
            res += f", {self.length}"
        return res + ")"

    def _children_ast(self: "FuncSubstring", indent: int) -> str:
        return super()._children_ast(indent) + self.length.syntax_tree(indent)

    def _eval(self: "FuncSubstring", xctx: XPathContext) -> str:
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

    def _eval(self: "FuncSubstringAfter", xctx: XPathContext) -> str:
        lres, rres = self._eval_ops_string(xctx)
        ind = lres.find(rres)
        return lres[ind + len(rres):] if ind >= 0 else ""


class FuncSubstringBefore(BinaryExpr):

    def _eval(self: "FuncSubstringBefore", xctx: XPathContext) -> str:
        lres, rres = self._eval_ops_string(xctx)
        ind = lres.find(rres)
        return lres[:ind] if ind >= 0 else ""


class FuncSum(UnaryExpr):

    def _eval(self: "FuncSum", xctx: XPathContext) -> float:
        ns = self.expr._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        try:
            return float(sum([n.value for n in ns]))
        except TypeError:
            return float('nan')


class FuncTranslate(BinaryExpr):

    def __init__(self: "FuncTranslate", s1: Expr, s2: Expr, s3: Expr):
        super().__init__(s1, s2)
        self.nchars = s3

    def __str__(self: "FuncTranslate") -> str:
        return f"{self._xfunc_name()}({self.left}, {self.right}, {self.nchars})"

    def _children_ast(self: "FuncTranslate", indent: int) -> str:
        return super()._children_ast(indent) + self.nchars.syntax_tree(indent)

    def _eval(self: "FuncTranslate", xctx: XPathContext) -> str:
        string, old = self._eval_ops_string(xctx)
        new = self.nchars._eval_string(xctx)[:len(old)]
        ttab = str.maketrans(old[:len(new)], new, old[len(new):])
        return string.translate(ttab)


class FuncTrue(Expr):

    def __str__(self: "FuncTrue") -> str:
        return "true()"

    def _eval(self: "FuncTrue", xctx: XPathContext) -> bool:
        return True
