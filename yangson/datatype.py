# Copyright © 2016–2026 CZ.NIC, z. s. p. o.
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
from abc import ABC, abstractmethod
import base64
import binascii
import decimal
import xml.etree.ElementTree as ET
import re
from typing import (Any, cast, ClassVar, Generic, Optional, Type,
                    TYPE_CHECKING, TypeVar, Union)

from .constraint import Intervals, Pattern
from .exceptions import (
    InvalidArgument, ParserException, ModuleNotRegistered, UnknownPrefix,
    InvalidLeafrefPath, MissingModuleNamespace, XPathTypeError)
from .schemadata import SchemaContext
from .instance import InstanceNode, InstanceIdParser
from .instroute import InstanceRoute
from .nodeset import NodeSet
from .statement import Statement
from .typealiases import (InstanceIdentifier, L, N, RN, QualName, RawScalar,
                          RS, S, ScalarValue, YangIdentifier)
from .xpathparser import Expr, XPathParser
if TYPE_CHECKING:
    from .schemanode import TerminalNode


class DataType(ABC, Generic[S, RS]):
    """Abstract class for YANG data types."""

    dtypes: ClassVar[dict[str, Type["DataType"]]]
    _option_template = '<option value="{}"{}>{}</option>'

    def __init__(self, sctx: SchemaContext, name: Optional[YangIdentifier]):
        """Initialize the class instance."""
        self.sctx = sctx
        self.default: Optional[S] = None
        self.name = name
        self.error_tag: Optional[str] = None
        self.error_message: Optional[str] = None
        self.units: Optional[str] = None

    @abstractmethod
    def __contains__(self, val: S) -> bool:
        """Return ``True`` if the receiver type contains `val`.

        If the result is ``False``, set also `error_tag` and `error_message`
        properties.
        """

    def __str__(self):
        """Return YANG name of the receiver type."""
        base = self.yang_type()
        return f"{self.name}({base})" if self.name else base

    @abstractmethod
    def from_raw(self, raw: RS) -> Optional[S]:
        """Return a cooked value of the receiver type.

        The input argument should follow the rules for JSON
        representation of scalar values as specified in
        [RFC7951]_. Conformance to the receiving type isn't
        guaranteed.

        Args:
            raw: Raw value obtained from JSON parser.

        """

    @abstractmethod
    def from_xml(self, xml: ET.Element) -> Optional[S]:
        """Return a cooked value of the received XML type.

        Args:
            xml: Text of the XML node
        """

    @abstractmethod
    def to_raw(self, val: S) -> Optional[RS]:
        """Return a raw value ready to be serialized in JSON."""

    def to_xml(self, val: S) -> Optional[str]:
        """Return XML text value ready to be serialized in XML."""
        return str(val) if val in self else None

    @abstractmethod
    def parse_value(self, text: str) -> Optional[S]:
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

    def canonical_string(self, val: S) -> Optional[str]:
        """Return canonical form of a value."""
        return str(val) if val in self else None

    def from_yang(self, text: str) -> S:
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

    def yang_type(self) -> YangIdentifier:
        """Return YANG name of the receiver."""
        return self.__class__.__name__[:-4].lower()

    def _set_error_info(self, error_tag: Optional[str] = None,
                        error_message: Optional[str] = None):
        self.error_tag = error_tag if error_tag else "invalid-type"
        self.error_message = (error_message if error_message else
                              "expected " + str(self))

    def _post_process(self, tnode: "TerminalNode") -> None:
        """Post-process the receiver type on behalf of a terminal node.

        By default do nothing.
        """
        pass

    @classmethod
    def _resolve_type(cls, stmt: Statement, sctx: SchemaContext) -> "DataType":
        typ = cast(str, stmt.argument)
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
            ts = cast(Statement, tdef.find1("type", required=True))
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
                dval = cast(str, dfst.argument)
                res.default = res.from_yang(dval)
                if res.default is None:
                    raise InvalidArgument(dval)
        res._handle_restrictions(stmt, sctx)
        return res

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        """Handle type substatements."""
        self._handle_restrictions(stmt, sctx)

    def _handle_restrictions(self, stmt: Statement,
                             sctx: SchemaContext) -> None:
        """Handle type restriction substatements."""
        pass

    def _type_digest(self, config: bool) -> dict[str, Any]:
        """Return receiver's type digest.

        Args:
            config: Specifies whether the type is on a configuration node.
        """
        res = {"base": self.yang_type()}
        if self.name is not None:
            res["derived"] = self.name
        return res


class EmptyType(DataType[tuple[None], list[None]]):
    """Class representing YANG "empty" type."""

    def __contains__(self, val: tuple[None]) -> bool:
        if val == (None,):
            return True
        self._set_error_info()
        return False

    def canonical_string(self, val: tuple[None]) -> Optional[str]:
        return ""

    def parse_value(self, text: str) -> Optional[tuple[None]]:
        return (None,) if text == "" else None

    def from_raw(self, raw: list[None]) -> Optional[tuple[None]]:
        return (None,) if raw == [None] else None

    def to_raw(self, val: tuple[None]) -> list[None]:
        return [None]

    def from_xml(self, xml: ET.Element) -> Optional[tuple[None]]:
        return (None,) if xml.text == None else None

    def to_xml(self, val: tuple[None]) -> None:
        return None


class BitsType(DataType[tuple[str, ...], str]):
    """Class representing YANG "bits" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.bit: dict[str, int] = {}

    def __contains__(self, val: tuple[str, ...]) -> bool:
        for b in val:
            if b not in self.bit:
                self._set_error_info(error_message="unknown bit " + b)
                return False
        return True

    def sorted_bits(self) -> list[tuple[str, int]]:
        """Return list of bit items sorted by position."""
        return sorted(self.bit.items(), key=lambda x: x[1])

    def from_raw(self, raw: str) -> Optional[tuple[str, ...]]:
        try:
            return tuple(raw.split())
        except AttributeError:
            return None

    def parse_value(self, text: str) -> Optional[tuple[str, ...]]:
        return self.from_raw(text)

    def from_xml(self, xml: ET.Element) -> Optional[tuple[str, ...]]:
        try:
            return tuple(cast(str, xml.text).split())
        except AttributeError:
            return None

    def to_raw(self, val: tuple[str, ...]) -> Optional[str]:
        return self.canonical_string(val)

    def to_xml(self, val: tuple[str, ...]) -> Optional[str]:
        return self.canonical_string(val)

    def as_int(self, val: tuple[str, ...]) -> Optional[int]:
        """Transform a "bits" value to an integer."""
        res = 0
        try:
            for b in val:
                res += 1 << self.bit[b]
        except KeyError:
            return None
        return res

    def canonical_string(self, val: tuple[str, ...]) -> Optional[str]:
        try:
            items = [(self.bit[b], b) for b in val]
        except KeyError:
            return None
        items.sort()
        return " ".join([x[1] for x in items])

    def _handle_properties(self, stmt: Statement,
                           sctx: SchemaContext) -> None:
        """Handle **bit** statements."""
        nextpos = 0
        for bst in stmt.find_all("bit"):
            if not sctx.schema_data.if_features(bst, sctx.text_mid):
                continue
            label = cast(str, bst.argument)
            pst = bst.find1("position")
            if pst:
                pos = int(cast(str, pst.argument))
                self.bit[label] = pos
                if pos > nextpos:
                    nextpos = pos
            else:
                self.bit[label] = nextpos
            nextpos += 1

    def _handle_restrictions(self, stmt: Statement,
                             sctx: SchemaContext) -> None:
        bst = stmt.find_all("bit")
        if not bst:
            return
        new = set([b.argument for b in bst if
                   sctx.schema_data.if_features(b, sctx.text_mid)])
        for bit in set(self.bit) - new:
            del self.bit[bit]

    def _type_digest(self, config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        bits: list[Optional[str]] = []
        i = 0
        for b in self.sorted_bits():
            while i < b[1]:
                bits.append(None)
                i += 1
            bits.append(b[0])
        res["bits"] = bits
        return res


class BooleanType(DataType[bool, bool]):
    """Class representing YANG "boolean" type."""

    def __contains__(self, val: bool) -> bool:
        if isinstance(val, bool):
            return True
        self._set_error_info()
        return False

    def from_raw(self, raw: bool) -> Optional[bool]:
        return raw if isinstance(raw, bool) else None

    def from_xml(self, xml: ET.Element) -> Optional[bool]:
        """Return a cooked value of the received XML type.

        Args:
            xml: Text of the XML node
        """
        return self.parse_value(cast(str, xml.text))

    def to_raw(self, val: bool) -> Optional[bool]:
        return val if val in self else None

    def parse_value(self, text: str) -> Optional[bool]:
        """Parse boolean value.

        Args:
            text: String representation of the value.
        """
        if text == "true":
            return True
        elif text == "false":
            return False
        else:
            return None

    def canonical_string(self, val: bool) -> Optional[str]:
        if val is True:
            return "true"
        elif val is False:
            return "false"
        else:
            return None

    def to_xml(self, val: bool) -> Optional[str]:
        return self.canonical_string(val)


class LinearType(DataType[L, str]):
    """Abstract class representing character or byte sequences."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.length: Optional[Intervals[int]] = None

    def __contains__(self, val: L) -> bool:
        if self.length and len(val) not in self.length:
            self._set_error_info(self.length.error_tag,
                                 self.length.error_message)
            return False
        return True

    def _handle_restrictions(self, stmt: Statement,
                             sctx: SchemaContext) -> None:
        lstmt = stmt.find1("length")
        if lstmt:
            if self.length is None:
                self.length = Intervals[int](
                    [[0, 4294967295]], error_message="invalid length")
            self.length.restrict_with(
                cast(str, lstmt.argument), *lstmt.get_error_info())

    def _type_digest(self, config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        if self.length:
            res["length"] = self.length.intervals
        return res


class StringType(LinearType[str]):
    """Class representing YANG "string" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.patterns: list[Pattern] = []

    def __contains__(self, val: str) -> bool:
        if not isinstance(val, str):
            self._set_error_info()
            return False
        if not super().__contains__(val):
            return False
        for p in self.patterns:
            if (p.regex.match(val) is not None) == p.invert_match:
                self._set_error_info(
                    p.error_tag, cast(str, p.error_message) + ': ' + val)
                return False
        return True

    def from_raw(self, raw: str) -> Optional[str]:
        return raw if isinstance(raw, str) else None

    def from_xml(self, xml: ET.Element) -> Optional[str]:
        return self.from_raw(cast(str, xml.text))

    def to_raw(self, val: str) -> Optional[str]:
        return val if val in self else None

    def parse_value(self, text: str) -> Optional[str]:
        return self.from_raw(text)

    def _handle_restrictions(self, stmt: Statement,
                             sctx: SchemaContext) -> None:
        super()._handle_restrictions(stmt, sctx)
        for pst in stmt.find_all("pattern"):
            invm = pst.find1("modifier", "invert-match") is not None
            self.patterns.append(Pattern(
                cast(str, pst.argument), invm, *pst.get_error_info()))

    def _type_digest(self, config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        pats = [p.pattern for p in self.patterns if not p.invert_match]
        ipats = [p.pattern for p in self.patterns if p.invert_match]
        if pats:
            res["patterns"] = pats
        if ipats:
            res["neg_patterns"] = ipats
        return res


class BinaryType(LinearType[bytes]):
    """Class representing YANG "binary" type."""

    def __contains__(self, val: bytes) -> bool:
        if not isinstance(val, bytes):
            self._set_error_info()
            return False
        return super().__contains__(val)

    def from_raw(self, raw: str) -> Optional[bytes]:
        """Override superclass method."""
        try:
            return base64.b64decode(raw, validate=True)
        except (TypeError, binascii.Error):
            return None

    def parse_value(self, text: str) -> Optional[bytes]:
        return self.from_raw(text)

    def from_xml(self, xml: ET.Element) -> Optional[bytes]:
        """Override superclass method."""
        try:
            return base64.b64decode(cast(str, xml.text), validate=True)
        except TypeError:
            return None

    def to_raw(self, val: bytes) -> Optional[str]:
        return self.canonical_string(val)

    def to_xml(self, val: bytes) -> Optional[str]:
        return self.canonical_string(val)

    def canonical_string(self, val: bytes) -> Optional[str]:
        try:
            return base64.b64encode(val).decode("ascii")
        except TypeError:
            return None


class EnumerationType(DataType[str, str]):
    """Class representing YANG "enumeration" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.enum: dict[str, int] = {}

    def __contains__(self, val: str) -> bool:
        if val in self.enum:
            return True
        self._set_error_info()
        return False

    def from_raw(self, raw: str) -> Optional[str]:
        return raw if isinstance(raw, str) else None

    def from_xml(self, xml: ET.Element) -> Optional[str]:
        return self.from_raw(cast(str, xml.text))

    def to_raw(self, val: str) -> Optional[str]:
        return val if val in self else None

    def parse_value(self, text: str) -> Optional[str]:
        return self.from_raw(text)

    def sorted_enums(self) -> list[tuple[str, int]]:
        """Return list of enum items sorted by value."""
        return sorted(self.enum.items(), key=lambda x: x[1])

    def _handle_properties(self, stmt: Statement,
                           sctx: SchemaContext) -> None:
        """Handle **enum** statements."""
        nextval = 0
        for est in stmt.find_all("enum"):
            if not sctx.schema_data.if_features(est, sctx.text_mid):
                continue
            label = cast(str, est.argument)
            vst = est.find1("value")
            if vst:
                val = int(cast(str, vst.argument))
                self.enum[label] = val
                if val > nextval:
                    nextval = val
            else:
                self.enum[label] = nextval
            nextval += 1

    def _handle_restrictions(self, stmt: Statement,
                             sctx: SchemaContext) -> None:
        est = stmt.find_all("enum")
        if not est:
            return
        new = set([e.argument for e in est if
                   sctx.schema_data.if_features(e, sctx.text_mid)])
        for en in set(self.enum) - new:
            del self.enum[en]

    def _type_digest(self, config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        if config:
            res["enums"] = list(self.enum.keys())
        return res


class LinkType(DataType[S, RS]):
    """Abstract class for instance-referencing types."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.require_instance: bool = True

    def _handle_restrictions(self, stmt: Statement,
                             sctx: SchemaContext) -> None:
        if stmt.find1("require-instance", "false"):
            self.require_instance = False


class LeafrefType(LinkType[ScalarValue, RawScalar]):
    """Class representing YANG "leafref" type."""

    path: Expr
    ref_type: DataType

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)

    def __contains__(self, val: ScalarValue) -> bool:
        return val in self.ref_type

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        super()._handle_properties(stmt, sctx)
        pathst = cast(Statement, stmt.find1("path", required=True))
        self.path = XPathParser(cast(str, pathst.argument), sctx).parse()

    def canonical_string(self, val: ScalarValue) -> Optional[str]:
        return self.ref_type.canonical_string(val)

    def from_raw(self, raw: RawScalar) -> Optional[ScalarValue]:
        return self.ref_type.from_raw(raw)

    def from_xml(self, xml: ET.Element) -> Optional[bytes]:
        return self.ref_type.from_xml(xml)

    def to_raw(self, val: ScalarValue) -> Optional[RawScalar]:
        return self.ref_type.to_raw(val)

    def to_xml(self, val: ScalarValue) -> Optional[str]:
        return self.ref_type.to_xml(val)

    def parse_value(self, text: str) -> Optional[ScalarValue]:
        return self.ref_type.parse_value(text)

    def from_yang(self, text: str) -> ScalarValue:
        return self.ref_type.from_yang(text)

    def _deref(self, node: InstanceNode) -> list[InstanceNode]:
        ns = self.path.evaluate(node)
        if isinstance(ns, NodeSet):
            return [n for n in ns if str(n) == str(node)]
        raise XPathTypeError(str(ns))

    def _post_process(self, tnode: "TerminalNode") -> None:
        ref = tnode._follow_leafref(self.path, tnode)
        if ref is None:
            raise InvalidLeafrefPath(tnode.qual_name)
        self.ref_type = ref.type

    def _type_digest(self, config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        res["ref_type"] = self.ref_type._type_digest(config)
        return res


class InstanceIdentifierType(LinkType[InstanceRoute, InstanceIdentifier]):
    """Class representing YANG "instance-identifier" type."""

    def __str__(self):
        return "instance-identifier"

    def __contains__(self, val: InstanceRoute) -> bool:
        return isinstance(val, InstanceRoute)

    def yang_type(self) -> YangIdentifier:
        """Override the superclass method."""
        return "instance-identifier"

    def from_raw(self, raw: InstanceIdentifier) -> Optional[InstanceRoute]:
        try:
            return InstanceIdParser(raw).parse()
        except ParserException:
            return None

    def parse_value(self, text: str) -> Optional[InstanceRoute]:
        return self.from_raw(text)

    def from_xml(self, xml: ET.Element) -> Optional[InstanceRoute]:
        return self.from_raw(cast(InstanceIdentifier, xml.text))

    def to_raw(self, val: InstanceRoute) -> InstanceIdentifier:
        """Override the superclass method."""
        return str(val)

    def to_xml(self, val: InstanceRoute) -> InstanceIdentifier:
        """Override the superclass method."""
        return str(val)

    def from_yang(self, text: str) -> InstanceRoute:
        """Override the superclass method."""
        return XPathParser(text, self.sctx).parse().as_instance_route()

    @staticmethod
    def _deref(node: InstanceNode) -> list[InstanceNode]:
        return [node.top().goto(cast(InstanceRoute, node.value))]


class IdentityrefType(DataType[QualName, YangIdentifier]):
    """Class representing YANG "identityref" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.bases: list[QualName] = []

    def __contains__(self, val: QualName) -> bool:
        for b in self.bases:
            if not self.sctx.schema_data.is_derived_from(val, b):
                self._set_error_info(
                    error_message=f"'{self.canonical_string(val)}'" +
                    f" not derived from '{self.canonical_string(b)}'")
                return False
        return True

    def from_raw(self, raw: YangIdentifier) -> Optional[QualName]:
        try:
            i1, s, i2 = raw.partition(":")
        except AttributeError:
            return None
        return (i2, i1) if s else (i1, self.sctx.default_ns)

    def parse_value(self, text: str) -> Optional[QualName]:
        return self.from_raw(text)

    def from_xml(self, xml: ET.Element) -> Optional[QualName]:
        try:
            i1, s, i2 = cast(str, xml.text).partition(":")
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
            raise MissingModuleNamespace(cast(str, ns_url))
        module = self.sctx.schema_data.modules_by_ns.get(ns_url)
        if not module:
            raise MissingModuleNamespace(ns_url)
        return (i2, module.main_module[0])

    def to_raw(self, val: QualName) -> YangIdentifier:
        return self.canonical_string(val)

    def to_xml(self, val: QualName) -> YangIdentifier:
        return self.canonical_string(val)

    def from_yang(self, text: YangIdentifier) -> QualName:
        """Override the superclass method."""
        try:
            return self.sctx.schema_data.translate_pname(
                text, self.sctx.text_mid)
        except (ModuleNotRegistered, UnknownPrefix):
            raise InvalidArgument(text)

    def canonical_string(self, val: QualName) -> str:
        """Return canonical form of a value."""
        return f"{val[1]}:{val[0]}"

    def _handle_properties(self, stmt: Statement,
                           sctx: SchemaContext) -> None:
        self.bases = []
        for b in stmt.find_all("base"):
            self.bases.append(
                sctx.schema_data.translate_pname(
                    cast(str, b.argument), sctx.text_mid))

    def _type_digest(self, config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        if config:
            res["identities"] = list(
                self.sctx.schema_data.derived_from_all(self.bases))
        return res


class NumericType(DataType[N, RN]):
    """Abstract class for numeric data types."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.range: Optional[Intervals[N]] = None

    def __contains__(self, val: N) -> bool:
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

    @property
    @abstractmethod
    def _range(self):
        """List with minimum and maximum value permitted by the type."""

    def _handle_restrictions(self, stmt: Statement,
                             sctx: SchemaContext) -> None:
        rstmt = stmt.find1("range")
        if rstmt:
            if self.range is None:
                self.range = Intervals[N](
                    [self._range], parser=self.parse_value,
                    error_message="not in range")
            self.range.restrict_with(
                cast(str, rstmt.argument), *rstmt.get_error_info())

    def _type_digest(self, config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        if self.range:
            res["range"] = [[self.to_raw(r[0]), self.to_raw(r[-1])]
                            for r in self.range.intervals]
        return res


class Decimal64Type(NumericType[decimal.Decimal, str]):
    """Class representing YANG "decimal64" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self._epsilon = decimal.Decimal(0)

    def __contains__(self, val: decimal.Decimal) -> bool:
        if not isinstance(val, decimal.Decimal):
            self._set_error_info()
            return False
        return super().__contains__(val)

    @property
    def _range(self) -> list[decimal.Decimal]:
        quot = decimal.Decimal(10**self.fraction_digits)
        lim = decimal.Decimal(9223372036854775808)
        return [-lim / quot, (lim - 1) / quot]

    def _handle_properties(self, stmt: Statement, sctx: SchemaContext) -> None:
        fd = cast(Statement, stmt.find1("fraction-digits", required=True))
        self.fraction_digits = int(cast(str, fd.argument))
        self._epsilon = decimal.Decimal(10) ** -self.fraction_digits
        super()._handle_properties(stmt, sctx)

    def from_raw(self, raw: str) -> Optional[decimal.Decimal]:
        """Override superclass method.

        According to [RFC7951]_, a raw instance must be string.
        """
        try:
            return (decimal.Decimal(raw).quantize(self._epsilon)
                    if isinstance(raw, str) else None)
        except decimal.InvalidOperation:
            return None

    def parse_value(self, text: str) -> Optional[decimal.Decimal]:
        return self.from_raw(text)

    def from_xml(self, xml: ET.Element) -> Optional[decimal.Decimal]:
        try:
            return (decimal.Decimal(xml.text).quantize(self._epsilon)
                    if isinstance(xml.text, str) else None)
        except decimal.InvalidOperation:
            return None

    def to_raw(self, val: decimal.Decimal) -> str:
        return self.canonical_string(val)

    def to_xml(self, val: decimal.Decimal) -> str:
        return self.canonical_string(val)

    def canonical_string(self, val: decimal.Decimal) -> str:
        if val == 0:
            return "0.0"
        sval = str(val.quantize(self._epsilon)).rstrip("0")
        return (sval + "0") if sval.endswith(".") else sval

    def _type_digest(self, config: bool) -> dict[str, Any]:
        res = super()._type_digest(config)
        res["fraction_digits"] = self.fraction_digits
        return res


class IntegralType(NumericType[int, RN]):
    """Abstract class for integral data types."""

    octhex = re.compile("[-+]?0([x0-9])")
    """Regular expression for octal or hexadecimal default."""

    def __contains__(self, val: int) -> bool:
        if not isinstance(val, int) or isinstance(val, bool):
            self._set_error_info()
            return False
        return super().__contains__(val)

    def parse_value(self, text: str) -> Optional[int]:
        """Override superclass method."""
        try:
            return int(text)
        except ValueError:
            return None

    def from_raw(self, raw: RN) -> Optional[int]:
        if not isinstance(raw, int) or isinstance(raw, bool):
            return None
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None

    def from_xml(self, xml: ET.Element) -> Optional[int]:
        try:
            return int(xml.text) if isinstance(xml.text, str) else None
        except (ValueError, TypeError):
            return None

    def from_yang(self, text: str) -> int:
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


class Int8Type(IntegralType[int]):
    """Class representing YANG "int8" type."""

    _range = [-128, 127]


    def to_raw(self, val: int) -> Optional[int]:
        return val if val in self else None


class Int16Type(IntegralType[int]):
    """Class representing YANG "int16" type."""

    _range = [-32768, 32767]


    def to_raw(self, val: int) -> Optional[int]:
        return val if val in self else None


class Int32Type(IntegralType[int]):
    """Class representing YANG "int32" type."""

    _range = [-2147483648, 2147483647]


    def to_raw(self, val: int) -> Optional[int]:
        return val if val in self else None

class Int64Type(IntegralType[str]):
    """Class representing YANG "int64" type."""

    _range = [-9223372036854775808, 9223372036854775807]

    def from_raw(self, raw: str) -> Optional[int]:
        """Override superclass method.

        According to [RFC7951]_, a raw instance must be string.
        """
        if not isinstance(raw, str) or isinstance(raw, bool):
            return None
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None

    def from_xml(self, xml: ET.Element) -> Optional[int]:
        """Override superclass method.

        XML is always delivered as a text element
        """
        try:
            return int(xml.text) if isinstance(xml.text, str) else None
        except (ValueError, TypeError):
            return None

    def to_raw(self, val: int) -> Optional[str]:
        return self.canonical_string(val)

    def to_xml(self, val: int) -> Optional[str]:
        return self.canonical_string(val)


class Uint8Type(IntegralType[int]):
    """Class representing YANG "uint8" type."""

    _range = [0, 255]

    def to_raw(self, val: int) -> Optional[int]:
        return val if val in self else None


class Uint16Type(IntegralType[int]):
    """Class representing YANG "uint16" type."""

    _range = [0, 65535]

    def to_raw(self, val: int) -> Optional[int]:
        return val if val in self else None


class Uint32Type(IntegralType[int]):
    """Class representing YANG "uint32" type."""

    _range = [0, 4294967295]

    def to_raw(self, val: int) -> Optional[int]:
        return val if val in self else None


class Uint64Type(IntegralType[str]):
    """Class representing YANG "uint64" type."""

    _range = [0, 18446744073709551615]

    def from_raw(self, raw: str) -> Optional[int]:
        """Override superclass method.

        According to [RFC7951]_, a raw instance must be string.
        """
        if not isinstance(raw, str):
            return None
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None

    def from_xml(self, xml: ET.Element) -> Optional[int]:
        """Override superclass method.

        XML is always delivered as a text element
        """
        try:
            return int(xml.text) if isinstance(xml.text, str) else None
        except (ValueError, TypeError):
            return None

    def to_raw(self, val: int) -> Optional[str]:
        return self.canonical_string(val)

    def to_xml(self, val: int) -> Optional[str]:
        return self.canonical_string(val)


class UnionType(DataType[ScalarValue, RawScalar]):
    """Class representing YANG "union" type."""

    def __init__(self, sctx: SchemaContext, name: YangIdentifier):
        """Initialize the class instance."""
        super().__init__(sctx, name)
        self.types: list[DataType] = []

    def __contains__(self, val: ScalarValue) -> bool:
        for t in self.types:
            try:
                if val in t:
                    return True
            except TypeError:
                continue
        return False

    def to_raw(self, val: ScalarValue) -> Optional[RawScalar]:
        for t in self.types:
            if val in t:
                return t.to_raw(val)
        return None

    def to_xml(self, val: ScalarValue) -> Optional[str]:
        for t in self.types:
            if val in t:
                return t.to_xml(val)
        return None

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

    def from_xml(self, xml: ET.Element) -> Optional[ScalarValue]:
        for t in self.types:
            val = t.from_xml(xml)
            if val is not None and val in t:
                return val
        return None

    def _handle_properties(self, stmt: Statement,
                           sctx: SchemaContext) -> None:
        self.types = [self._resolve_type(ts, sctx)
                      for ts in stmt.find_all("type")]

    def _post_process(self, tnode: "TerminalNode") -> None:
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
