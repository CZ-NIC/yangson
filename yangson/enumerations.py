"""Enumeration classes."""

from enum import Enum

class ContentType(Enum):
    """Enumeration of instance data content types."""

    config = 1
    """Configuration data."""
    nonconfig = 2
    """Data that does not represent configuration."""
    all = 3
    """Nodes containing both configuration and state data."""

class DefaultDeny(Enum):
    """Enumeration of NACM default deny values."""

    none = 1
    """Data node with no default access restrictions."""
    write = 2
    """Sensitive security system parameter."""
    all = 3
    """Very sensitive security system parameter."""

class Axis(Enum):
    """Enumeration of implemented XPath axes."""

    ancestor = 1
    """Ancestors of the context node."""
    ancestor_or_self = 2
    """Context node and its ancestors."""
    attribute = 3
    """Attributes of the context node."""
    child = 4
    """Children of the context node."""
    descendant = 5
    """Descendants of the context node."""
    descendant_or_self = 6
    """Context node and its descendants."""
    following_sibling = 7
    """Following siblings of the context node."""
    parent = 8
    """Parent of the context node."""
    preceding_sibling = 9
    """Preceding siblings of the context node."""
    self = 10
    """Just the context node."""

class MultiplicativeOp(Enum):
    """Enumeration of XPath multiplicative operators."""

    multiply = 1
    """Multiplication operator (``*``)."""
    divide = 2
    """Division operator (``div``)."""
    modulo = 3
    """Modulo operator (``mod``)."""
