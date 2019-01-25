# Copyright © 2016-2019 CZ.NIC, z. s. p. o.
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
"""

import base64
import decimal
import numbers
from typing import Any, Dict, List, Optional, Tuple, Union

from .constraint import Intervals, Pattern
from .exceptions import (
    InvalidArgument, ParserException, ModuleNotRegistered, UnknownPrefix)
from .schemadata import SchemaContext
from .instance import InstanceNode, InstanceIdParser, InstanceRoute
from .statement import Statement
from .typealiases import QualName, RawScalar, ScalarValue, YangIdentifier
from .xpathparser import XPathParser


class DataType:
    """Abstract class for YANG data types."""

    _option_template = '<option value="{}"{}>{}</option>'

    def __init__(self, sctx: SchemaContext, name: Optional[YangIdentifier]):
        """Initialize the class instance."""
        self.sctx = sctx
        self.default = None
        self.name = name
        self.error_tag = None
        self.error_message = None

    def __contains__(self, val: ScalarValue) -> bool:
        """Return ``True`` if the receiver type contains `val`.

        If the result is ``False``, set also `error_tag` and `error_message`
        properties.
        """
        return True

    def __str__(self):
        """Return YANG name of the receiver type."""
        base = self.yang_type()
        return f"{self.name}({base})" if self.name else base

    def from_raw(self, raw: RawScalar) -> Optional[ScalarValue]:
        """Return a cooked value of the receiver type.

        Args:
            raw: Raw value obtained from JSON parser.
        """
        if isinstance(raw, str):
            return raw

    def to_raw(self, val: ScalarValue) -> Optional[RawScalar]:
        """Return a raw value ready to be serialized in JSON."""
        return val

    def parse_value(self, text: str) -> Optional[ScalarValue]:
        """Parse value of the receiver's type.

        Args:
            text: String representation of the value.

        Returns:
            A value of the receiver's type or ``None`` if parsing fails.
        """
        return self.from_raw(text)

    def canonical_string(self, val: ScalarValue) -> Optional[str]:
        """Return canonical form of a value."""
        return str(val)

    def from_yang(self, text: str) -> ScalarValue:
        """Parse value specified in a YANG module.

        Args:
            text: String representation of the value.

        Raises:
            InvalidArgument: If the receiver type cannot parse the text.
        """
        res = self.parse_value(text)
        if res is None:
            raise InvalidArgument(text)
        return res

    def yang_type(self) -> YangIdentifier:
        """Return YANG name of the receiver."""
        return self.__class__.__name__[:-4].lower()

    def _set_error_info(self, error_tag: str = None, error_message: str = None):
        self.error_tag = error_tag if error_tag else "invalid-type"
        self.error_message = (error_message if error_message else
                              "expected " + str(self))

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
            if ts.argument in cls.dtypes:
                break
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
                res.default = res.from_yang(dfst.argument)
                if res.default is None:
                    raise InvalidArgument(dfst.argument)
        res._handle_restrictions(stmt, sctx)
        return res

    def _deref(self, node: InstanceNode) -> List[InstanceNode]:
        return []

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        """Handle type substatements."""
        self._handle_restrictions(stmt, sctx)

    def _handle_restrictions(self, stmt: Statement, sctx: SchemaContext) -> None:
        """Handle type restriction substatements."""
        pass

    def _type_digest(self, config: bool) -> Dict[str, Any]:
        """Return receiver's type digest.

        Args:
            config: Specifies whether the type is on a configuration node.
        """
        res = {"base": self.yang_type()}
        if self.name is not None:
            res["derived"] = self.name
        return res


class EmptyType(DataType):
    """Class representing YANG "empty" type."""

    def canonical_string(self, val: Tuple[None]) -> Optional[str]:
        return ""

    def __contains__(self, val: Tuple[None]) -> bool:
        if val == (None,):
            return True
        self._set_error_info()
        return False

    def parse_value(self, text: str) -> Optional[Tuple[None]]:
        if text == "":
            return (None,)

    def from_raw(self, raw: RawScalar) -> Optional[Tuple[None]]:
        if raw == [None]:
            return (None,)


class BitsType(DataType):
    """Class representing YANG "bits" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.bit = {}

    def sorted_bits(self) -> List[Tuple[str, int]]:
        """Return list of bit items sorted by position."""
        return sorted(self.bit.items(), key=lambda x: x[1])

    def from_raw(self, raw: RawScalar) -> Optional[Tuple[str]]:
        try:
            return tuple(raw.split())
        except AttributeError:
            return None

    def __contains__(self, val: Tuple[str]) -> bool:
        for b in val:
            if b not in self.bit:
                self._set_error_info(error_message="unknown bit " + b)
                return False
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
            return None
        return res

    def canonical_string(self, val: Tuple[str]) -> Optional[str]:
        try:
            items = [(self.bit[b], b) for b in val]
        except KeyError:
            return None
        items.sort()
        return " ".join([x[1] for x in items])

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
        if not bst:
            return
        new = set([b.argument for b in bst if
                   sctx.schema_data.if_features(b, sctx.text_mid)])
        for bit in set(self.bit) - new:
            del self.bit[bit]

    def _type_digest(self, config: bool) -> Dict[str, Any]:
        res = super()._type_digest(config)
        bits = []
        i = 0
        for b in self.sorted_bits():
            while i < b[1]:
                bits.append(None)
                i += 1
            bits.append(b[0])
        res["bits"] = bits
        return res


class BooleanType(DataType):
    """Class representing YANG "boolean" type."""

    def __contains__(self, val: bool) -> bool:
        if isinstance(val, bool):
            return True
        self._set_error_info()
        return False

    def from_raw(self, raw: RawScalar) -> Optional[bool]:
        """Override superclass method."""
        if isinstance(raw, bool):
            return raw

    def parse_value(self, text: str) -> Optional[bool]:
        """Parse boolean value.

        Args:
            text: String representation of the value.
        """
        if text == "true":
            return True
        if text == "false":
            return False

    def canonical_string(self, val: bool) -> Optional[str]:
        if val is True:
            return "true"
        if val is False:
            return "false"


class LinearType(DataType):
    """Abstract class representing character or byte sequences."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.length = None  # type: Optional[Intervals]

    def _handle_restrictions(self, stmt: Statement, sctx: SchemaContext) -> None:
        lstmt = stmt.find1("length")
        if lstmt:
            if self.length is None:
                self.length = Intervals(
                    [[0, 4294967295]], error_message="invalid length")
            self.length.restrict_with(lstmt.argument, *lstmt.get_error_info())

    def __contains__(self, val: Union[str, bytes]) -> bool:
        if self.length and len(val) not in self.length:
            self._set_error_info(self.length.error_tag, self.length.error_message)
            return False
        return True

    def _type_digest(self, config: bool) -> Dict[str, Any]:
        res = super()._type_digest(config)
        if self.length:
            res["length"] = self.length.intervals
        return res


class StringType(LinearType):
    """Class representing YANG "string" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.patterns = []  # type: List[Pattern]

    def _handle_restrictions(self, stmt: Statement, sctx: SchemaContext) -> None:
        super()._handle_restrictions(stmt, sctx)
        for pst in stmt.find_all("pattern"):
            invm = pst.find1("modifier", "invert-match") is not None
            self.patterns.append(Pattern(
                pst.argument, invm, *pst.get_error_info()))

    def __contains__(self, val: str) -> bool:
        if not isinstance(val, str):
            self._set_error_info()
            return False
        if not super().__contains__(val):
            return False
        for p in self.patterns:
            if (p.regex.match(val) is not None) == p.invert_match:
                self._set_error_info(p.error_tag, p.error_message)
                return False
        return True

    def _type_digest(self, config: bool) -> Dict[str, Any]:
        res = super()._type_digest(config)
        pats = [p.pattern for p in self.patterns if not p.invert_match]
        ipats = [p.pattern for p in self.patterns if p.invert_match]
        if pats:
            res["patterns"] = pats
        if ipats:
            res["neg_patterns"] = ipats
        return res


class BinaryType(LinearType):
    """Class representing YANG "binary" type."""

    def from_raw(self, raw: RawScalar) -> Optional[bytes]:
        """Override superclass method."""
        try:
            return base64.b64decode(raw, validate=True)
        except TypeError:
            return None

    def __contains__(self, val: bytes) -> bool:
        if not isinstance(val, bytes):
            self._set_error_info()
            return False
        return super().__contains__(val)

    def to_raw(self, val: bytes) -> str:
        return self.canonical_string(val)

    def canonical_string(self, val: bytes) -> Optional[str]:
        return base64.b64encode(val).decode("ascii")


class EnumerationType(DataType):
    """Class representing YANG "enumeration" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.enum = {}  # type: Dict[str, int]

    def sorted_enums(self) -> List[Tuple[str, int]]:
        """Return list of enum items sorted by value."""
        return sorted(self.enum.items(), key=lambda x: x[1])

    def __contains__(self, val: str) -> bool:
        if val in self.enum:
            return True
        self._set_error_info()
        return False

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
        if not est:
            return
        new = set([e.argument for e in est if
                   sctx.schema_data.if_features(e, sctx.text_mid)])
        for en in set(self.enum) - new:
            del self.enum[en]

    def _type_digest(self, config: bool) -> Dict[str, Any]:
        res = super()._type_digest(config)
        if config:
            res["enums"] = list(self.enum.keys())
        return res


class LinkType(DataType):
    """Abstract class for instance-referencing types."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.require_instance = True  # type: bool

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

    def canonical_string(self, val: ScalarValue) -> Optional[str]:
        return self.ref_type.canonical_string(val)

    def __contains__(self, val: ScalarValue) -> bool:
        return val in self.ref_type

    def from_raw(self, raw: RawScalar) -> Optional[ScalarValue]:
        return self.ref_type.from_raw(raw)

    def to_raw(self, val: ScalarValue) -> RawScalar:
        return self.ref_type.to_raw(val)

    def _deref(self, node: InstanceNode) -> List[InstanceNode]:
        ns = self.path.evaluate(node)
        return [n for n in ns if str(n) == str(node)]

    def _type_digest(self, config: bool) -> Dict[str, Any]:
        res = super()._type_digest(config)
        res["ref_type"] = self.ref_type._type_digest(config)
        return res


class InstanceIdentifierType(LinkType):
    """Class representing YANG "instance-identifier" type."""

    def __str__(self):
        return "instance-identifier"

    def yang_type(self) -> YangIdentifier:
        """Override the superclass method."""
        return "instance-identifier"

    def from_raw(self, raw: RawScalar) -> Optional[InstanceRoute]:
        try:
            return InstanceIdParser(raw).parse()
        except ParserException:
            return None

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
        self.bases = []  # type: List[QualName]

    def from_raw(self, raw: RawScalar) -> Optional[QualName]:
        try:
            i1, s, i2 = raw.partition(":")
        except AttributeError:
            return None
        return (i2, i1) if s else (i1, self.sctx.default_ns)

    def __contains__(self, val: QualName) -> bool:
        for b in self.bases:
            if not self.sctx.schema_data.is_derived_from(val, b):
                self._set_error_info(error_message=f"not derived from {b[1]}:{b[0]}")
                return False
        return True

    def to_raw(self, val: QualName) -> str:
        return self.canonical_string(val)

    def from_yang(self, text: str) -> Optional[QualName]:
        """Override the superclass method."""
        try:
            return self.sctx.schema_data.translate_pname(text, self.sctx.text_mid)
        except (ModuleNotRegistered, UnknownPrefix):
            raise InvalidArgument(text)

    def canonical_string(self, val: ScalarValue) -> Optional[str]:
        """Return canonical form of a value."""
        return f"{val[1]}:{val[0]}"

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        self.bases = []
        for b in stmt.find_all("base"):
            self.bases.append(
                sctx.schema_data.translate_pname(b.argument, sctx.text_mid))

    def _type_digest(self, config: bool) -> Dict[str, Any]:
        res = super()._type_digest(config)
        if config:
            res["identities"] = list(
                self.sctx.schema_data.derived_from_all(self.bases))
        return res


class NumericType(DataType):
    """Abstract class for numeric data types."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.range = None  # type: Optional[Intervals]

    def __contains__(self, val: Union[int, decimal.Decimal]) -> bool:
        if self.range is None:
            if self._range[0] <= val <= self._range[1]:
                return True
            else:
                self._set_error_info()
                return False
        if val in self.range:
            return True
        self._set_error_info(self.range.error_tag, self.range.error_message)
        return False

    def _handle_restrictions(self, stmt: Statement, sctx: SchemaContext) -> None:
        rstmt = stmt.find1("range")
        if rstmt:
            if self.range is None:
                self.range = Intervals([self._range], parser=self.parse_value,
                                       error_message="not in range")
            self.range.restrict_with(rstmt.argument, *rstmt.get_error_info())

    def _type_digest(self, config: bool) -> Dict[str, Any]:
        res = super()._type_digest(config)
        if self.range:
            res["range"] = [[self.to_raw(r[0]), self.to_raw(r[-1])]
                            for r in self.range.intervals]
        return res


class Decimal64Type(NumericType):
    """Class representing YANG "decimal64" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self._epsilon = decimal.Decimal(0)  # type: decimal.Decimal

    @property
    def _range(self) -> List[decimal.Decimal]:
        quot = decimal.Decimal(10**self.fraction_digits)
        lim = decimal.Decimal(9223372036854775808)
        return [-lim / quot, (lim - 1) / quot]

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        self.fraction_digits = int(
            stmt.find1("fraction-digits", required=True).argument)
        self._epsilon = decimal.Decimal(10) ** -self.fraction_digits
        super()._handle_properties(stmt, sctx)

    def from_raw(self, raw: RawScalar) -> Optional[decimal.Decimal]:
        if not isinstance(raw, (str, numbers.Real)):
            return None
        try:
            return decimal.Decimal(raw).quantize(self._epsilon)
        except decimal.InvalidOperation:
            return None

    def to_raw(self, val: decimal.Decimal) -> str:
        return self.canonical_string(val)

    def canonical_string(self, val: decimal.Decimal) -> Optional[str]:
        if val == 0:
            return "0.0"
        sval = str(val.quantize(self._epsilon)).rstrip("0")
        return (sval + "0") if sval.endswith(".") else sval

    def __contains__(self, val: decimal.Decimal) -> bool:
        if not isinstance(val, decimal.Decimal):
            self._set_error_info()
            return False
        return super().__contains__(val)

    def _type_digest(self, config: bool) -> Dict[str, Any]:
        res = super()._type_digest(config)
        res["fraction_digits"] = self.fraction_digits
        return res


class IntegralType(NumericType):
    """Abstract class for integral data types."""

    def __contains__(self, val: int) -> bool:
        if not isinstance(val, int):
            self._set_error_info()
            return False
        return super().__contains__(val)

    def parse_value(self, text: str) -> Optional[int]:
        """Override superclass method."""
        try:
            return int(text)
        except ValueError:
            return None

    def from_raw(self, raw: RawScalar) -> Optional[int]:
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None

    def from_yang(self, text: str) -> Optional[int]:
        """Override the superclass method."""
        if text.startswith("0"):
            base = 16 if text.startswith("0x") else 8
        else:
            base = 10
        try:
            return int(text, base)
        except (ValueError, TypeError):
            raise InvalidArgument(text)


class Int8Type(IntegralType):
    """Class representing YANG "int8" type."""

    _range = [-128, 127]


class Int16Type(IntegralType):
    """Class representing YANG "int16" type."""

    _range = [-32768, 32767]


class Int32Type(IntegralType):
    """Class representing YANG "int32" type."""

    _range = [-2147483648, 2147483647]


class Int64Type(IntegralType):
    """Class representing YANG "int64" type."""

    _range = [-9223372036854775808, 9223372036854775807]

    def to_raw(self, val: int) -> str:
        return self.canonical_string(val)


class Uint8Type(IntegralType):
    """Class representing YANG "uint8" type."""

    _range = [0, 255]


class Uint16Type(IntegralType):
    """Class representing YANG "uint16" type."""

    _range = [0, 65535]


class Uint32Type(IntegralType):
    """Class representing YANG "uint32" type."""

    _range = [0, 4294967295]


class Uint64Type(IntegralType):
    """Class representing YANG "uint64" type."""

    _range = [0, 18446744073709551615]

    def to_raw(self, val: int) -> str:
        return self.canonical_string(val)


class UnionType(DataType):
    """Class representing YANG "union" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.types = []  # type: List[DataType]

    def to_raw(self, val: ScalarValue) -> RawScalar:
        for t in self.types:
            if val in t:
                return t.to_raw(val)

    def canonical_string(self, val: ScalarValue) -> Optional[str]:
        for t in self.types:
            if val in t:
                return t.canonical_string(val)
        return None

    def parse_value(self, text: str) -> Optional[ScalarValue]:
        for t in self.types:
            val = t.parse_value(text)
            if val is not None and val in t:
                return val
        return None

    def from_raw(self, raw: RawScalar) -> Optional[ScalarValue]:
        for t in self.types:
            val = t.from_raw(raw)
            if val is not None and val in t:
                return val
        return None

    def __contains__(self, val: Any) -> bool:
        for t in self.types:
            try:
                if val in t:
                    return True
            except TypeError:
                continue
        return False

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        self.types = [self._resolve_type(ts, sctx)
                      for ts in stmt.find_all("type")]


DataType.dtypes = {"binary": BinaryType,
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
