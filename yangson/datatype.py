import decimal
import re
from typing import Any, Callable, List, Optional, Tuple, Union
from .exception import YangsonException
from .statement import Statement
from .typealiases import *

class DataType(object):
    """Abstract class for YANG data types."""

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

    def parse_value(self, input: str) -> str:
        """Parse value of the receiver datatype.

        :param input: string representation of the value
        """
        return input

    def handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type decimal64`` statement
        :param mid: id of the context module
        """
        pass

class Empty(DataType):
    """Class representing YANG "empty" type."""

    _instance = None

    def __new__(cls):
        """Create the singleton instance if it doesn't exist yet."""
        if not cls._instance:
            cls._instance = super(Empty, cls).__new__(cls)
        return cls._instance

class Boolean(DataType):
    """Class representing YANG "boolean" type."""

    def parse_value(self, input: str) -> str:
        """Parse boolean value.

        :param input: string representation of the value
        """
        if input == "true": return True
        if input == "false": return False
        raise YangTypeError(input)

class String(DataType):
    """Class representing YANG "string" type."""

    _length = [[0, 4294967295]] # type: Range

    def __init__(self) -> None:
        """Initialize the instance."""
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

    def contains(self, val: str) -> bool:
        """Decide whether the receiver type contains a value.

        :param val: a value to test
        """
        return self._in_range(len(val), self._length)

    def parse_value(self, input: str) -> str:
        """Parse boolean value.

        :param input: a string
        """
        if self.contains(input): return input
        raise YangTypeError(input)

class NumericType(DataType):
    """Abstract class for numeric data types."""

    def __init__(self) -> None:
        """Initialize the instance."""
        super().__init__()

    def contains(self, val: Union[int, decimal.Decimal]) -> bool:
        """Decide whether the receiver type contains a value.

        :param val: a value to test
        """
        return self._in_range(val, self._range)

    def parse_value(self, input: str) -> int:
        """Parse integral value.

        :param input: string representation of the value
        """
        res = super().parse_value(input)
        if self.contains(res): return res
        raise YangTypeError(res)

    def handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type`` statement
        :param mid: id of the context module
        """
        rstmt = stmt.find1("range")
        if rstmt:
            self._range = self._combine_ranges(self._range, rstmt.argument,
                                               self.parse_value)

class Decimal64(NumericType):
    """Class representing YANG "decimal64" type."""

    def __init__(self) -> None:
        """Initialize the instance."""
        super().__init__()
        self.epsilon = decimal.Decimal(0) # type: decimal.Decimal
        self.context = None # type: Optional[decimal.Context]

    def handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type decimal64`` statement
        :param mid: id of the context module
        """
        fd = stmt.find1("fraction-digits", required=True).argument
        self.epsilon = decimal.Decimal(10) ** -int(fd)
        super().handle_substatements(stmt, mid)

    def parse_value(self, input: str) -> decimal.Decimal:
        """Parse decimal value.

        :param input: string representation of the value
        """
        return decimal.Decimal(input).quantize(self.epsilon)

class IntegralType(NumericType):
    """Abstract class for integral data types."""

    # Regular expressions
    hexa_re = re.compile(r"\s*(\+|-)?0x")

    def parse_value(self, input: str) -> int:
        """Parse integral value.

        :param input: string representation of the value
        """
        return (int(input, 16) if self.hexa_re.match(input) else int(input))

class SignedInteger(IntegralType):
    """Abstract class for signed integer types."""
    pass

class UnsignedInteger(IntegralType):
    """Abstract class for unsigned integer types."""
    pass

class Int8(SignedInteger):
    """Class representing YANG "int8" type."""

    _range = [[-128,127]] # type: Range

class Int16(SignedInteger):
    """Class representing YANG "int16" type."""

    _range = [[-32768, 32767]] # type: Range

class Int32(SignedInteger):
    """Class representing YANG "int32" type."""

    _range = [[-2147483648, 2147483647]]  # type: Range

class Int64(SignedInteger):
    """Class representing YANG "int64" type."""

    _range = [[-9223372036854775808, 9223372036854775807]] # type: Range

class Uint8(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    _range = [[0, 255]] # type: Range

class Uint16(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    _range = [[0, 65535]] # type: Range

class Uint32(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    _range = [[0, 4294967295]] # type: Range

class Uint64(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    _range = [[0, 18446744073709551615]] # type: Range

class YangTypeError(YangsonException):
    """Exception to be raised if a value doesn't match its type."""

    def __init__(self, value) -> None:
        self.value = value

    def __str__(self) -> str:
        return "incorrect type error for value " + str(self.value)
