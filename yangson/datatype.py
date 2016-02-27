import decimal
import re
from typing import Any, Callable, List, Optional, Tuple, Union
from .context import Context
from .exception import YangsonException
from .statement import Statement
from .typealiases import *

class DataType(object):
    """Abstract class for YANG data types."""

    @classmethod
    def resolve_type(cls, stmt: Statement, mid: ModuleId) -> "DataType":
        typ = stmt.argument
        if typ == "union":
            res = UnionType()
            res.types = [ cls.resolve_type(ts, mid)
                          for ts in stmt.find_all("type") ]
        elif typ in cls.dtypes:
            res = cls.dtypes[typ]()
            res.handle_substatements(stmt, mid)
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
        qst = (stmt, mid)
        while qst[0].argument != "union" and qst[0].argument not in cls.dtypes:
            tchain.append(qst)
            tdef, tid = Context.get_definition(*qst)
            qst = (tdef.find1("type", required=True), tid)
        tname = qst[0].argument
        if tname == "union":
            res = UnionType()
            res.types = [ cls.resolve_type(ts, qst[1])
                          for ts in qst[0].find_all("type") ]
        else:
            res = cls.dtypes[tname]()
        res.handle_substatements(*qst)
        while tchain:
            res.handle_substatements(*tchain.pop())
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

    def _parse(self, input: str) -> str:
        """The most generic parsing method is to return `input`.

        :param input: string representation of the value
        """
        return input

    def _constraints(self, val: Any) -> bool:
        return True

    def handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type decimal64`` statement
        :param mid: id of the context module
        """
        pass

class UnionType(DataType):
    """Class representing YANG "union" type."""

    def __init__(self):
        """Initialize the class instance."""
        self.types = [] # type: List[DataType]

    def _parse(self, input: str):
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

class EmptyType(DataType):
    """Class representing YANG "empty" type."""

    _instance = None

    def __new__(cls):
        """Create the singleton instance if it doesn't exist yet."""
        if not cls._instance:
            cls._instance = super(EmptyType, cls).__new__(cls)
        return cls._instance

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
        self.regexps = []

    def handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG string type statement
        :param mid: id of the context module
        """
        lstmt = stmt.find1("length")
        if lstmt:
            self._length = self._combine_ranges(self._length,
                                                lstmt.argument, int)

    def _constraints(self, val: str) -> bool:
        return self._in_range(len(val), self._length)

class EnumerationType(DataType):
    """Class representing YANG "enumeration" type."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        self._nextval = 0
        self.enum = {}

    def _constraints(self, val: str) -> bool:
        return val in self.enum

    def handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type enumeration`` statement
        :param mid: id of the context module
        """
        for est in stmt.find_all("enum"):
            label = est.argument
            vst = est.find1("value")
            if vst:
                val = int(vst.argument)
                if not self.enum or val > self._nextval:
                    self._nextval = val
                self.enum[label] = val
            else:
                self.enum[label] = self._nextval
                self._nextval += 1

class NumericType(DataType):
    """Abstract class for numeric data types."""

    def _constraints(self, val: Union[int, decimal.Decimal]) -> bool:
        return self._in_range(val, self._range)

    def handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
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
        self.context = None # type: Optional[decimal.Context]

    def handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type decimal64`` statement
        :param mid: id of the context module
        """
        fd = int(stmt.find1("fraction-digits", required=True).argument)
        self._epsilon = decimal.Decimal(10) ** -fd
        quot = decimal.Decimal(10**fd)
        lim = decimal.Decimal(9223372036854775808)
        self._range = [[-lim / quot, (lim - 1) / quot]]
        super().handle_substatements(stmt, mid)

    def _parse(self, input: str) -> decimal.Decimal:
        """Parse decimal value.

        :param input: string representation of the value
        """
        try:
            return decimal.Decimal(input).quantize(self._epsilon)
        except decimal.InvalidOperation:
            raise YangTypeError(input)

    def contains(self, val: decimal.Decimal) -> bool:
        """Return ``True`` if the receiver type contains `val`.

        :param val: value to test
        """
        return isinstance(val, decimal.Decimal)

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
            raise YangTypeError(input)

    def contains(self, val: int) -> bool:
        """Return ``True`` if the receiver type contains `val`.

        :param val: value to test
        """
        return isinstance(val, int) and self._constraints(val)

class SignedIntegerType(IntegralType):
    """Abstract class for signed integer types."""
    pass

class UnsignedIntegerType(IntegralType):
    """Abstract class for unsigned integer types."""
    pass

class Int8Type(SignedIntegerType):
    """Class representing YANG "int8" type."""

    _range = [[-128,127]] # type: Range

class Int16Type(SignedIntegerType):
    """Class representing YANG "int16" type."""

    _range = [[-32768, 32767]] # type: Range

class Int32Type(SignedIntegerType):
    """Class representing YANG "int32" type."""

    _range = [[-2147483648, 2147483647]]  # type: Range

class Int64Type(SignedIntegerType):
    """Class representing YANG "int64" type."""

    _range = [[-9223372036854775808, 9223372036854775807]] # type: Range

class Uint8Type(UnsignedIntegerType):
    """Class representing YANG "uint8" type."""

    _range = [[0, 255]] # type: Range

class Uint16Type(UnsignedIntegerType):
    """Class representing YANG "uint16" type."""

    _range = [[0, 65535]] # type: Range

class Uint32Type(UnsignedIntegerType):
    """Class representing YANG "uint32" type."""

    _range = [[0, 4294967295]] # type: Range

class Uint64Type(UnsignedIntegerType):
    """Class representing YANG "uint64" type."""

    _range = [[0, 18446744073709551615]] # type: Range

class YangTypeError(YangsonException):
    """Exception to be raised if a value doesn't match its type."""

    def __init__(self, value) -> None:
        self.value = value

    def __str__(self) -> str:
        return "incorrect type error for value " + str(self.value)

DataType.dtypes = { "boolean": BooleanType,
                    "decimal64": Decimal64Type,
                    "empty": EmptyType,
                    "enumeration": EnumerationType,
                    "int8": Int8Type,
                    "int16": Int16Type,
                    "int32": Int32Type,
                    "int64": Int64Type,
                    "string": StringType,
                    "uint8": Uint8Type,
                    "uint16": Uint16Type,
                    "uint32": Uint32Type,
                    "uint64": Uint64Type,
                    "union": UnionType
                    }
"""Dictionary mapping type names to classes."""
