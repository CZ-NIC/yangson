import decimal
import re
from typing import  Any, List, Optional, Tuple
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

    def handle_substatements(self, stmt: Statement) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type`` statement
        """
        dstmt = stmt.find1

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
        raise YangTypeError(self, input)

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

class Decimal64(NumericType):
    """Class representing YANG "decimal64" type."""

    def __init__(self) -> None:
        """Initialize the instance."""
        super().__init__()
        self.epsilon = decimal.Decimal(0) # type: decimal.Decimal
        self.context = None # type: Optional[decimal.Context]

    def handle_substatements(self, stmt: Statement) -> None:
        """Handle type substatements.

        :param stmt: YANG ``type decimal64`` statement
        """
        fd = stmt.find1("fraction-digits", required=True).argument
        self.epsilon = decimal.Decimal(10) ** -int(fd)
        super().handle_substatements(stmt)

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
        if -self.bound <= res < self.bound: return res
        raise YangTypeError(self, res)

class UnsignedInteger(IntegralType):
    """Abstract class for unsigned integer types."""

    def parse_value(self, input: str) -> int:
        """Parse integral value.

        :param input: string representation of the value
        """
        res = super().parse_value(input)
        if 0 <= res < self.bound: return res
        raise YangTypeError(self, res)

class Int8(SignedInteger):
    """Class representing YANG "int8" type."""

    bound = 128

class Int16(SignedInteger):
    """Class representing YANG "int16" type."""

    bound = 32768

class Int32(SignedInteger):
    """Class representing YANG "int32" type."""

    bound = 2147483648

class Int64(SignedInteger):
    """Class representing YANG "int64" type."""

    bound = 9223372036854775808

class Uint8(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    bound = 256

class Uint16(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    bound = 65536

class Uint32(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    bound = 4294967296

class Uint64(UnsignedInteger):
    """Class representing YANG "uint8" type."""

    bound = 18446744073709551616

class YangTypeError(YangsonException):
    """Exception to be raised if a value doesn't match its type."""

    def __init__(self, type: DataType, value) -> None:
        self.type = type
        self.value = value

    def __str__(self) -> str:
        return "value '{}' is not of type {}".format(str(self.value),
                                                     str(self.type))
