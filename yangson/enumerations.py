"""Enumeration classes."""

from enum import Enum

class ContentType(Enum):
    """Enumeration of data content types."""
    config = 1
    nonconfig = 2
    all = 3

class DefaultDeny(Enum):
    """Enumeration of NACM default deny values."""
    none = 1
    write = 2
    all = 3

class Axis(Enum):
    """Enumeration of implemented XPath axes."""
    ancestor = 1
    ancestor_or_self = 2
    attribute = 3
    child = 4
    descendant = 5
    descendant_or_self = 6
    following_sibling = 7
    parent = 8
    preceding_sibling = 9
    self = 10

class MultiplicativeOp(Enum):
    """Enumeration of XPath multiplicative operators."""
    multiply = 1
    divide = 2
    modulo = 3

