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

"""Parser for XPath 1.0 expressions.

This module defines the following classes:

* XPathParser: Recursive descent parser for XPath expressions.

The module also defines the following exceptions:

"""

from typing import List, Optional, Tuple, Union
from .schemadata import SchemaContext
from .enumerations import Axis, MultiplicativeOp
from .exceptions import EndOfInput, InvalidXPath, NotSupported, UnexpectedInput
from .parser import Parser
from .typealiases import *
from .xpathast import *

class XPathParser(Parser):
    """Parser for XPath expressions."""

    def __init__(self, text: str, sctx: SchemaContext):
        """Initialize the parser instance.

        Args:
            sctx: Schema context for XPath expression parsing.
        """
        super().__init__(text)
        self.sctx = sctx

    def parse(self) -> Expr:
        """Parse an XPath expression.

        Returns:
            A node of the XPath AST.

        Raises:
            InvalidXPath: If the input XPath expression is invalid.
            NotSupported: If the input XPath expression contains a feature
                that isn't supported by the implementation.
        """
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
            next == "." and "0" <= self.input[self.offset + 1] <= "9"):
            val = self.unsigned_float()
            self.skip_ws()
            return Number(val)
        start = self.offset
        try:
            fname = self.yang_identifier()
        except UnexpectedInput:
            return self._location_path()
        self.skip_ws()
        if self.test_string("(") and fname not in (
                "node", "comment", "processing-instruction", "text"):
            self.skip_ws()
            return self._path_expr(fname)
        self.offset = start
        return self._location_path()

    def _path_expr(self, fname: str) -> Expr:
        fexpr = self._filter_expr(fname)
        if self.test_string("/"):
            return PathExpr(fexpr, self._location_path())
        return fexpr

    def _filter_expr(self, fname: str) -> Expr:
        if fname is None:
            prim = self._or_expr()
        else:
            mname = "_func_" + fname.replace("-", "_")
            try:
                prim = getattr(self, mname)()
            except AttributeError:
                if fname in ("id", "lang", "namespace-uri"):
                    raise NotSupported(self,
                        "function '{}()'".format(fname)) from None
                raise InvalidXPath(self) from None
        self.char(")")
        self.skip_ws()
        return FilterExpr(prim, self._predicates())

    def _predicates(self) -> List[Expr]:
        res = []
        while self.test_string("["):
            self.skip_ws()
            res.append(self._predicate())
            self.char("]")
            self.skip_ws()
        return res

    def _predicate(self) -> Expr:
        return self._or_expr()

    def _location_path(self) -> LocationPath:
        if self.test_string("/"):
            self.skip_ws()
            if self.at_end(): return Root()
            op1 = LocationPath(Root(), self._step())
        else:
            op1 = self._step()
        while self.test_string("/"):
            self.skip_ws()
            op2 = self._step()
            op1 = LocationPath(op1, op2)
        return op1

    def _step(self) -> Step:
        return Step(*self._axis_qname(), self._predicates())

    def _axis_qname(self) -> Tuple[Axis, Union[QualName, bool, None]]:
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
            return (Axis.child, (yid, None))
        if next == "(":
            return (Axis.child, self._node_type(yid))
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
                        raise NotSupported(
                            self, "axis '{}::'".format(yid)) from None
                    raise InvalidXPath(self) from None
                return (axis, self._qname())
            if ws:
                raise InvalidXPath(self)
            nsp = self.sctx.schema_data.prefix2ns(yid, self.sctx.text_mid)
            loc = self.yang_identifier()
            self.skip_ws()
            return (Axis.child, (loc, nsp))
        return (Axis.child, (yid, None))

    def _node_type(self, typ):
        if typ == "node":
            self.adv_skip_ws()
            self.char(")")
            self.skip_ws()
            return None
        elif typ in ("comment", "processing-instruction", "text"):
            raise NotSupported(self, "node type '{}()'".format(typ))
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
            return (ident, None)
        if next == "(":
            return self._node_type(ident)
        if not ws and self.test_string(":"):
            res = (
                self.yang_identifier(),
                self.sctx.schema_data.prefix2ns(ident, self.sctx.text_mid))
        else:
            res = (ident, None)
        self.skip_ws()
        return res

    def _opt_arg(self) -> Optional[Expr]:
        return None if self.peek() == ")" else self.parse()

    def _two_args(self) -> Tuple[Expr]:
        fst = self.parse()
        self.char(",")
        self.skip_ws()
        return (fst, self.parse())

    def _func_bit_is_set(self) -> FuncBitIsSet:
        return FuncBitIsSet(*self._two_args())

    def _func_boolean(self) -> FuncBoolean:
        return FuncBoolean(self.parse())

    def _func_ceiling(self) -> FuncCeiling:
        return FuncCeiling(self.parse())

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

    def _func_deref(self) -> FuncDeref:
        return FuncDeref(self.parse())

    def _func_derived_from(self) -> FuncDerivedFrom:
        return FuncDerivedFrom(*self._two_args(), False, self.sctx)

    def _func_derived_from_or_self(self) -> FuncDerivedFrom:
        return FuncDerivedFrom(*self._two_args(), True, self.sctx)

    def _func_enum_value(self) -> FuncEnumValue:
        return FuncEnumValue(self.parse())

    def _func_false(self) -> FuncFalse:
        return FuncFalse()

    def _func_floor(self) -> FuncFloor:
        return FuncFloor(self.parse())

    def _func_last(self) -> FuncLast:
        return FuncLast()

    def _func_local_name(self) -> FuncName:
        return FuncName(self._opt_arg(), local=True)

    def _func_name(self) -> FuncName:
        return FuncName(self._opt_arg(), local=False)

    def _func_normalize_space(self) -> FuncNormalizeSpace:
        return FuncNormalizeSpace(self._opt_arg())

    def _func_not(self) -> FuncNot:
        return FuncNot(self.parse())

    def _func_number(self) -> FuncNumber:
        return FuncNumber(self._opt_arg())

    def _func_position(self) -> FuncPosition:
        return FuncPosition()

    def _func_re_match(self) -> FuncReMatch:
        return FuncReMatch(*self._two_args())

    def _func_round(self) -> FuncRound:
        return FuncRound(self.parse())

    def _func_starts_with(self) -> FuncStartsWith:
        return FuncStartsWith(*self._two_args())

    def _func_string(self) -> FuncString:
        return FuncString(self._opt_arg())

    def _func_string_length(self) -> FuncStringLength:
        return FuncStringLength(self._opt_arg())

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

    def _func_sum(self) -> FuncSum:
        return FuncSum(self.parse())

    def _func_translate(self) -> FuncTranslate:
        s1, s2 = self._two_args()
        self.char(",")
        self.skip_ws()
        return FuncTranslate(s1, s2, self.parse())

    def _func_true(self) -> FuncTrue:
        return FuncTrue()
