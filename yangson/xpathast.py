# Copyright © 2016, 2017 CZ.NIC, z. s. p. o.
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
# You should have received a copy of the GNU Lesser General Public License along
# with Yangson.  If not, see <http://www.gnu.org/licenses/>.

"""Abstract syntax tree for XPath 1.0 expressions with YANG extensions.

This module defines a number of classes that mostly correspond to
variables (non-terminals) of the XPath 1.0 grammar. Only the following
class is intended to be public:

* Expr: XPath 1.0 expression with YANG 1.1 extensions.
"""

import decimal
from math import ceil, copysign, floor
from pyxb.utils.xmlre import XMLToPython
import re
from typing import List, Optional, Tuple
from .schemadata import SchemaContext
from .enumerations import Axis, MultiplicativeOp
from .exceptions import XPathTypeError
from .instance import InstanceNode
from .nodeset import NodeExpr, NodeSet, XPathValue
from .typealiases import *

class XPathContext:

    def __init__(self, cnode: InstanceNode, origin: InstanceNode,
                 position: int, size: int):
        self.cnode = cnode
        self.origin = origin
        self.position = position
        self.size = size

    def update_cnode(self, new_cnode: InstanceNode) -> "XPathContext":
        return self.__class__(new_cnode, self.origin, self.position, self.size)

class Expr:
    """Abstract class for nodes of XPath AST."""

    indent = 2

    def __str__(self) -> str:
        """Return a string representation of the receiver's AST."""
        return self._tree()

    def evaluate(self, node: InstanceNode) -> XPathValue:
        """Evaluate the receiver and return the result.

        Args:
            node: Context node for XPath evaluation.

        Raises:
            XPathTypeError: If a subexpression of the receiver is of a wrong
                type.
        """
        return self._eval(XPathContext(node, node, 1, 1))

    def _eval_float(self, xctx: XPathContext) -> float:
        val = self._eval(xctx)
        try:
            return float(val)
        except ValueError:
            return float('nan')

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

    def _tree(self, indent: int = 0) -> str:
        node_name = self.__class__.__name__
        attr = self._properties_str()
        attr_str  = " (" + attr + ")\n" if attr else "\n"
        return (" " * indent + node_name + attr_str +
                self._children_str(indent + self.indent))

    def _properties_str(self) -> str:
        return ""

    def _children_str(self, indent) -> str:
        return ""

    def _predicates_str(self, indent) -> str:
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

    def __init__(self, expr: Optional[Expr]):
        self.expr = expr

    def _children_str(self, indent: int) -> str:
        return self.expr._tree(indent) if self.expr else ""

class BinaryExpr(Expr):
    """Abstract superclass of binary expressions."""

    def __init__(self, left: Expr, right: Expr):
        self.left = left
        self.right = right

    def _children_str(self, indent: int) -> str:
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

    def __init__(self, left: Expr, right: Expr, negate: bool):
        super().__init__(left, right)
        self.negate = negate

    def _properties_str(self) -> str:
        return "!=" if self.negate else "="

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops(xctx)
        return lres != rres if self.negate else lres == rres

class RelationalExpr(BinaryExpr):

    def __init__(self, left: Expr, right: Expr, less: bool,
                 equal: bool):
        super().__init__(left, right)
        self.less = less
        self.equal = equal

    def _properties_str(self) -> str:
        res = "<" if self.less else ">"
        if self.equal: res += "="
        return res

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops(xctx)
        if self.less:
            return lres <= rres if self.equal else lres < rres
        return lres >= rres if self.equal else lres > rres

class AdditiveExpr(BinaryExpr):

    def __init__(self, left: Expr, right: Expr, plus: bool):
        super().__init__(left, right)
        self.plus = plus

    def _properties_str(self) -> str:
        return "+" if self.plus else "-"

    def _eval(self, xctx: XPathContext) -> float:
        lres, rres = self._eval_ops_float(xctx)
        return lres + rres if self.plus else lres - rres

class MultiplicativeExpr(BinaryExpr):

    def __init__(self, left: Expr, right: Expr,
                 operator: MultiplicativeOp):
        super().__init__(left, right)
        self.operator = operator

    def _properties_str(self) -> str:
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

    def _properties_str(self) -> str:
        return "-" if self.negate else "+"

    def _eval(self, xctx: XPathContext) -> float:
        res = self.expr._eval_float(xctx)
        return -res if self.negate else res

class UnionExpr(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> NodeSet:
        lres, rres = self._eval_ops(xctx)
        return lres.union(rres)

class Literal(Expr):

    def __init__(self, value: str):
        self.value = value

    def _properties_str(self) -> str:
        return self.value

    def _eval(self, xctx: XPathContext) -> str:
        return self.value

class Number(Expr):

    def __init__(self, value: float):
        self.value = value

    def _properties_str(self) -> str:
        return str(self.value)

    def _eval(self, xctx: XPathContext) -> float:
        return float(self.value)

class PathExpr(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> XPathValue:
        ns = self.left._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        res = NodeSet([])
        for n in ns:
            res = res.union(self.right._eval(xctx.update_cnode(n)))
        return res

class FilterExpr(Expr):

    def __init__(self, primary: Expr, predicates: List[Expr]):
        self.primary = primary
        self.predicates = predicates

    def _children_str(self, indent) -> str:
        return self.primary._tree(indent) + self._predicates_str(indent)

    def _eval(self, xctx: XPathContext) -> XPathValue:
        res = self.primary._eval(xctx)
        return self._apply_predicates(res, xctx)

class LocationPath(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> XPathValue:
        lres = self.left._eval(xctx)
        ns = lres.bind(self.right._node_trans(xctx))
        return self.right._apply_predicates(ns, xctx)

class Root(Expr):

    def _eval(self, xctx: XPathContext) -> NodeSet:
        return NodeSet([xctx.cnode.top()])

class Step(Expr):

    def __init__(self, axis: Axis, qname: QualName,
                 predicates: List[Expr]):
        self.axis = axis
        self.qname = qname
        self.predicates = predicates

    def _properties_str(self) -> str:
        return "{} {}".format(self.axis.name, self.qname)

    def _children_str(self, indent) -> str:
        return self._predicates_str(indent)

    def _node_trans(self, xctx) -> NodeExpr:
        qname = ((self.qname[0], xctx.origin.namespace) if
                     self.qname and self.qname[1] is None else self.qname)
        return {
            Axis.ancestor: lambda n, qn=qname: n._ancestors(qn),
            Axis.ancestor_or_self:
                lambda n, qn=qname: n._ancestors_or_self(qn),
            Axis.child: lambda n, qn=qname: n._children(qn),
            Axis.descendant: lambda n, qn=qname: n._descendants(qn),
            Axis.descendant_or_self:
                lambda n, qn=qname: n._descendants(qn, True),
            Axis.following_sibling:
                lambda n, qn=qname: n._following_siblings(qn),
            Axis.parent: (
                lambda n, qn=qname: [] if qn and qn != n.parent.qual_name
                else n._parent()),
            Axis.preceding_sibling:
                lambda n, qn=qname: n._preceding_siblings(qn),
            Axis.self:
                lambda n, qn=qname: [] if qn and qn != n.qual_name else [n],
                }[self.axis]

    def _eval(self, xctx: XPathContext) -> XPathValue:
        ns = NodeSet(self._node_trans(xctx)(xctx.cnode))
        return self._apply_predicates(ns, xctx)

class FuncBitIsSet(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        ns = self.left._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        bit = self.right._eval_string(xctx)
        try:
            return bit in ns[0].value
        except (IndexError, TypeError):
            return False

class FuncBoolean(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        return bool(self.expr._eval(xctx))

class FuncCeiling(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> float:
        return float(ceil(self.expr._eval_float(xctx)))

class FuncConcat(Expr):

    def __init__(self, parts: List[Expr]):
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

class FuncDeref(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> NodeSet:
        ns = self.expr._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        ref = ns[0]
        return NodeSet(ref._deref())

class FuncDerivedFrom(BinaryExpr):

    def __init__(self, left: Expr, right: Expr, or_self: bool,
                 sctx: SchemaContext):
        super().__init__(left, right)
        self.or_self = or_self
        self.sctx = sctx

    def _properties_str(self) -> str:
        return ("OR-SELF, " if self.or_self
                else "") + self.sctx.schema_data.namespace(self.mid)

    def _eval(self, xctx: XPathContext) -> bool:
        ns = self.left._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        i = self.sctx.schema_data.translate_pname(
            self.right._eval_string(xctx), self.sctx.text_mid)
        for n in ns:
            if not n.schema_node._is_identityref(): return False
            if self.or_self and n.value == i: return True
            if self.sctx.schema_data.is_derived_from(n.value, i):
                return True
        return False

class FuncEnumValue(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> float:
        ns = self.expr._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        try:
            node = ns[0]
            return float(node.schema_node.type.enum[node.value])
        except (AttributeError, IndexError, KeyError):
            return float('nan')

class FuncFalse(Expr):

    def _eval(self, xctx: XPathContext) -> bool:
        return False

class FuncFloor(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> float:
        return float(floor(self.expr._eval_float(xctx)))

class FuncLast(Expr):

    def _eval(self, xctx: XPathContext) -> int:
        return float(xctx.size)

class FuncName(UnaryExpr):

    def __init__(self, expr: Optional[Expr], local: bool):
        super().__init__(expr)
        self.local = local

    def _properties_str(self) -> str:
        return "LOCAL" if self.local else ""

    def _eval(self, xctx: XPathContext) -> str:
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
        if node.path is (): return ""
        if self.local:
            p, s, loc = node.name.partition(":")
            return loc if s else p
        return node.name

class FuncNormalizeSpace(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> str:
        string = self.expr._eval_string(xctx) if self.expr else str(xctx.cnode)
        return " ".join(string.strip().split())

class FuncNot(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        return not(self.expr._eval(xctx))

class FuncNumber(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> float:
        if self.expr is None:
            try:
                return float(xctx.cnode.value)
            except ValueError:
                return float('nan')
        return self.expr._eval_float(xctx)

class FuncPosition(Expr):

    def _eval(self, xctx: XPathContext) -> int:
        return xctx.position

class FuncReMatch(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops_string(xctx)
        try:
            return re.match(XMLToPython(rres), lres) is not None
        except:
            raise InvalidArgument(rres) from None

class FuncRound(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> float:
        dec = decimal.Decimal(self.expr._eval_float(xctx))
        try:
            return float(dec.to_integral_value(
                decimal.ROUND_HALF_UP if dec > 0 else decimal.ROUND_HALF_DOWN))
        except decimal.InvalidOperation:
            return float('nan')

class FuncStartsWith(BinaryExpr):

    def _eval(self, xctx: XPathContext) -> bool:
        lres, rres = self._eval_ops_string(xctx)
        return lres.startswith(rres)

class FuncString(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> str:
        if self.expr is None:
            return str(xctx.cnode)
        return self.expr._eval_string(xctx)

class FuncStringLength(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> str:
        string = self.expr._eval_string(xctx) if self.expr else str(xctx.cnode)
        return float(len(string))

class FuncSubstring(BinaryExpr):

    def __init__(self, string: Expr, start: Expr,
                 length: Optional[Expr]):
        super().__init__(string, start)
        self.length = length

    def _children_str(self, indent: int) -> str:
        return super()._children_str(indent) + self.length._tree(indent)

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

class FuncSum(UnaryExpr):

    def _eval(self, xctx: XPathContext) -> float:
        ns = self.expr._eval(xctx)
        if not isinstance(ns, NodeSet):
            raise XPathTypeError(str(ns))
        try:
            return float(sum([n.value for n in ns]))
        except TypeError:
            return float('nan')

class FuncTranslate(BinaryExpr):

    def __init__(self, s1: Expr, s2: Expr, s3: Expr):
        super().__init__(s1, s2)
        self.nchars = s3

    def _children_str(self, indent: int) -> str:
        return super()._children_str(indent) + self.nchars._tree(indent)

    def _eval(self, xctx: XPathContext) -> str:
        string, old = self._eval_ops_string(xctx)
        new = self.nchars._eval_string(xctx)[:len(old)]
        ttab = str.maketrans(old[:len(new)], new, old[len(new):])
        return string.translate(ttab)

class FuncTrue(Expr):

    def _eval(self, xctx: XPathContext) -> bool:
        return True
