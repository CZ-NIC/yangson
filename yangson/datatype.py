import decimal
import re
from typing import  Any, List, Optional, Tuple, Union
from .exception import YangsonException
from .statement import Statement
from .typealiases import *

class DataType(object):
    """Abstract class for YANG data types."""

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

    def __init__(self) -> None:
        """Initialize the instance."""
        super().__init__()
        self.length = None

class NumericType(DataType):
    """Abstract class for numeric data types."""

    def __init__(self) -> None:
        """Initialize the instance."""
        super().__init__()
        self.range = None

    def handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type`` statement
        :param mid: id of the context module
        """
        rstmt = stmt.find1("range")
        if rstmt: self.apply_range(rstmt.argument)

    def apply_range(self, rex: str) -> None:
        """Parse range specified in `rex` and apply it to the receiver.

        :param rex: range expression
        """
        to_num = lambda xs: [ self.parse_value(x) for x in xs ]
        lo = self.ranges[0][0]
        hi = self.ranges[-1][-1]
        parts = [ p.strip() for p in rex.split("|") ]
        ran = [ [ i.strip() for i in p.split("..") ] for p in parts ]
        if ran[0][0] != "min":
            lo = self.parse_value(ran[0][0])
        if ran[-1][-1] != "max":
            hi = self.parse_value(ran[-1][-1])
        self.ranges = (
            [[lo, hi]] if len(ran) == 1 else
            [[lo, self.parse_value(ran[0][-1])]] +
            [ to_num(r) for r in ran[1:-1] ] +
            [[self.parse_value(ran[-1][0]), hi]])

    def in_range(self, num: Union[int, decimal.Decimal]) -> bool:
        """Decide whether `num` fits the receiver's ranges.

        :param num: a number
        """
        for r in self.ranges:
            if len(r) == 1:
                if r[0] == num: return True
            elif r[0] <= num <= r[1]: return True
        return False

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

    def parse_value(self, input: str) -> int:
        """Parse integral value.

        :param input: string representation of the value
        """
        res = super().parse_value(input)
        if self.in_range(res): return res
        raise YangTypeError(res)

class UnsignedInteger(IntegralType):
    """Abstract class for unsigned integer types."""

    def parse_value(self, input: str) -> int:
        """Parse integral value.

        :param input: string representation of the value
        """
        res = super().parse_value(input)
        if self.in_range(res): return res
        raise YangTypeError(res)

class Int8(SignedInteger):
    """Class representing YANG "int8" type."""

    ranges = [[-128,127]]

class Int16(SignedInteger):
    """Class representing YANG "int16" type."""

    ranges = [[-32768, 32767]]

class Int32(SignedInteger):
    """Class representing YANG "int32" type."""

    ranges = [[-2147483648, 2147483647]]

class Int64(SignedInteger):
    """Class representing YANG "int64" type."""

    ranges = [[-9223372036854775808, 9223372036854775807]]

class Uint8(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    ranges = [[0, 255]]

class Uint16(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    ranges = [[0, 65535]]

class Uint32(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    ranges = [[0, 4294967295]]

class Uint64(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    ranges = [[0, 18446744073709551615]]

class YangTypeError(YangsonException):
    """Exception to be raised if a value doesn't match its type."""

    def __init__(self, value) -> None:
        self.value = value

    def __str__(self) -> str:
        return "incorrect type error for value " + str(self.value)
