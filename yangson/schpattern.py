"""This module defines classes for schema patterns."""

from typing import List, Optional
from .enumerations import ContentType
from .typealiases import *
from .typealiases import _Singleton
from .xpathast import Expr

class SchemaPattern:
    """Abstract class for schema patterns."""

    @staticmethod
    def optional(p: "SchemaPattern") -> "SchemaPattern":
        """Make `p` an optional pattern."""
        if isinstance(p, NotAllowed): return Empty()
        return Alternative(Empty(), p, False, ContentType.all)

    def nullable(self, cnode: "InstanceNode", ctype: ContentType) -> bool:
        """Return ``True`` the receiver is nullable.

        By default, schema patterns are not nullable.
        """
        return False

class Empty(SchemaPattern, metaclass=_Singleton):
    """Singleton class representing the empty pattern."""

    def nullable(self, cnode: "InstanceNode", ctype: ContentType) -> bool:
        """Override the superclass method.

        The empty pattern is nullable.
        """
        return True

    def deriv(self, x: str, cnode: "InstanceNode",
              ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return NotAllowed("member '{}'".format(x))

    def _tree(self, indent: int = 0):
        return " " * indent + "Empty"

    def __str__(self) -> str:
        return "Empty"

class NotAllowed(SchemaPattern):

    def __init__(self, reason: str = "invalid") -> None:
        """Initialize the class instance."""
        self.reason = reason

    def deriv(self, x: str, cnode: "InstanceNode",
              ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return self

    def _tree(self, indent: int = 0):
        return " " * indent + "NotAllowed: " + self.reason

    def __str__(self) -> str:
        return "not allowed: " + self.reason

class Typeable(SchemaPattern):
    """Multiple content types and their combinations."""

    def __init__(self, ctype: ContentType) -> None:
        """Initialize the class instance."""
        self.ctype = ctype

    def nullable(self, cnode: "InstanceNode", ctype: ContentType) -> bool:
        return self.ctype.value & ctype.value == 0

class Conditional(SchemaPattern):
    """Class representing conditional pattern."""

    def __init__(self, p: SchemaPattern, when: Expr) -> None:
        """Initialize the class instance."""
        self.pattern = p
        self.when = when

    def nullable(self, cnode: "InstanceNode", ctype: ContentType) -> bool:
        """Override the superclass method."""
        return (self.when and not self.when.evaluate(cnode)
                or self.pattern.nullable(cnode, ctype))

    def deriv(self, x: str, cnode: "InstanceNode",
              ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        if self.when is None or self.when.evaluate(cnode):
            return self.pattern.deriv(x, cnode, ctype)
        return NotAllowed("conditional member '{}'".format(x))

    def _tree(self, indent: int = 0):
        return (" " * indent + "Conditional\n" +
                self.pattern._tree(indent + 2))

    def __str__(self) -> str:
        return str(self.pattern)

class Member(Typeable):

    def __init__(self, name: InstanceName, when: Expr,
                 ctype: ContentType) -> None:
        super().__init__(ctype)
        self.name = name
        self.when = when

    def nullable(self, cnode: "InstanceNode", ctype: ContentType) -> bool:
        """Override the superclass method."""
        if super().nullable(cnode,ctype): return True
        if self.when is None: return False
        dummy = cnode.put_member(self.name, (None,0))
        return not self.when.evaluate(dummy.member(self.name))

    def deriv(self, x: str, cnode: "InstanceNode",
              ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return (Empty() if self.name == x and not self.nullable(cnode, ctype)
                else NotAllowed("member '{}'".format(x)))

    def _tree(self, indent: int = 0):
        return " " * indent + "Member " + self.name

    def __str__(self) -> str:
        return "member '{}'".format(self.name)

class Alternative(Typeable):

    @classmethod
    def combine(cls, p: SchemaPattern, q: SchemaPattern,
                 mandatory: bool = False,
                 ctype: ContentType = ContentType.all):
        if isinstance(p, NotAllowed): return q
        if isinstance(q, NotAllowed): return p
        return cls(p, q, mandatory, ctype)

    def __init__(self, p: SchemaPattern, q: SchemaPattern,
                 mandatory: bool, ctype: ContentType) -> None:
        super().__init__(ctype)
        self.left = p
        self.right = q
        self.mandatory = mandatory

    def nullable(self, cnode: "InstanceNode", ctype: ContentType) -> bool:
        """Override the superclass method."""
        return (super().nullable(cnode, ctype) or not self.mandatory or
                self.left.nullable(cnode, ctype) or
                self.right.nullable(cnode, ctype))

    def deriv(self, x: str, cnode: "InstanceNode",
              ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return Alternative.combine(self.left.deriv(x, cnode, ctype),
                                   self.right.deriv(x, cnode, ctype))

    def _tree(self, indent: int = 0):
        return (" " * indent + "Alternative\n" +
                self.left._tree(indent + 2) + "\n" +
                self.right._tree(indent + 2))

    def __str__(self) -> str:
        return "alternative"

class Pair(SchemaPattern):

    @classmethod
    def combine(cls, p: SchemaPattern, q: SchemaPattern):
        if isinstance(p, Empty): return q
        if isinstance(q, Empty): return p
        if isinstance(p, NotAllowed):
                return NotAllowed(p.reason)
        if isinstance(q, NotAllowed):
                return NotAllowed(q.reason)
        return cls(p, q)

    def __init__(self, p: SchemaPattern, q: SchemaPattern) -> None:
        self.left = p
        self.right = q

    def nullable(self, cnode: "InstanceNode", ctype: ContentType) -> bool:
        """Override the superclass method."""
        return (self.left.nullable(cnode, ctype) and
                self.right.nullable(cnode, ctype))

    def deriv(self, x: str, cnode: "InstanceNode",
              ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return Alternative.combine(
            Pair.combine(self.left.deriv(x, cnode, ctype), self.right),
            Pair.combine(self.right.deriv(x, cnode, ctype), self.left))

    def _tree(self, indent: int = 0):
        return (" " * indent + "Pair\n" +
                self.left._tree(indent + 2) + "\n" +
                self.right._tree(indent + 2))

    def __str__(self) -> str:
        return str(self.left)
