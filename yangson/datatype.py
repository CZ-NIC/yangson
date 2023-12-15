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
import binascii
import decimal
import numbers
import xml.etree.ElementTree as ET
import re
from typing import Any, Optional, Union, TYPE_CHECKING

from .constraint import Intervals, Pattern
from .exceptions import (
    InvalidArgument, ParserException, ModuleNotRegistered, UnknownPrefix,
    InvalidLeafrefPath, MissingModuleNamespace)
from .schemadata import SchemaContext
from .instance import InstanceNode, InstanceIdParser, InstanceRoute
from .statement import Statement
from .typealiases import QualName, RawScalar, ScalarValue, YangIdentifier
from .xpathparser import XPathParser
if TYPE_CHECKING:
    from .schemanode import TerminalNode


class DataType:
    """Abstract class for YANG data types."""

    _option_template = '<option value="{}"{}>{}</option>'

    def __init__(self: "DataType", sctx: SchemaContext, name: Optional[YangIdentifier]):
        """Initialize the class instance."""
        self.sctx = sctx
        self.default = None
        self.name = name
        self.error_tag = None
        self.error_message = None
        self.units = None

    def __contains__(self: "DataType", val: ScalarValue) -> bool:
        """Return ``True`` if the receiver type contains `val`.

        If the result is ``False``, set also `error_tag` and `error_message`
        properties.
        """
        return True

    def __str__(self: "DataType"):
        """Return YANG name of the receiver type."""
        base = self.yang_type()
        return f"{self.name}({base})" if self.name else base

    def from_raw(self: "DataType", raw: RawScalar) -> Optional[ScalarValue]:
        """Return a cooked value of the receiver type.

        The input argument should follow the rules for JSON
        representation of scalar values as specified in
        [RFC7951]_. Conformance to the receiving type isn't
        guaranteed.

        Args:
            raw: Raw value obtained from JSON parser.

        """
        if isinstance(raw, str):
            return raw

    def from_xml(self: "DataType", xml: ET.Element) -> Optional[ScalarValue]:
        """Return a cooked value of the received XML type.

        Args:
            xml: Text of the XML node
        """
        if isinstance(xml.text, str):
            return xml.text

    def to_raw(self: "DataType", val: ScalarValue) -> Optional[RawScalar]:
        """Return a raw value ready to be serialized in JSON."""
        return val

    def to_xml(self: "DataType", val: ScalarValue) -> Optional[str]:
        """Return XML text value ready to be serialized in XML."""
        return str(val)

    def parse_value(self: "DataType", text: str) -> Optional[ScalarValue]:
        """Parse value of the receiver's type.

        The input text should follow the rules for lexical
        representation of scalar values as specified in
        [RFC7950]_. Conformance to the receiving type isn't
        guaranteed.

        Args:
            text: String representation of the value.

        Returns:
            A value of the receiver's type or ``None`` if parsing fails.

        """
        return self.from_raw(text)

    def canonical_string(self: "DataType", val: ScalarValue) -> Optional[str]:
        """Return canonical form of a value."""
        return str(val)

    def from_yang(self: "DataType", text: str) -> ScalarValue:
        """Parse value specified as default in a YANG module.

        Conformance to the receiving type isn't guaranteed.

        Args:
            text: String representation of the value.

        Raises:
            InvalidArgument: If the receiver type cannot parse the text.
        """
        res = self.parse_value(text)
        if res is None:
            raise InvalidArgument(text)
        return res

    def yang_type(self: "DataType") -> YangIdentifier:
        """Return YANG name of the receiver."""
        return self.__class__.__name__[:-4].lower()

    def _set_error_info(self: "DataType", error_tag: str = None, error_message: str = None):
        self.error_tag = error_tag if error_tag else "invalid-type"
        self.error_message = (error_message if error_message else
                              "expected " + str(self))

    def _post_process(self: "DataType", tnode: "TerminalNode") -> None:
        """Post-process the receiver type on behalf of a terminal node.

        By default do nothing.
        """
        pass

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
            ust = tdef.find1("units")
            if ust:
                res.units = ust.argument
            dfst = tdef.find1("default")
            if dfst:
                res.default = res.from_yang(dfst.argument)
                if res.default is None:
                    raise InvalidArgument(dfst.argument)
        res._handle_restrictions(stmt, sctx)
        return res

    def _handle_properties(self: "DataType", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle type substatements."""
        self._handle_restrictions(stmt, sctx)

    def _handle_restrictions(self: "DataType", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle type restriction substatements."""
        pass

    def _type_digest(self: "DataType", config: bool) -> dict[str, Any]:
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

    def canonical_string(self: "EmptyType", val: tuple[None]) -> Optional[str]:
        return ""

    def __contains__(self: "EmptyType", val: tuple[None]) -> bool:
        if val == (None,):
            return True
        self._set_error_info()
        return False

    def parse_value(self: "EmptyType", text: str) -> Optional[tuple[None]]:
        if text == "":
            return (None,)

    def from_raw(self: "EmptyType", raw: RawScalar) -> Optional[tuple[None]]:
        if raw == [None]:
            return (None,)

    def to_raw(self: "EmptyType", val: tuple[None]) -> list[None]:
        return [None]

    def from_xml(self: "EmptyType", xml: ET.Element) -> Optional[tuple[None]]:
        if xml.text == None:
            return (None,)

    def to_xml(self: "EmptyType", val: tuple[None]) -> None:
        return None


class BitsType(DataType):
    """Class representing YANG "bits" type."""

    def __init__(self: "BitsType", sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.bit = {}

    def sorted_bits(self: "BitsType") -> list[tuple[str, int]]:
        """Return list of bit items sorted by position."""
        return sorted(self.bit.items(), key=lambda x: x[1])

    def from_raw(self: "BitsType", raw: RawScalar) -> Optional[tuple[str]]:
        try:
            return tuple(raw.split())
        except AttributeError:
            return None

    def from_xml(self: "BitsType", xml: ET.Element) -> Optional[tuple[str]]:
        try:
            return tuple(xml.text.split())
        except AttributeError:
            return None

    def __contains__(self: "BitsType", val: tuple[str]) -> bool:
        for b in val:
            if b not in self.bit:
                self._set_error_info(error_message="unknown bit " + b)
                return False
        return True

    def to_raw(self: "BitsType", val: tuple[str]) -> str:
        return self.canonical_string(val)

    def to_xml(self: "BitsType", val: tuple[str]) -> str:
        return self.canonical_string(val)

    def as_int(self: "BitsType", val: tuple[str]) -> int:
        """Transform a "bits" value to an integer."""
        res = 0
        try:
            for b in val:
                res += 1 << self.bit[b]
        except KeyError:
            return None
        return res

    def canonical_string(self: "BitsType", val: tuple[str]) -> Optional[str]:
        try:
            items = [(self.bit[b], b) for b in val]
        except KeyError:
            return None
        items.sort()
        return " ".join([x[1] for x in items])

    def _handle_properties(self: "BitsType", stmt: Statement, sctx: SchemaContext) -> None:
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

    def _handle_restrictions(self: "BitsType", stmt: Statement, sctx: SchemaContext) -> None:
        bst = stmt.find_all("bit")
        if not bst:
            return
        new = set([b.argument for b in bst if
                   sctx.schema_data.if_features(b, sctx.text_mid)])
        for bit in set(self.bit) - new:
            del self.bit[bit]

    def _type_digest(self: "BitsType", config: bool) -> dict[str, Any]:
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

    def __contains__(self: "BooleanType", val: bool) -> bool:
        if isinstance(val, bool):
            return True
        self._set_error_info()
        return False

    def from_raw(self: "BooleanType", raw: RawScalar) -> Optional[bool]:
        """Override superclass method."""
        if isinstance(raw, bool):
            return raw

    def from_xml(self: "BooleanType", xml: ET.Element) -> Optional[ScalarValue]:
        """Return a cooked value of the received XML type.

        Args:
            xml: Text of the XML node
        """
        return self.parse_value(xml.text)

    def parse_value(self: "BooleanType", text: str) -> Optional[bool]:
        """Parse boolean value.

        Args:
            text: String representation of the value.
        """
        if text == "true":
            return True
        if text == "false":
            return False

    def canonical_string(self: "BooleanType", val: bool) -> Optional[str]:
        if val is True:
            return "true"
        if val is False:
            return "false"

    def to_xml(self: "BooleanType", val: bool) -> str:
        return self.canonical_string(val)


class LinearType(DataType):
    """Abstract class representing character or byte sequences."""

    def __init__(self: "LinearType", sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.length = None  # type: Optional[Intervals]

    def _handle_restrictions(self: "LinearType", stmt: Statement, sctx: SchemaContext) -> None:
        lstmt = stmt.find1("length")
        if lstmt:
            if self.length is None:
                self.length = Intervals(
                    [[0, 4294967295]], error_message="invalid length")
            self.length.restrict_with(lstmt.argument, *lstmt.get_error_info())

    def __contains__(self: "LinearType", val: Union[str, bytes]) -> bool:
        if self.length and len(val) not in self.length:
            self._set_error_info(self.length.error_tag, self.length.error_message)
            return False
        return True

    def _type_digest(self: "LinearType", config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        if self.length:
            res["length"] = self.length.intervals
        return res


class StringType(LinearType):
    """Class representing YANG "string" type."""

    def __init__(self: "StringType", sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.patterns = []  # type: list[Pattern]

    def _handle_restrictions(self: "StringType", stmt: Statement, sctx: SchemaContext) -> None:
        super()._handle_restrictions(stmt, sctx)
        for pst in stmt.find_all("pattern"):
            invm = pst.find1("modifier", "invert-match") is not None
            self.patterns.append(Pattern(
                pst.argument, invm, *pst.get_error_info()))

    def __contains__(self: "StringType", val: str) -> bool:
        if not isinstance(val, str):
            self._set_error_info()
            return False
        if not super().__contains__(val):
            return False
        for p in self.patterns:
            if (p.regex.match(val) is not None) == p.invert_match:
                self._set_error_info(p.error_tag, p.error_message + ': ' + val)
                return False
        return True

    def _type_digest(self: "StringType", config: bool) -> dict[str, Any]:
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

    def from_raw(self: "BinaryType", raw: RawScalar) -> Optional[bytes]:
        """Override superclass method."""
        try:
            return base64.b64decode(raw, validate=True)
        except (TypeError, binascii.Error):
            return None

    def from_xml(self: "BinaryType", xml: ET.Element) -> Optional[bytes]:
        """Override superclass method."""
        try:
            return base64.b64decode(xml.text, validate=True)
        except TypeError:
            return None

    def __contains__(self: "BinaryType", val: bytes) -> bool:
        if not isinstance(val, bytes):
            self._set_error_info()
            return False
        return super().__contains__(val)

    def to_raw(self: "BinaryType", val: bytes) -> str:
        return self.canonical_string(val)

    def to_xml(self: "BinaryType", val: bytes) -> str:
        return self.canonical_string(val)

    def canonical_string(self: "BinaryType", val: bytes) -> Optional[str]:
        return base64.b64encode(val).decode("ascii")


class EnumerationType(DataType):
    """Class representing YANG "enumeration" type."""

    def __init__(self: "EnumerationType", sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.enum = {}  # type: dict[str, int]

    def sorted_enums(self: "EnumerationType") -> list[tuple[str, int]]:
        """Return list of enum items sorted by value."""
        return sorted(self.enum.items(), key=lambda x: x[1])

    def __contains__(self: "EnumerationType", val: str) -> bool:
        if val in self.enum:
            return True
        self._set_error_info()
        return False

    def _handle_properties(self: "EnumerationType", stmt: Statement, sctx: SchemaContext) -> None:
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

    def _handle_restrictions(self: "EnumerationType", stmt: Statement, sctx: SchemaContext) -> None:
        est = stmt.find_all("enum")
        if not est:
            return
        new = set([e.argument for e in est if
                   sctx.schema_data.if_features(e, sctx.text_mid)])
        for en in set(self.enum) - new:
            del self.enum[en]

    def _type_digest(self: "EnumerationType", config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        if config:
            res["enums"] = list(self.enum.keys())
        return res


class LinkType(DataType):
    """Abstract class for instance-referencing types."""

    def __init__(self: "LinkType", sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.require_instance = True  # type: bool

    def _handle_restrictions(self: "LinkType", stmt: Statement, sctx: SchemaContext) -> None:
        if stmt.find1("require-instance", "false"):
            self.require_instance = False


class LeafrefType(LinkType):
    """Class representing YANG "leafref" type."""

    def __init__(self: "LeafrefType", sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.path = None
        self.ref_type = None

    def _handle_properties(self: "LeafrefType", stmt: Statement, sctx: SchemaContext) -> None:
        super()._handle_properties(stmt, sctx)
        self.path = XPathParser(
            stmt.find1("path", required=True).argument, sctx).parse()

    def canonical_string(self: "LeafrefType", val: ScalarValue) -> Optional[str]:
        return self.ref_type.canonical_string(val)

    def __contains__(self: "LeafrefType", val: ScalarValue) -> bool:
        return val in self.ref_type

    def from_raw(self: "LeafrefType", raw: RawScalar) -> Optional[ScalarValue]:
        return self.ref_type.from_raw(raw)

    def from_xml(self: "LeafrefType", xml: ET.Element) -> Optional[bytes]:
        return self.ref_type.from_xml(xml)

    def to_raw(self: "LeafrefType", val: ScalarValue) -> RawScalar:
        return self.ref_type.to_raw(val)

    def to_xml(self: "LeafrefType", val: ScalarValue) -> RawScalar:
        return self.ref_type.to_xml(val)

    def parse_value(self: "LeafrefType", text: str) -> Optional[ScalarValue]:
        return self.ref_type.parse_value(text)

    def from_yang(self: "LeafrefType", text: str) -> ScalarValue:
        return self.ref_type.from_yang(text)

    def _deref(self: "LeafrefType", node: InstanceNode) -> list[InstanceNode]:
        ns = self.path.evaluate(node)
        return [n for n in ns if str(n) == str(node)]

    def _post_process(self: "LeafrefType", tnode: "TerminalNode") -> None:
        ref = tnode._follow_leafref(self.path, tnode)
        if ref is None:
            raise InvalidLeafrefPath(tnode.qual_name)
        self.ref_type = ref.type

    def _type_digest(self: "LeafrefType", config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        res["ref_type"] = self.ref_type._type_digest(config)
        return res


class InstanceIdentifierType(LinkType):
    """Class representing YANG "instance-identifier" type."""

    def __str__(self: "InstanceIdentifierType"):
        return "instance-identifier"

    def yang_type(self: "InstanceIdentifierType") -> YangIdentifier:
        """Override the superclass method."""
        return "instance-identifier"

    def from_raw(self: "InstanceIdentifierType", raw: RawScalar) -> Optional[InstanceRoute]:
        try:
            return InstanceIdParser(raw).parse()
        except ParserException:
            return None

    def from_xml(self: "InstanceIdentifierType", xml: ET.Element) -> Optional[InstanceRoute]:
        return self.from_raw(xml.text)

    def to_raw(self: "InstanceIdentifierType", val: InstanceRoute) -> str:
        """Override the superclass method."""
        return str(val)

    def to_xml(self: "InstanceIdentifierType", val: InstanceRoute) -> str:
        """Override the superclass method."""
        return str(val)

    def from_yang(self: "InstanceIdentifierType", text: str) -> InstanceRoute:
        """Override the superclass method."""
        return XPathParser(text, self.sctx).parse().as_instance_route()

    @staticmethod
    def _deref(node: InstanceNode) -> list[InstanceNode]:
        return [node.top().goto(node.value)]


class IdentityrefType(DataType):
    """Class representing YANG "identityref" type."""

    def __init__(self: "IdentityrefType", sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.bases = []  # type: list[QualName]

    def from_raw(self: "IdentityrefType", raw: RawScalar) -> Optional[QualName]:
        try:
            i1, s, i2 = raw.partition(":")
        except AttributeError:
            return None
        return (i2, i1) if s else (i1, self.sctx.default_ns)

    def from_xml(self: "IdentityrefType", xml: ET.Element) -> Optional[QualName]:
        try:
            i1, s, i2 = xml.text.partition(":")
        except AttributeError:
            return None

        if not s:
            # not prefixed, so assume default ns
            return (i1, self.sctx.default_ns)
        elif i1 == self.sctx.default_ns:
            # prefixed with default ns
            return (i2, self.sctx.default_ns)

        # the following code has issues (Issue #79)
        ns_url = xml.attrib.get('xmlns:'+i1)
        if not ns_url:
            raise MissingModuleNamespace(ns_url)
        module = self.sctx.schema_data.modules_by_ns.get(ns_url)
        if not module:
            raise MissingModuleNamespace(ns_url)
        return (i2, module.main_module[0])

    def __contains__(self: "IdentityrefType", val: QualName) -> bool:
        for b in self.bases:
            if not self.sctx.schema_data.is_derived_from(val, b):
                self._set_error_info(
                    error_message=f"'{self.canonical_string(val)}'" +
                    f" not derived from '{self.canonical_string(b)}'")
                return False
        return True

    def to_raw(self: "IdentityrefType", val: QualName) -> str:
        return self.canonical_string(val)

    def to_xml(self: "IdentityrefType", val: QualName) -> str:
        return self.canonical_string(val)

    def from_yang(self: "IdentityrefType", text: str) -> QualName:
        """Override the superclass method."""
        try:
            return self.sctx.schema_data.translate_pname(
                text, self.sctx.text_mid)
        except (ModuleNotRegistered, UnknownPrefix):
            raise InvalidArgument(text)

    def canonical_string(self: "IdentityrefType",
                         val: ScalarValue) -> Optional[str]:
        """Return canonical form of a value."""
        return f"{val[1]}:{val[0]}"

    def _handle_properties(self: "IdentityrefType", stmt: Statement, sctx: SchemaContext) -> None:
        self.bases = []
        for b in stmt.find_all("base"):
            self.bases.append(
                sctx.schema_data.translate_pname(b.argument, sctx.text_mid))

    def _type_digest(self: "IdentityrefType", config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        if config:
            res["identities"] = list(
                self.sctx.schema_data.derived_from_all(self.bases))
        return res


class NumericType(DataType):
    """Abstract class for numeric data types."""

    def __init__(self: "NumericType", sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.range = None  # type: Optional[Intervals]

    def __contains__(self: "NumericType", val: Union[int, decimal.Decimal]) -> bool:
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

    def _handle_restrictions(self: "NumericType", stmt: Statement, sctx: SchemaContext) -> None:
        rstmt = stmt.find1("range")
        if rstmt:
            if self.range is None:
                self.range = Intervals([self._range], parser=self.parse_value,
                                       error_message="not in range")
            self.range.restrict_with(rstmt.argument, *rstmt.get_error_info())

    def _type_digest(self: "NumericType", config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        if self.range:
            res["range"] = [[self.to_raw(r[0]), self.to_raw(r[-1])]
                            for r in self.range.intervals]
        return res


class Decimal64Type(NumericType):
    """Class representing YANG "decimal64" type."""

    def __init__(self: "Decimal64Type", sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self._epsilon = decimal.Decimal(0)  # type: decimal.Decimal

    @property
    def _range(self: "Decimal64Type") -> list[decimal.Decimal]:
        quot = decimal.Decimal(10**self.fraction_digits)
        lim = decimal.Decimal(9223372036854775808)
        return [-lim / quot, (lim - 1) / quot]

    def _handle_properties(self: "Decimal64Type", stmt: Statement, sctx: SchemaContext) -> None:
        self.fraction_digits = int(
            stmt.find1("fraction-digits", required=True).argument)
        self._epsilon = decimal.Decimal(10) ** -self.fraction_digits
        super()._handle_properties(stmt, sctx)

    def from_raw(self: "Decimal64Type", raw: RawScalar) -> Optional[decimal.Decimal]:
        """Override superclass method.

        According to [RFC7951]_, a raw instance must be string.
        """
        if not isinstance(raw, str):
            return None
        try:
            return decimal.Decimal(raw).quantize(self._epsilon)
        except decimal.InvalidOperation:
            return None

    def from_xml(self: "Decimal64Type", xml: ET.Element) -> Optional[decimal.Decimal]:
        try:
            return decimal.Decimal(xml.text).quantize(self._epsilon)
        except decimal.InvalidOperation:
            return None

    def to_raw(self: "Decimal64Type", val: decimal.Decimal) -> str:
        return self.canonical_string(val)

    def to_xml(self: "Decimal64Type", val: decimal.Decimal) -> str:
        return self.canonical_string(val)

    def canonical_string(self: "Decimal64Type", val: decimal.Decimal) -> Optional[str]:
        if val == 0:
            return "0.0"
        sval = str(val.quantize(self._epsilon)).rstrip("0")
        return (sval + "0") if sval.endswith(".") else sval

    def __contains__(self: "Decimal64Type", val: decimal.Decimal) -> bool:
        if not isinstance(val, decimal.Decimal):
            self._set_error_info()
            return False
        return super().__contains__(val)

    def _type_digest(self: "Decimal64Type", config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        res["fraction_digits"] = self.fraction_digits
        return res


class IntegralType(NumericType):
    """Abstract class for integral data types."""

    octhex = re.compile("[-+]?0([x0-9])")
    """Regular expression for octal or hexadecimal default."""

    def __contains__(self: "IntegralType", val: int) -> bool:
        if not isinstance(val, int) or isinstance(val, bool):
            self._set_error_info()
            return False
        return super().__contains__(val)

    def parse_value(self: "IntegralType", text: str) -> Optional[int]:
        """Override superclass method."""
        try:
            return int(text)
        except ValueError:
            return None

    def from_raw(self: "IntegralType", raw: RawScalar) -> Optional[int]:
        if not isinstance(raw, int) or isinstance(raw, bool):
            return None
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None

    def from_xml(self: "IntegralType", xml: ET.Element) -> Optional[int]:
        try:
            return int(xml.text)
        except (ValueError, TypeError):
            return None

    def from_yang(self: "IntegralType", text: str) -> int:
        """Override the superclass method."""
        mo = self.octhex.match(text)
        if mo:
            base = 16 if mo.group(1) == "x" else 8
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

    def from_raw(self: "Int64Type", raw: RawScalar) -> Optional[int]:
        """Override superclass method.

        According to [RFC7951]_, a raw instance must be string.
        """
        if not isinstance(raw, str) or isinstance(raw, bool):
            return None
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None

    def from_xml(self: "Int64Type", xml: ET.Element) -> Optional[int]:
        """Override superclass method.

        XML is always delivered as a text element
        """
        try:
            return int(xml.text)
        except (ValueError, TypeError):
            return None

    def to_raw(self: "Int64Type", val: int) -> str:
        return self.canonical_string(val)

    def to_xml(self: "Int64Type", val: int) -> str:
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

    def from_raw(self: "Uint64Type", raw: str) -> Optional[int]:
        """Override superclass method.

        According to [RFC7951]_, a raw instance must be string.
        """
        if not isinstance(raw, str) or isinstance(raw, bool):
            return None
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None

    def from_xml(self: "Uint64Type", xml: ET.Element) -> Optional[int]:
        """Override superclass method.

        XML is always delivered as a text element
        """
        try:
            return int(xml.text)
        except (ValueError, TypeError):
            return None

    def to_raw(self: "Uint64Type", val: int) -> str:
        return self.canonical_string(val)

    def to_xml(self: "Uint64Type", val: int) -> str:
        return self.canonical_string(val)


class UnionType(DataType):
    """Class representing YANG "union" type."""

    def __init__(self: "UnionType", sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.types = []  # type: list[DataType]

    def to_raw(self: "UnionType", val: ScalarValue) -> RawScalar:
        for t in self.types:
            if val in t:
                return t.to_raw(val)

    def to_xml(self: "UnionType", val: ScalarValue) -> RawScalar:
        for t in self.types:
            if val in t:
                return t.to_xml(val)

    def canonical_string(self: "UnionType", val: ScalarValue) -> Optional[str]:
        for t in self.types:
            if val in t:
                return t.canonical_string(val)
        return None

    def parse_value(self: "UnionType", text: str) -> Optional[ScalarValue]:
        for t in self.types:
            val = t.parse_value(text)
            if val is not None and val in t:
                return val
        return None

    def from_raw(self: "UnionType", raw: RawScalar) -> Optional[ScalarValue]:
        for t in self.types:
            val = t.from_raw(raw)
            if val is not None and val in t:
                return val
        return None

    def from_xml(self: "UnionType", xml: ET.Element) -> Optional[ScalarValue]:
        for t in self.types:
            val = t.from_xml(xml)
            if val is not None and val in t:
                return val
        return None

    def __contains__(self: "UnionType", val: Any) -> bool:
        for t in self.types:
            try:
                if val in t:
                    return True
            except TypeError:
                continue
        return False

    def _handle_properties(self: "UnionType", stmt: Statement, sctx: SchemaContext) -> None:
        self.types = [self._resolve_type(ts, sctx)
                      for ts in stmt.find_all("type")]

    def _post_process(self: "UnionType", tnode: "TerminalNode") -> None:
        for t in self.types:
            t._post_process(tnode)


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
