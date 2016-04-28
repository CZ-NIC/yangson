import base64
import decimal
import re
from pyxb.utils.xmlre import XMLToPython
from typing import Any, Callable, List, Optional, Tuple, Union
from .constants import YangsonException
from .context import Context
from .statement import Statement
from .typealiases import *

# Local type aliases
Range = List[List[Union[int, decimal.Decimal]]]
RawScalar = Union[int, str]

class DataType:
    """Abstract class for YANG data types."""

    @classmethod
    def resolve_type(cls, stmt: Statement, mid: ModuleId) -> "DataType":
        typ = stmt.argument
        if typ in cls.dtypes:
            res = cls.dtypes[typ]()
            res.handle_properties(stmt, mid)
        else:
            res = cls.derived_type(stmt, mid)
        return res

    @classmethod
    def derived_type(cls, stmt: Statement, mid: ModuleId) -> "DataType":
        """Completely resolve a derived type.

        :param stmt: derived type statement
        :param mid: id of the context module
        """
        tchain = []
        tctx = (stmt, mid)
        while True:
            tdef = Context.get_definition(*tctx)
            tchain.append(tdef)
            tst = tdef[0].find1("type", required=True)
            if tst.argument in cls.dtypes: break
            tctx = (tst, tdef[1])
        res = cls.dtypes[tst.argument]()
        res.handle_properties(tst, tdef[1])
        while tchain:
            tdst, tid = tchain.pop()
            typst = tdst.find1("type", required=True)
            res.handle_restrictions(typst, tid)
            dfst = tdst.find1("default")
            if dfst:
                res.default = res.parse_value(dfst.argument)
        res.handle_restrictions(stmt, mid)
        return res


    @staticmethod
    def _in_range(num: Union[int, decimal.Decimal], rng: Range) -> bool:
        """Decide whether a number fits into a range.

        :param num: a number
        :param rng: range
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

        :param orig: original range
        :param rex: range expression
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

    def __init__(self) -> None:
        """Initialize the class instance."""
        self.default = None

    def __str__(self) -> str:
        """String representation of the receiver type."""
        return self.__class__.__name__.lower()

    def contains(self, val: Any) -> bool:
        """Return ``True`` if the receiver type contains `val`.

        :param val: value to test
        """
        return self._constraints(val)

    def parse_value(self, input: str) -> int:
        """Parse value of a data type.

        :param input: string representation of the value
        """
        res = self._parse(input)
        if self._constraints(res): return res
        raise YangTypeError(res)

    def _parse(self, input: str) -> ScalarValue:
        """The most generic parsing method is to return `input`.

        :param input: string representation of the value
        """
        return self._convert_raw(input)

    def from_raw(self, raw: RawScalar) -> ScalarValue:
        """Return a cooked value of the receiver type.

        :param raw: raw value obtained from JSON parser
        """
        try:
            res = self._convert_raw(raw)
            if self._constraints(res): return res
        except TypeError:
            raise YangTypeError(res) from None
        raise YangTypeError(res)

    def _convert_raw(self, raw: RawScalar) -> ScalarValue:
        """Return a cooked value."""
        return raw

    def _constraints(self, val: Any) -> bool:
        return True

    def handle_properties(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type`` statement
        :param mid: id of the context module
        """
        self.handle_restrictions(stmt, mid)

    def handle_restrictions(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type restriction substatements.

        :param stmt: YANG ``type`` statement
        :param mid: id of the context module
        """
        pass

class UnionType(DataType):
    """Class representing YANG "union" type."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self.types = [] # type: List[DataType]

    def _parse(self, input: str) -> Any:
        for t in self.types:
            try:
                val = t._parse(input)
            except YangTypeError:
                continue
            if self._constraints(val):
                return val
        raise YangTypeError(input)

    def contains(self, val: Any) -> bool:
        """Return ``True`` if the receiver type contains `val`.

        :param val: value to test
        """
        for t in self.types:
            if t.contains(val): return True
        return False

    def handle_properties(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type`` statement
        :param mid: id of the context module
        """
        self.types = [ self.resolve_type(ts, mid)
                       for ts in stmt.find_all("type") ]

class EmptyType(DataType):
    """Class representing YANG "empty" type."""

    _instance = None

    def __new__(cls):
        """Create the singleton instance if it doesn't exist yet."""
        if not cls._instance:
            cls._instance = super(EmptyType, cls).__new__(cls)
        return cls._instance

    def _constraints(self, val: Tuple[None]) -> bool:
        return val == (None,)

    def _parse(self, input: str) -> Tuple[None]:
        if input: raise YangTypeError(raw)
        return (None,)

    def _convert_raw(self, raw: List[None]) -> Tuple[None]:
        try:
            return tuple(raw)
        except TypeError:
            raise YangTypeError(raw) from None

class BitsType(DataType):
    """Class representing YANG "bits" type."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.bit = {}

    def _convert_raw(self, raw: str) -> List[str]:
        return tuple(raw.split())

    def _constraints(self, val: List[str]) -> bool:
        for b in val:
            if b not in self.bit: return False
        return True

    def as_int(self, val: List[str]) -> int:
        """Transform a "bits" value to an integer."""
        res = 0
        try:
            for b in val:
                res += 1 << self.bit[b]
        except KeyError:
            raise YangTypeError(val) from None
        return res

    def handle_restrictions(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type restrictions.

        :param stmt: YANG ``type bits`` statement
        :param mid: id of the context module
        """
        nextpos = 0
        for bst in stmt.find_all("bit"):
            if not Context.if_features(bst, mid):
                continue
            label = bst.argument
            pst = bst.find1("position")
            if pst:
                pos = int(pst.argument)
                if not self.bit or pos > nextpos:
                    nextpos = pos
                self.bit[label] = pos
            else:
                self.bit[label] = nextpos
                nextpos += 1

class BooleanType(DataType):
    """Class representing YANG "boolean" type."""

    def contains(self, val: bool) -> bool:
        """Return ``True`` if the receiver type contains `val`.

        :param val: value to test
        """
        return isinstance(val, bool)

    def _parse(self, input: str) -> bool:
        """Parse boolean value.

        :param input: string representation of the value
        """
        if input == "true": return True
        if input == "false": return False
        raise YangTypeError(input)

class StringType(DataType):
    """Class representing YANG "string" type."""

    _length = [[0, 4294967295]] # type: Range

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.patterns = []
        self.invert_patterns = []

    def handle_restrictions(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type restrictions.

        :param stmt: YANG string type statement
        :param mid: id of the context module
        """
        lstmt = stmt.find1("length")
        if lstmt:
            self._length = self._combine_ranges(self._length,
                                                lstmt.argument, int)
        for pst in stmt.find_all("pattern"):
            pat = re.compile(XMLToPython(pst.argument))
            if pst.find1("modifier", "invert-match"):
                self.invert_patterns.append(pat)
            else:
                self.patterns.append(pat)

    def contains(self, val: str) -> bool:
        """Return ``True`` if the receiver type contains `val`.

        :param val: value to test
        """
        return isinstance(val, str) and self._constraints(val)

    def _constraints(self, val: str) -> bool:
        if not self._in_range(len(val), self._length):
            return False
        for p in self.patterns:
            if not p.match(val): return False
        for p in self.invert_patterns:
            if p.match(val): return False
        return True

class BinaryType(StringType):
    """Class representing YANG "binary" type."""

    def _convert_raw(self, raw: str) -> bytes:
        return base64.b64decode(raw, validate=True)

class EnumerationType(DataType):
    """Class representing YANG "enumeration" type."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.enum = {}

    def _constraints(self, val: str) -> bool:
        return val in self.enum

    def handle_restrictions(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type restrictions.

        :param stmt: YANG ``type enumeration`` statement
        :param mid: id of the context module
        """
        nextval = 0
        for est in stmt.find_all("enum"):
            if not Context.if_features(est, mid):
                continue
            label = est.argument
            vst = est.find1("value")
            if vst:
                val = int(vst.argument)
                if not self.enum or val > nextval:
                    nextval = val
                self.enum[label] = val
            else:
                self.enum[label] = nextval
                nextval += 1

class LinkType(DataType):
    """Abstract class for instance-referencing types."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.require_instance = True # type: bool

    def handle_restrictions(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type leafref/instance-identifier`` statement
        :param mid: id of the context module
        """
        if stmt.find1("require-instance", "false"):
            self.require_instance = False

class LeafrefType(LinkType):
    """Class representing YANG "leafref" type."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.path = None

    def handle_properties(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type leafref`` statement
        :param mid: id of the context module
        """
        self.path = stmt.find1("path", required=True).argument

class InstanceIdentifierType(LinkType):
    """Class representing YANG "instance-identifier" type."""
    pass

class IdentityrefType(DataType):
    """Class representing YANG "identityref" type."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.bases = [] # type: List[QualName]

    def handle_properties(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type identityref`` statement
        :param mid: id of the context module
        """
        self.bases = [ Context.translate_pname(b.argument, mid)
                       for b in stmt.find_all("base") ]

class NumericType(DataType):
    """Abstract class for numeric data types."""

    def _constraints(self, val: Union[int, decimal.Decimal]) -> bool:
        return self._in_range(val, self._range)

    def handle_restrictions(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type`` statement
        :param mid: id of the context module
        """
        rstmt = stmt.find1("range")
        if rstmt:
            self._range = self._combine_ranges(self._range, rstmt.argument,
                                               self.parse_value)

class Decimal64Type(NumericType):
    """Class representing YANG "decimal64" type."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self._epsilon = decimal.Decimal(0) # type: decimal.Decimal
        self.context = None # type: decimal.Context

    def handle_properties(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type decimal64`` statement
        :param mid: id of the context module
        """
        fd = int(stmt.find1("fraction-digits", required=True).argument)
        self._epsilon = decimal.Decimal(10) ** -fd
        quot = decimal.Decimal(10**fd)
        lim = decimal.Decimal(9223372036854775808)
        self._range = [[-lim / quot, (lim - 1) / quot]]
        super().handle_properties(stmt, mid)

    def _convert_raw(self, raw: str) -> decimal.Decimal:
        try:
            return decimal.Decimal(raw).quantize(self._epsilon)
        except decimal.InvalidOperation:
            raise YangTypeError(raw) from None

    def contains(self, val: decimal.Decimal) -> bool:
        """Return ``True`` if the receiver type contains `val`.

        :param val: value to test
        """
        return isinstance(val, decimal.Decimal) and self._constraints(val)

class IntegralType(NumericType):
    """Abstract class for integral data types."""

    # Regular expressions
    hexa_re = re.compile(r"\s*(\+|-)?0x")

    def _parse(self, input: str) -> int:
        """Parse integral value.

        :param input: string representation of the value
        """
        try:
            return (int(input, 16) if self.hexa_re.match(input) else int(input))
        except ValueError:
            raise YangTypeError(input) from None

    def contains(self, val: int) -> bool:
        """Return ``True`` if the receiver type contains `val`.

        :param val: value to test
        """
        return isinstance(val, int) and self._constraints(val)

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

    def _convert_raw(self, raw: str) -> int:
        try:
            return int(raw)
        except ValueError:
            raise YangTypeError(raw) from None

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
            raise YangTypeError(raw) from None

class YangTypeError(YangsonException):
    """Exception to be raised if a value doesn't match its type."""

    def __init__(self, value) -> None:
        self.value = value

    def __str__(self) -> str:
        return "value " + repr(self.value)

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
