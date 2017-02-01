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

"""Classes representing YANG data types.

This module implements the following classes:

* BitsType: YANG bits type.
* BinaryType: YANG binary type.
* BooleanType: YANG boolean type.
* DataType: Abstract class for data types.
* Decimal64Type: YANG decimal64 type.
* EmptyType: YANG empty type.
* EnumerationType: YANG enumeration type.
* IdentityrefType: YANG identityref type.
* InstanceIdentifierType: YANG instance-identifier type.
* LeafrefType: YANG leafref type.
* LinkType: Abstract class for data types representing links.
* IntegralType: Abstract class for integral types.
* Int8Type: YANG int8 type.
* Int16Type: YANG int16 type.
* Int32Type: YANG int32 type.
* Int64Type: YANG int64 type.
* NumericType: Abstract class for numeric types.
* StringType: YANG string type.
* Uint8Type: YANG uint8 type.
* Uint16Type: YANG uint16 type.
* Uint32Type: YANG uint32 type.
* Uint64Type: YANG uint64 type.
* UnionType: YANG union type.

The module also defines the following exceptions:

* YangTypeError: A scalar value is of incorrect type.
"""

import base64
import decimal
import numbers
import re
from pyxb.utils.xmlre import XMLToPython
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from .exceptions import YangsonException
from .schemadata import SchemaContext
from .instance import InstanceNode, InstanceIdParser, InstanceRoute
from .parser import ParserException
from .statement import Statement
from .typealiases import *
from .typealiases import _Singleton
from .xpathparser import XPathParser

# Local type aliases
Range = List[List[Union[int, decimal.Decimal]]]

class DataType:
    """Abstract class for YANG data types."""

    _option_template = '<option value="{}"{}>{}</option>'

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        self.sctx = sctx
        self.default = None
        self.name = name

    def __str__(self):
        """Return YANG name of the receiver type."""
        base = self.yang_type()
        return "{}({})".format(self.name, base) if self.name else base

    def from_raw(self, raw: RawScalar) -> ScalarValue:
        """Return a cooked value of the receiver type.

        Args:
            raw: Raw value obtained from JSON parser.

        Raises:
            YangTypeError: If `raw` doesn't conform to the receiver.
        """
        try:
            res = self._convert_raw(raw)
            if res is not None and self._constraints(res): return res
        except TypeError:
            raise YangTypeError(self, raw) from None
        raise YangTypeError(self, raw)

    def to_raw(self, val: ScalarValue) -> RawScalar:
        """Return a raw value ready to be serialized in JSON."""
        return val

    def parse_value(self, text: str) -> ScalarValue:
        """Parse value of a data type.

        Args:
            text: String representation of the value.
        """
        res = self._parse(text)
        if res is not None and self._constraints(res): return res
        raise YangTypeError(self, text)

    def canonical_string(self, val: ScalarValue) -> str:
        """Return canonical form of a value."""
        return str(val)

    def from_yang(self, text: str, sctx: SchemaContext) -> ScalarValue:
        """Parse value specified in a YANG module."""
        return self.parse_value(text)

    def contains(self, val: ScalarValue) -> bool:
        """Return ``True`` if the receiver type contains `val`."""
        try:
            return self._constraints(val)
        except TypeError:
            return False

    def yang_type(self) -> YangIdentifier:
        """Return YANG name of the receiver."""
        return self.__class__.__name__[:-4].lower()

    def _convert_raw(self, raw: RawScalar) -> ScalarValue:
        """Return a cooked value."""
        return raw

    def _constraints(self, val: Any) -> bool:
        return True

    @classmethod
    def _resolve_type(cls, stmt: Statement, sctx: SchemaContext) -> "DataType":
        typ = stmt.argument
        if typ in cls.dtypes:
            res = cls.dtypes[typ](sctx, None)
            res._handle_properties(stmt, sctx)
        else:
            p, s, loc = typ.partition(":")
            res = cls._derived_type(stmt, sctx, loc if s else typ)
        return res

    @classmethod
    def _derived_type(cls, stmt: Statement, sctx: SchemaContext,
                          name: YangIdentifier) -> "DataType":
        tchain = []
        ts = stmt
        sc = sctx
        while True:
            tdef, sc = sctx.schema_data.get_definition(ts, sc)
            ts = tdef.find1("type", required=True)
            tchain.append((tdef, ts, sc))
            if ts.argument in cls.dtypes: break
        res = cls.dtypes[ts.argument](sctx, name)
        btyp = True
        while tchain:
            tdef, typst, tsc = tchain.pop()
            if btyp:
                res._handle_properties(ts, sc)
                btyp = False
            else:
                res._handle_restrictions(typst, tsc)
            dfst = tdef.find1("default")
            if dfst:
                res.default = res.from_yang(dfst.argument, tsc)
        res._handle_restrictions(stmt, sctx)
        return res

    @staticmethod
    def _in_range(num: Union[int, decimal.Decimal], rng: Range) -> bool:
        """Decide whether a number fits into a range.

        Args:
            num: A number.
            rng: Numeric range.
        """
        for r in rng:
            if len(r) == 1:
                if r[0] == num: return True
            elif r[0] <= num <= r[1]: return True
        return False

    @staticmethod
    def _combine_ranges(orig: Range, rex: str,
                       parser: Callable[[str], Any]) -> Range:
        """Combine original range with a new one specified in `rex`.

        Args:
            orig: Original range.
            rex: Range expression.
        """
        to_num = lambda xs: [ parser(x) for x in xs ]
        lo = orig[0][0]
        hi = orig[-1][-1]
        parts = [ p.strip() for p in rex.split("|") ]
        ran = [ [ i.strip() for i in p.split("..") ] for p in parts ]
        if ran[0][0] != "min":
            lo = parser(ran[0][0])
        if ran[-1][-1] != "max":
            hi = parser(ran[-1][-1])
        return (
            [[lo, hi]] if len(ran) == 1 else
            [[lo, parser(ran[0][-1])]] +
            [ to_num(r) for r in ran[1:-1] ] +
            [[parser(ran[-1][0]), hi]])

    def _parse(self, text: str) -> Optional[ScalarValue]:
        return self._convert_raw(text)

    def _deref(self, node: InstanceNode) -> List[InstanceNode]:
        return []

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        """Handle type substatements."""
        self._handle_restrictions(stmt, sctx)

    def _handle_restrictions(self, stmt: Statement, sctx: SchemaContext) -> None:
        """Handle type restriction substatements."""
        pass

class EmptyType(DataType, metaclass=_Singleton):
    """Singleton class representing YANG "empty" type."""

    def canonical_string(self, val: Tuple[None]) -> str:
        return ""

    def _constraints(self, val: Tuple[None]) -> bool:
        return val == (None,)

    def _parse(self, text: str) -> Tuple[None]:
        return None if text else (None,)

    def _convert_raw(self, raw: List[None]) -> Tuple[None]:
        try:
            return tuple(raw)
        except TypeError:
            return None

class BitsType(DataType):
    """Class representing YANG "bits" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.bit = {}

    def sorted_bits(self) -> List[Tuple[str, int]]:
        """Return list of bit items sorted by position."""
        return sorted(self.bit.items(), key=lambda x: x[1])

    def _convert_raw(self, raw: str) -> Tuple[str]:
        try:
            return tuple(raw.split())
        except AttributeError:
            return None

    def _constraints(self, val: Tuple[str]) -> bool:
        for b in val:
            if b not in self.bit: return False
        return True

    def to_raw(self, val: Tuple[str]) -> str:
        return self.canonical_string(val)

    def as_int(self, val: Tuple[str]) -> int:
        """Transform a "bits" value to an integer."""
        res = 0
        try:
            for b in val:
                res += 1 << self.bit[b]
        except KeyError:
            raise YangTypeError(self, val) from None
        return res

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        """Handle **bit** statements."""
        nextpos = 0
        for bst in stmt.find_all("bit"):
            if not sctx.schema_data.if_features(bst, sctx.text_mid):
                continue
            label = bst.argument
            pst = bst.find1("position")
            if pst:
                pos = int(pst.argument)
                self.bit[label] = pos
                if pos > nextpos:
                    nextpos = pos
            else:
                self.bit[label] = nextpos
            nextpos += 1

    def _handle_restrictions(self, stmt: Statement, sctx: SchemaContext) -> None:
        bst = stmt.find_all("bit")
        if not bst: return
        new = set([b.argument for b in bst if
                        sctx.schema_data.if_features(b, sctx.text_mid)])
        for bit in set(self.bit) - new:
            del self.bit[bit]

    def canonical_string(self, val: Tuple[str]) -> str:
        try:
            items = [(self.bit[b], b) for b in val]
        except KeyError:
            raise YangTypeError(self, val) from None
        items.sort()
        return " ".join([x[1] for x in items])
        
class BooleanType(DataType):
    """Class representing YANG "boolean" type."""

    def _constraints(self, val: bool) -> bool:
        return isinstance(val, bool)

    def _parse(self, text: str) -> bool:
        """Parse boolean value.

        Args:
            text: String representation of the value.
        """
        if text == "true": return True
        if text == "false": return False

    def canonical_string(self, val: bool) -> str:
        if val is True: return "true"
        if val is False: return "false"
        raise YangTypeError(self, val)

class StringType(DataType):
    """Class representing YANG "string" type."""

    length = [[0, 4294967295]] # type: Range

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.patterns = [] # type: List[Pattern]
        self.invert_patterns = [] # type: List[Pattern]

    def _handle_restrictions(self, stmt: Statement, sctx: SchemaContext) -> None:
        lstmt = stmt.find1("length")
        if lstmt:
            self.length = self._combine_ranges(self.length,
                                                lstmt.argument, int)
        for pst in stmt.find_all("pattern"):
            pat = re.compile(XMLToPython(pst.argument))
            if pst.find1("modifier", "invert-match"):
                self.invert_patterns.append(pat)
            else:
                self.patterns.append(pat)

    def _constraints(self, val: str) -> bool:
        if not (isinstance(val, str) and self._in_range(len(val), self.length)):
            return False
        for p in self.patterns:
            if not p.match(val): return False
        for p in self.invert_patterns:
            if p.match(val): return False
        return True

class BinaryType(StringType):
    """Class representing YANG "binary" type."""

    def _convert_raw(self, raw: str) -> bytes:
        try:
            return base64.b64decode(raw, validate=True)
        except TypeError:
            return None

    def _constraints(self, val: bytes) -> bool:
        return isinstance(val, bytes) and self._in_range(len(val), self.length)

    def to_raw(self, val: bytes) -> str:
        return self.canonical_string(val)

    def canonical_string(self, val: bytes) -> str:
        return base64.b64encode(val).decode("ascii")

class EnumerationType(DataType):
    """Class representing YANG "enumeration" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.enum = {} # type: Dict[str, int]

    def sorted_enums(self) -> List[Tuple[str, int]]:
        """Return list of enum items sorted by value."""
        return sorted(self.enum.items(), key=lambda x: x[1])

    def _constraints(self, val: str) -> bool:
        return val in self.enum

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        """Handle **enum** statements."""
        nextval = 0
        for est in stmt.find_all("enum"):
            if not sctx.schema_data.if_features(est, sctx.text_mid):
                continue
            label = est.argument
            vst = est.find1("value")
            if vst:
                val = int(vst.argument)
                self.enum[label] = val
                if val > nextval:
                    nextval = val
            else:
                self.enum[label] = nextval
            nextval += 1

    def _handle_restrictions(self, stmt: Statement, sctx: SchemaContext) -> None:
        est = stmt.find_all("enum")
        if not est: return
        new = set([ e.argument for e in est if
                        sctx.schema_data.if_features(e, sctx.text_mid) ])
        for en in set(self.enum) - new:
            del self.enum[en]

class LinkType(DataType):
    """Abstract class for instance-referencing types."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.require_instance = True # type: bool

    def _handle_restrictions(self, stmt: Statement, sctx: SchemaContext) -> None:
        if stmt.find1("require-instance", "false"):
            self.require_instance = False

class LeafrefType(LinkType):
    """Class representing YANG "leafref" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.path = None
        self.ref_type = None

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        super()._handle_properties(stmt, sctx)
        self.path = XPathParser(
            stmt.find1("path", required=True).argument, sctx).parse()

    def canonical_string(self, val: ScalarValue) -> str:
        return self.ref_type.canonical_string(val)

    def _constraints(self, val: ScalarValue) -> bool:
        return self.ref_type._constraints(val)

    def _convert_raw(self, raw: RawScalar) -> ScalarValue:
        return self.ref_type._convert_raw(raw)

    def to_raw(self, val: ScalarValue) -> RawScalar:
        return self.ref_type.to_raw(val)

    def _deref(self, node: InstanceNode) -> List[InstanceNode]:
        ns = self.path.evaluate(node)
        return [n for n in ns if str(n) == str(node)]

class InstanceIdentifierType(LinkType):
    """Class representing YANG "instance-identifier" type."""

    def __str__(self):
        return "instance-identifier"

    def yang_type(self) -> YangIdentifier:
        """Override the superclass method."""
        return "instance-identifier"

    def _convert_raw(self, raw: str) -> InstanceRoute:
        try:
            return InstanceIdParser(raw).parse()
        except ParserException:
            raise YangTypeError(self, raw) from None

    def to_raw(self, val: InstanceRoute) -> str:
        """Override the superclass method."""
        return str(val)

    def _deref(self, node: InstanceNode) -> List[InstanceNode]:
        return [node.top().goto(node.value)]

class IdentityrefType(DataType):
    """Class representing YANG "identityref" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.bases = [] # type: List[QualName]

    def _convert_raw(self, raw: str) -> QualName:
        try:
            i1, s, i2 = raw.partition(":")
        except AttributeError:
            return None
        return (i2, i1) if s else (i1, self.namespace)

    def _constraints(self, val: QualName) -> bool:
        for b in self.bases:
            if not self.sctx.schema_data.is_derived_from(val, b):
                return False
        return True

    def to_raw(self, val: QualName) -> str:
        return self.canonical_string(val)

    def from_yang(self, text: str, sctx: SchemaContext) -> QualName:
        """Override the superclass method."""
        try:
            res = sctx.schema_data.translate_pname(text, self.sctx.text_mid)
        except:
            raise YangTypeError(self, text) from None
        if self._constraints(res): return res
        raise YangTypeError(self, text)

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        self.bases = []
        for b in stmt.find_all("base"):
            self.bases.append(
                sctx.schema_data.translate_pname(b.argument, sctx.text_mid))

    def canonical_string(self, val: ScalarValue) -> str:
        """Return canonical form of a value."""
        return "{}:{}".format(val[1], val[0])

class NumericType(DataType):
    """Abstract class for numeric data types."""

    def _constraints(self, val: Union[int, decimal.Decimal]) -> bool:
        return self._in_range(val, self._range)

    def _handle_restrictions(self, stmt: Statement, sctx: SchemaContext) -> None:
        rstmt = stmt.find1("range")
        if rstmt:
            self._range = self._combine_ranges(self._range, rstmt.argument,
                                               self.parse_value)

class Decimal64Type(NumericType):
    """Class representing YANG "decimal64" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self._epsilon = decimal.Decimal(0) # type: decimal.Decimal

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        fd = int(stmt.find1("fraction-digits", required=True).argument)
        self._epsilon = decimal.Decimal(10) ** -fd
        quot = decimal.Decimal(10**fd)
        lim = decimal.Decimal(9223372036854775808)
        self._range = [[-lim / quot, (lim - 1) / quot]]
        super()._handle_properties(stmt, sctx)

    def _convert_raw(self, raw: str) -> decimal.Decimal:
        if not isinstance(raw, (str, numbers.Real)):
            return None
        try:
            return decimal.Decimal(raw).quantize(self._epsilon)
        except decimal.InvalidOperation:
            return None

    def to_raw(self, val: decimal.Decimal) -> str:
        return self.canonical_string(val)

    def canonical_string(self, val: decimal.Decimal) -> str:
        return "0.0" if val == 0 else str(val).rstrip("0")

    def _constraints(self, val: decimal.Decimal) -> bool:
        return isinstance(val, decimal.Decimal) and super()._constraints(val)

class IntegralType(NumericType):
    """Abstract class for integral data types."""

    # Regular expressions
    hexa_re = re.compile(r"\s*(\+|-)?0x")

    def _parse(self, text: str) -> int:
        """Parse integral value.

        Args:
            text: String representation of the value.
        """
        try:
            return (int(text, 16) if self.hexa_re.match(text) else int(text))
        except ValueError:
            return None

    def _convert_raw(self, raw: str) -> int:
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None

    def _constraints(self, val: int) -> bool:
        return isinstance(val, int) and super()._constraints(val)

class Int8Type(IntegralType):
    """Class representing YANG "int8" type."""

    _range = [[-128,127]] # type: Range

class Int16Type(IntegralType):
    """Class representing YANG "int16" type."""

    _range = [[-32768, 32767]] # type: Range

class Int32Type(IntegralType):
    """Class representing YANG "int32" type."""

    _range = [[-2147483648, 2147483647]]  # type: Range

class Int64Type(IntegralType):
    """Class representing YANG "int64" type."""

    _range = [[-9223372036854775808, 9223372036854775807]] # type: Range

    def to_raw(self, val: int) -> str:
        return self.canonical_string(val)

class Uint8Type(IntegralType):
    """Class representing YANG "uint8" type."""

    _range = [[0, 255]] # type: Range

class Uint16Type(IntegralType):
    """Class representing YANG "uint16" type."""

    _range = [[0, 65535]] # type: Range

class Uint32Type(IntegralType):
    """Class representing YANG "uint32" type."""

    _range = [[0, 4294967295]] # type: Range

class Uint64Type(IntegralType):
    """Class representing YANG "uint64" type."""

    _range = [[0, 18446744073709551615]] # type: Range

    def _convert_raw(self, raw: str) -> int:
        try:
            return int(raw)
        except ValueError:
            return None

    def to_raw(self, val: int) -> str:
        return self.canonical_string(val)

class UnionType(DataType):
    """Class representing YANG "union" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.types = [] # type: List[DataType]

    def to_raw(self, val: ScalarValue) -> RawScalar:
        for t in self.types:
            if t.contains(val):
                return t.to_raw(val)

    def canonical_string(self, val: ScalarValue) -> str:
        for t in self.types:
            if t.contains(val):
                return t.canonical_string(val)

    def _parse(self, text: str) -> Optional[ScalarValue]:
        for t in self.types:
            val = t._parse(text)
            if val is not None and t._constraints(val): return val
        return None

    def _convert_raw(self, raw: RawScalar) -> Optional[ScalarValue]:
        for t in self.types:
            val = t._convert_raw(raw)
            if val is not None and t._constraints(val): return val
        return None

    def _constraints(self, val: Any) -> bool:
        for t in self.types:
            try:
                if t._constraints(val): return True
            except TypeError:
                continue
        return False

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        self.types = [ self._resolve_type(ts, sctx)
                       for ts in stmt.find_all("type") ]

class YangTypeError(YangsonException):
    """A value doesn't match its expected type."""

    def __init__(self, typ, value):
        self.typ = typ
        self.value = value

    def __str__(self) -> str:
        return "{}, expected {}".format(repr(self.value), str(self.typ))

DataType.dtypes = { "binary": BinaryType,
                    "bits": BitsType,
                    "boolean": BooleanType,
                    "decimal64": Decimal64Type,
                    "empty": EmptyType,
                    "enumeration": EnumerationType,
                    "identityref": IdentityrefType,
                    "instance-identifier": InstanceIdentifierType,
                    "int8": Int8Type,
                    "int16": Int16Type,
                    "int32": Int32Type,
                    "int64": Int64Type,
                    "leafref": LeafrefType,
                    "string": StringType,
                    "uint8": Uint8Type,
                    "uint16": Uint16Type,
                    "uint32": Uint32Type,
                    "uint64": Uint64Type,
                    "union": UnionType
                    }
"""Dictionary mapping type names to classes."""
