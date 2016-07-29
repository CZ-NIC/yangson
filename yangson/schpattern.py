"""This module defines classes for schema patterns."""

from typing import List, Optional
from .typealiases import *
from .xpathast import Expr

class SchemaPattern:
    """Abstract class for schema patterns."""

    @staticmethod
    def optional(p: "SchemaPattern") -> "SchemaPattern":
        """Make `p` an optional pattern."""
        if isinstance(p, NotAllowed): return Empty()
        return Alternative(Empty(), p, False)

    @staticmethod
    def conditional(p: "SchemaPattern", when: Expr, dummy: InstanceName = None):
        """Make `p` conditionally depend on a "when" expression."""
        if isinstance(p, (Empty, NotAllowed)): return Empty()
        return Alternative(EmptyUnless(when, dummy), p, False)

    def nullable(self, cnode: "DataNode") -> bool:
        """Return ``True`` the receiver is nullable.

        By default, schema patterns are not nullable.
        """
        return False

class Empty(SchemaPattern):
    """Singleton class representing empty pattern."""

    _instance = None

    def __new__(cls):
        """Create the singleton instance if it doesn't exist yet."""
        if not cls._instance:
            cls._instance = super(Empty, cls).__new__(cls)
        return cls._instance

    def nullable(self, cnode: "DataNode") -> bool:
        """Override the superclass method.

        The empty pattern is nullable.
        """
        return True

    def deriv(self, x: str) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return NotAllowed("member '{}'".format(x))

    def __str__(self) -> str:
        return "Empty"

class EmptyUnless(SchemaPattern):
    """Class representing conditionally empty pattern."""

    def __init__(self, when: Expr, dummy: Optional[InstanceName]) -> None:
        """Initialize the class instance."""
        self.when = when
        self.dummy = dummy

    def nullable(self, cnode: "DataNode") -> bool:
        """Override the superclass method.

        The empty pattern is nullable.
        """
        if self.dummy is None:
            return not self.when.evaluate(cnode)
        ncn = cnode.put_member(self.dummy, (None,0))
        return not self.when.evaluate(ncn.member(self.dummy))

    def deriv(self, x: str) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return NotAllowed("member '{}'".format(x))

    def __str__(self) -> str:
        return "EmptyUnless"

class NotAllowed(SchemaPattern):

    def __init__(self, reason: str = "invalid") -> None:
        """Initialize the class instance."""
        self.reason = reason

    def deriv(self, x: str) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return self

    def __str__(self) -> str:
        return "not allowed: " + self.reason

class Member(SchemaPattern):

    def __init__(self, name: str) -> None:
        self.name = name

    def deriv(self, x: str) -> "SchemaPattern":
        """Return derivative of the receiver."""
        if self.name == x: return Empty()
        return NotAllowed("member '{}'".format(x))

    def __str__(self) -> str:
        return "missing mandatory member '{}'".format(self.name)

class Alternative(SchemaPattern):

    @classmethod
    def combine(cls, p: "SchemaPattern", q: "SchemaPattern",
                 mandatory: bool = False):
        if isinstance(p, NotAllowed): return q
        if isinstance(q, NotAllowed): return p
        return cls(p, q, mandatory)

    def __init__(self, p: "SchemaPattern", q: "SchemaPattern",
                 mandatory: bool) -> None:
        self.left = p
        self.right = q
        self.mandatory = mandatory

    def nullable(self, cnode: "DataNode") -> bool:
        """Override the superclass method."""
        return (False if self.mandatory else
                self.left.nullable(cnode) or self.right.nullable(cnode))

    def deriv(self, x: str) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return Alternative.combine(self.left.deriv(x), self.right.deriv(x))

    def __str__(self) -> str:
        return "no instances of mandatory choice"

class Pair(SchemaPattern):

    @classmethod
    def combine(cls, p: "SchemaPattern", q: "SchemaPattern"):
        if isinstance(p, Empty): return q
        if isinstance(q, Empty): return p
        if isinstance(p, NotAllowed):
                return NotAllowed(p.reason)
        if isinstance(q, NotAllowed):
                return NotAllowed(q.reason)
        return cls(p, q)

    def __init__(self, p: "SchemaPattern", q: "SchemaPattern") -> None:
        self.left = p
        self.right = q

    def nullable(self, cnode: "DataNode") -> bool:
        """Override the superclass method."""
        return self.left.nullable(cnode) and self.right.nullable(cnode)

    def deriv(self, x: str) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return Alternative.combine(
            Pair.combine(self.left.deriv(x), self.right),
            Pair.combine(self.right.deriv(x), self.left))

    def __str__(self) -> str:
        return str(self.left)
