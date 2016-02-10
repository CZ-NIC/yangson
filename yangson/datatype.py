import re
from typing import  Any, List, Optional, Tuple
from yangson.types import Range, YangIdentifier

class DataType(object):
    """Abstract class for YANG data types."""

    def __init__(self, default: str) -> None:
        """Initialize the instance.

        :param default: type's default value
        """
        self.default = self.parse_value(default)

class NumericType(DataType):
    """Abstract class for numeric data types."""

    def __init__(self, default: str,
                 range: str) -> None:
        """Initialize the instance.

        :param default: type's default value
        :param range: range expression
        """
        super().__init__(default)
        # self.range = self.parse_range(range)

class IntegralType(NumericType):
    """Abstract class for numeric data types."""

    # Regular expressions
    hexa_re = re.compile(r"\s*(\+|-)?0x")

    def parse_value(self, input):
        """Parse integral value.

        :param input: input string
        """
        return (int(input, 16) if self.hexa_re.match(input) else int(input))
