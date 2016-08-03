"""This module defines classes for schema patterns."""

from typing import List, Optional
from .constants import ContentType
from .typealiases import *
from .xpathast import Expr

class SchemaPattern:
    """Abstract class for schema patterns."""

    @staticmethod
    def optional(p: "SchemaPattern") -> "SchemaPattern":
        """Make `p` an optional pattern."""
        if isinstance(p, NotAllowed): return Empty()
        return Alternative(Empty(), p, False)

    def nullable(self, cnode: "DataNode", content: ContentType) -> bool:
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

    def nullable(self, cnode: "DataNode", content: ContentType) -> bool:
        """Override the superclass method.

        The empty pattern is nullable.
        """
        return True

    def deriv(self, x: str, cnode: "DataNode",
              content: ContentType) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return NotAllowed("member '{}'".format(x))

    def _tree(self, indent: int = 0):
        return " " * indent + "Empty"

    def __str__(self) -> str:
        return "Empty"

class Conditional(SchemaPattern):
    """Class representing conditional pattern."""

    def __init__(self, p: SchemaPattern, config: bool, when: Expr) -> None:
        """Initialize the class instance."""
        self.pattern = p
        self.config = config
        self.when = when

    def nullable(self, cnode: "DataNode", content: ContentType) -> bool:
        """Override the superclass method."""
        return (not self.config and content == ContentType.config or
                self.when is not None and not self.when.evaluate(cnode)
                or self.pattern.nullable(cnode, content))

    def deriv(self, x: str, cnode: "DataNode",
              content: ContentType) -> "SchemaPattern":
        """Return derivative of the receiver."""
        if not self.config and content == ContentType.config:
            return NotAllowed("non-config member '{}'".format(x))
        if self.when is None or self.when.evaluate(cnode):
            return self.pattern.deriv(x, cnode, content)
        return NotAllowed("conditional member '{}'".format(x))

    def _tree(self, indent: int = 0):
        return (" " * indent + "Conditional\n" +
                self.pattern._tree(indent + 2))

    def __str__(self) -> str:
        return str(self.pattern)

class NotAllowed(SchemaPattern):

    def __init__(self, reason: str = "invalid") -> None:
        """Initialize the class instance."""
        self.reason = reason

    def deriv(self, x: str, cnode: "DataNode",
              content: ContentType) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return self

    def _tree(self, indent: int = 0):
        return " " * indent + "NotAllowed: " + self.reason

    def __str__(self) -> str:
        return "not allowed: " + self.reason

class Member(SchemaPattern):

    def __init__(self, name: InstanceName, config: bool, when: Expr) -> None:
        self.name = name
        self.config = config
        self.when = when

    def nullable(self, cnode: "DataNode", content: ContentType) -> bool:
        """Override the superclass method."""
        if not self.config and content == ContentType.config:
            return True
        if self.when is None:
            return False
        dummy = cnode.put_member(self.name, (None,0))
        return not self.when.evaluate(dummy.member(self.name))

    def deriv(self, x: str, cnode: "DataNode",
              content: ContentType) -> "SchemaPattern":
        """Return derivative of the receiver."""
        if (self.name == x and
            (self.config or content != ContentType.config) and
            (self.when is None or self.when.evaluate(cnode.member(self.name)))):
            return Empty()
        return NotAllowed("member '{}'".format(x))

    def _tree(self, indent: int = 0):
        return " " * indent + "Member " + self.name

    def __str__(self) -> str:
        return "member '{}'".format(self.name)

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

    def nullable(self, cnode: "DataNode", content: ContentType) -> bool:
        """Override the superclass method."""
        return not self.mandatory and (
            self.left.nullable(cnode, content) or
            self.right.nullable(cnode, content))

    def deriv(self, x: str, cnode: "DataNode",
              content: ContentType) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return Alternative.combine(self.left.deriv(x, cnode, content),
                                   self.right.deriv(x, cnode, content))

    def _tree(self, indent: int = 0):
        return (" " * indent + "Alternative\n" +
                self.left._tree(indent + 2) + "\n" +
                self.right._tree(indent + 2))

    def __str__(self) -> str:
        return "alternative"

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

    def nullable(self, cnode: "DataNode", content: ContentType) -> bool:
        """Override the superclass method."""
        return (self.left.nullable(cnode, content) and
                self.right.nullable(cnode, content))

    def deriv(self, x: str, cnode: "DataNode",
              content: ContentType = ContentType.config) -> "SchemaPattern":
        """Return derivative of the receiver."""
        return Alternative.combine(
            Pair.combine(self.left.deriv(x, cnode, content), self.right),
            Pair.combine(self.right.deriv(x, cnode, content), self.left))

    def _tree(self, indent: int = 0):
        return (" " * indent + "Pair\n" +
                self.left._tree(indent + 2) + "\n" +
                self.right._tree(indent + 2))

    def __str__(self) -> str:
        return str(self.left)
