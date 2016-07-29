"""This module defines classes for schema patterns."""

from typing import List

class SchemaPattern:
    """Abstract class for schema patterns."""

    @staticmethod
    def optional(p: "SchemaPattern") -> "SchemaPattern":
        """Make `p` an optional pattern."""
        if isinstance(p, NotAllowed): return Empty()
        return Alternative(Empty(), p)

    def nullable(self) -> bool:
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

    def nullable(self) -> bool:
        """Override the superclass method.

        The empty pattern is nullable.
        """
        return True

    def deriv(self, x: str) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return NotAllowed("member '{}'".format(x))

    def __str__(self) -> str:
        return "Empty"

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
        return "member '{}'".format(self.name)

class Alternative(SchemaPattern):

    @classmethod
    def combine(cls, p: "SchemaPattern", q: "SchemaPattern"):
        if isinstance(p, NotAllowed): return q
        if isinstance(q, NotAllowed): return p
        return cls(p, q)

    def __init__(self, p: "SchemaPattern", q: "SchemaPattern") -> None:
        self.left = p
        self.right = q

    def nullable(self) -> bool:
        """Override the superclass method."""
        return self.left.nullable() or self.right.nullable()

    def deriv(self, x: str) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return Alternative.combine(self.left.deriv(x), self.right.deriv(x))

    def __str__(self) -> str:
        return "({} or {})".format(self.left, self.right)

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

    def nullable(self) -> bool:
        """Override the superclass method."""
        return self.left.nullable() and self.right.nullable()

    def deriv(self, x: str) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return Alternative.combine(
            Pair.combine(self.left.deriv(x), self.right),
            Pair.combine(self.right.deriv(x), self.left))

    def __str__(self) -> str:
        return "({} and {})".format(self.left, self.right)
