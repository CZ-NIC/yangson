# Copyright © 2016, 2017 CZ.NIC, z. s. p. o.
#
# This file is part of Yangson.
#
# Yangson is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Yangson is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with Yangson.  If not, see <http://www.gnu.org/licenses/>.

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
        return Alternative.combine(Empty(), p)

    def nullable(self, ctype: ContentType) -> bool:
        """Return ``True`` the receiver is nullable."""
        return False

    def empty(self) -> bool:
        """Return ``True`` if the receiver is (conditionally) empty."""
        return False

    def _eval_when(self, cnode: "InstanceNode") -> None:
        return

class Empty(SchemaPattern, metaclass=_Singleton):
    """Singleton class representing the empty pattern."""

    def nullable(self, ctype: ContentType) -> bool:
        """Override the superclass method."""
        return True

    def deriv(self, x: str, ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return NotAllowed()

    def empty(self) -> bool:
        """Override the superclass method."""
        return True

    def tree(self, indent: int = 0):
        return " " * indent + "Empty"

    def __str__(self) -> str:
        return "Empty"

class NotAllowed(SchemaPattern):

    def deriv(self, x: str, ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return self

    def tree(self, indent: int = 0):
        return " " * indent + "NotAllowed"

    def __str__(self) -> str:
        return "NotAllowed"

class Conditional(SchemaPattern):
    """Class representing conditional pattern."""

    def __init__(self, when: Expr):
        """Initialize the class instance."""
        self.when = when
        self._val_when = None # type: bool

    def empty(self) -> bool:
        """Override the superclass method."""
        return self.when and not self._val_when

    def _eval_when(self, cnode: "InstanceNode") -> None:
        self._val_when = bool(self.when.evaluate(cnode))

    def check_when(self) -> bool:
        return not self.when or self._val_when

class Typeable(SchemaPattern):
    """Multiple content types and their combinations."""

    def __init__(self, ctype: ContentType):
        """Initialize the class instance."""
        self.ctype = ctype

    def match_ctype(self, ctype) -> bool:
        return self.ctype.value & ctype.value != 0

class ConditionalPattern(Conditional):
    """Class representing conditional pattern."""

    def __init__(self, p: SchemaPattern, when: Expr):
        """Initialize the class instance."""
        super().__init__(when)
        self.pattern = p

    def _eval_when(self, cnode: "InstanceNode") -> None:
        super()._eval_when(cnode)
        self.pattern._eval_when(cnode)

    def nullable(self, ctype: ContentType) -> bool:
        """Override the superclass method."""
        return (not self.check_when() or self.pattern.nullable(ctype))

    def deriv(self, x: str, ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return (self.pattern.deriv(x, ctype) if self.check_when() else
                NotAllowed())

    def tree(self, indent: int = 0):
        return (" " * indent + "Conditional\n" +
                self.pattern.tree(indent + 2))

    def __str__(self) -> str:
        return str(self.pattern)

class Member(Typeable, Conditional):

    def __init__(self, name: InstanceName, ctype: ContentType,
                 when: Expr):
        Typeable.__init__(self, ctype)
        Conditional.__init__(self, when)
        self.name = name

    def _eval_when(self, cnode: "InstanceNode") -> None:
        if self.when:
            dummy = cnode.put_member(self.name, (None,))
            super()._eval_when(dummy)

    def nullable(self, ctype: ContentType) -> bool:
        """Override the superclass method."""
        return not (self.match_ctype(ctype) and self.check_when())

    def deriv(self, x: str, ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return (Empty() if
                self.name == x and self.match_ctype(ctype) and self.check_when()
                else NotAllowed())

    def tree(self, indent: int = 0):
        return " " * indent + "Member " + self.name

    def __str__(self) -> str:
        return "member '{}'".format(self.name)

class Alternative(SchemaPattern):

    @classmethod
    def combine(cls, p: SchemaPattern, q: SchemaPattern) -> "Alternative":
        if isinstance(p, NotAllowed): return q
        if isinstance(q, NotAllowed): return p
        return cls(p, q)

    def __init__(self, p: SchemaPattern, q: SchemaPattern):
        self.left = p
        self.right = q

    def _eval_when(self, cnode: "InstanceNode") -> None:
        super()._eval_when(cnode)
        self.left._eval_when(cnode)
        self.right._eval_when(cnode)

    def nullable(self, ctype: ContentType) -> bool:
        """Override the superclass method."""
        return self.left.nullable(ctype) or self.right.nullable(ctype)

    def deriv(self, x: str, ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return Alternative.combine(self.left.deriv(x, ctype),
                                   self.right.deriv(x, ctype))

    def tree(self, indent: int = 0):
        return (" " * indent + "Alternative\n" +
                self.left.tree(indent + 2) + "\n" +
                self.right.tree(indent + 2))

    def __str__(self) -> str:
        return str(self.left) + " or " + str(self.right)

class ChoicePattern(Alternative, Typeable):

    def __init__(self, p: SchemaPattern, q: SchemaPattern,
                 name: YangIdentifier):
        super().__init__(p, q)
        self.ctype = ContentType.all # type: ContentType
        self.name = name

    def nullable(self, ctype: ContentType):
        return not self.match_ctype(ctype)

    def deriv(self, x: str, ctype: ContentType):
        return (super().deriv(x, ctype) if self.match_ctype(ctype) else
                NotAllowed())

    def tree(self, indent: int = 0):
        return " " * indent + "Choice {}\n{}\n{}".format(
            self.name,
            self.left.tree(indent + 2), self.right.tree(indent + 2))

class Pair(SchemaPattern):

    @classmethod
    def combine(cls, p: SchemaPattern, q: SchemaPattern):
        if p.empty(): return q
        if q.empty(): return p
        if isinstance(p, NotAllowed): return p
        if isinstance(q, NotAllowed): return q
        return cls(p, q)

    def __init__(self, p: SchemaPattern, q: SchemaPattern):
        self.left = p
        self.right = q

    def nullable(self, ctype: ContentType) -> bool:
        """Override the superclass method."""
        return (self.left.nullable(ctype) and
                self.right.nullable(ctype))

    def deriv(self, x: str, ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return Alternative.combine(
            Pair.combine(self.left.deriv(x, ctype), self.right),
            Pair.combine(self.right.deriv(x, ctype), self.left))

    def _eval_when(self, cnode: "InstanceNode") -> None:
        self.left._eval_when(cnode)
        self.right._eval_when(cnode)

    def tree(self, indent: int = 0):
        return (" " * indent + "Pair\n" +
                self.left.tree(indent + 2) + "\n" +
                self.right.tree(indent + 2))

    def __str__(self) -> str:
        return str(self.left)
