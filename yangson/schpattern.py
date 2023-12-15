# Copyright © 2016–2023 CZ.NIC, z. s. p. o.
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
from typing import Optional, TYPE_CHECKING
from .enumerations import ContentType
from .typealiases import InstanceName, _Singleton, YangIdentifier
from .xpathast import Expr
if TYPE_CHECKING:
    from .instance import InstanceNode


class SchemaPattern:
    """Abstract class for schema patterns."""

    @staticmethod
    def optional(p: "SchemaPattern") -> "SchemaPattern":
        """Make `p` an optional pattern."""
        return Alternative.combine(Empty(), p)

    @staticmethod
    def optional_config(p: "SchemaPattern") -> "SchemaPattern":
        """Make `p` an optional in configuration."""
        return Alternative.combine(EmptyConfig(), p)

    def nullable(self: "SchemaPattern", ctype: ContentType) -> bool:
        """Return ``True`` the receiver is nullable."""
        return False

    def empty(self: "SchemaPattern") -> bool:
        """Return ``True`` if the receiver is (conditionally) empty."""
        return False

    def _active(self: "SchemaPattern", ctype: ContentType) -> bool:
        """Return ``True`` if the receiver is active in the current context."""
        return True

    def _eval_when(self: "SchemaPattern", cnode: "InstanceNode") -> None:
        return

    def _mandatory_members(self: "SchemaPattern",
                           ctype: ContentType) -> list[InstanceName]:
        return None


class Empty(SchemaPattern, metaclass=_Singleton):
    """Singleton class representing the empty pattern."""

    def nullable(self: "Empty", ctype: ContentType) -> bool:
        """Override the superclass method."""
        return True

    def deriv(self: "Empty", x: str, ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return NotAllowed()

    def empty(self: "Empty") -> bool:
        """Override the superclass method."""
        return True

    def tree(self: "Empty", indent: int = 0):
        return " " * indent + "Empty"

    def __str__(self: "Empty") -> str:
        return "Empty"


class EmptyConfig(SchemaPattern, metaclass=_Singleton):
    """A pattern empty in configuration, not allowed otherwise."""

    def nullable(self: "EmptyConfig", ctype: ContentType) -> bool:
        """Override the superclass method."""
        return ctype == ContentType.config

    def deriv(self: "EmptyConfig", x: str, ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return NotAllowed()

    def tree(self: "EmptyConfig", indent: int = 0):
        return " " * indent + "EmptyConfig"

    def __str__(self: "EmptyConfig") -> str:
        return "EmptyConfig"

    def _mandatory_members(self: "Member",
                           ctype: ContentType) -> list[InstanceName]:
        if ctype.value & ContentType.nonconfig.value:
            return []


class NotAllowed(SchemaPattern, metaclass=_Singleton):

    def deriv(self: "NotAllowed", x: str, ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return self

    def tree(self: "NotAllowed", indent: int = 0):
        return " " * indent + "NotAllowed"

    def __str__(self: "NotAllowed") -> str:
        return "NotAllowed"


class Conditional(SchemaPattern):
    """Class representing conditional pattern."""

    def __init__(self: "Conditional", when: Expr):
        """Initialize the class instance."""
        self.when = when
        self._val_when = None  # type: bool

    def empty(self: "Conditional") -> bool:
        """Override the superclass method."""
        return self.when and not self._val_when

    def check_when(self: "Conditional") -> bool:
        return not self.when or self._val_when

    def _eval_when(self: "Conditional", cnode: "InstanceNode") -> None:
        self._val_when = bool(self.when.evaluate(cnode))

    def _active(self: "Conditional", ctype: ContentType) -> bool:
        return super()._active(ctype) and self.check_when()


class Typeable(SchemaPattern):
    """Multiple content types and their combinations."""

    def __init__(self: "Typeable", ctype: ContentType):
        """Initialize the class instance."""
        self.ctype = ctype

    def match_ctype(self: "Typeable", ctype) -> bool:
        return self.ctype.value & ctype.value != 0

    def _active(self: "Typeable", ctype: ContentType) -> bool:
        return super()._active(ctype) and self.match_ctype(ctype)


class ConditionalPattern(Conditional):
    """Class representing conditional pattern."""

    def __init__(self: "ConditionalPattern", p: SchemaPattern, when: Expr):
        """Initialize the class instance."""
        super().__init__(when)
        self.pattern = p

    def _eval_when(self: "ConditionalPattern", cnode: "InstanceNode") -> None:
        super()._eval_when(cnode)
        self.pattern._eval_when(cnode)

    def nullable(self: "ConditionalPattern", ctype: ContentType) -> bool:
        """Override the superclass method."""
        return (not self.check_when() or self.pattern.nullable(ctype))

    def deriv(self: "ConditionalPattern", x: str,
              ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return (self.pattern.deriv(x, ctype) if self.check_when() else
                NotAllowed())

    def tree(self: "ConditionalPattern", indent: int = 0):
        return (" " * indent + "Conditional\n" +
                self.pattern.tree(indent + 2))

    def __str__(self: "ConditionalPattern") -> str:
        return str(self.pattern)

    def _mandatory_members(self: "ConditionalPattern",
                           ctype: ContentType) -> list[InstanceName]:
        if self._active(ctype):
            return self.pattern._mandatory_members(ctype)


class Member(Typeable, Conditional):

    def __init__(self: "Member", name: InstanceName, ctype: ContentType,
                 when: Optional[Expr]):
        Typeable.__init__(self, ctype)
        Conditional.__init__(self, when)
        self.name = name

    def _eval_when(self: "Member", cnode: "InstanceNode") -> None:
        if self.when:
            dummy = cnode.put_member(self.name, (None,))
            super()._eval_when(dummy)

    def nullable(self: "Member", ctype: ContentType) -> bool:
        """Override the superclass method."""
        return not (self._active(ctype))

    def deriv(self: "Member", x: str, ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return (Empty() if
                self.name == x and self._active(ctype)
                else NotAllowed())

    def tree(self: "Member", indent: int = 0):
        return " " * indent + "Member " + self.name

    def __str__(self: "Member") -> str:
        return f"member '{self.name}'"

    def _mandatory_members(self: "Member",
                           ctype: ContentType) -> list[InstanceName]:
        if self._active(ctype):
            return [self.name]


class Alternative(SchemaPattern):

    @classmethod
    def combine(cls, p: SchemaPattern, q: SchemaPattern) -> "Alternative":
        if isinstance(p, NotAllowed):
            return q
        if isinstance(q, NotAllowed):
            return p
        return cls(p, q)

    def __init__(self: "Alternative", p: SchemaPattern, q: SchemaPattern):
        self.left = p
        self.right = q

    def _eval_when(self: "Alternative", cnode: "InstanceNode") -> None:
        super()._eval_when(cnode)
        self.left._eval_when(cnode)
        self.right._eval_when(cnode)

    def nullable(self: "Alternative", ctype: ContentType) -> bool:
        """Override the superclass method."""
        return self.left.nullable(ctype) or self.right.nullable(ctype)

    def deriv(self: "Alternative", x: str,
              ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return Alternative.combine(self.left.deriv(x, ctype),
                                   self.right.deriv(x, ctype))

    def tree(self: "Alternative", indent: int = 0):
        return (" " * indent + "Alternative\n" +
                self.left.tree(indent + 2) + "\n" +
                self.right.tree(indent + 2))

    def __str__(self: "Alternative") -> str:
        return f"{self.left!s} or {self.right!s}"

    def _mandatory_members(self: "Alternative",
                           ctype: ContentType) -> list[InstanceName]:
        lm = self.left._mandatory_members(ctype)
        rm = self.right._mandatory_members(ctype)
        if lm is not None and rm is not None:
            return lm + rm


class ChoicePattern(Alternative, Typeable):

    def __init__(self: "ChoicePattern", p: SchemaPattern, q: SchemaPattern,
                 name: YangIdentifier):
        super().__init__(p, q)
        self.ctype = ContentType.all  # type: ContentType
        self.name = name

    def nullable(self: "ChoicePattern", ctype: ContentType):
        return not self.match_ctype(ctype)

    def deriv(self: "ChoicePattern", x: str, ctype: ContentType):
        return (super().deriv(x, ctype) if self.match_ctype(ctype) else
                NotAllowed())

    def tree(self: "ChoicePattern", indent: int = 0):
        return (" " * indent +
                f"Choice {self.name}\n{self.left.tree(indent + 2)}\n"
                f"{self.right.tree(indent + 2)}")

    def _members(self: "ChoicePattern",
                 ctype: ContentType) -> list[InstanceName]:
        return super()._members(ctype) if self._active(ctype) else []


class Pair(SchemaPattern):

    @classmethod
    def combine(cls, p: SchemaPattern, q: SchemaPattern):
        if p.empty():
            return q
        if q.empty():
            return p
        if isinstance(p, NotAllowed):
            return p
        if isinstance(q, NotAllowed):
            return q
        return cls(p, q)

    def __init__(self: "Pair", p: SchemaPattern, q: SchemaPattern):
        self.left = p
        self.right = q

    def nullable(self: "Pair", ctype: ContentType) -> bool:
        """Override the superclass method."""
        return (self.left.nullable(ctype) and
                self.right.nullable(ctype))

    def deriv(self: "Pair", x: str, ctype: ContentType) -> SchemaPattern:
        """Return derivative of the receiver."""
        return Alternative.combine(
            Pair.combine(self.left.deriv(x, ctype), self.right),
            Pair.combine(self.right.deriv(x, ctype), self.left))

    def _eval_when(self: "Pair", cnode: "InstanceNode") -> None:
        self.left._eval_when(cnode)
        self.right._eval_when(cnode)

    def tree(self: "Pair", indent: int = 0):
        return (" " * indent + "Pair\n" +
                self.left.tree(indent + 2) + "\n" +
                self.right.tree(indent + 2))

    def __str__(self: "Pair") -> str:
        return str(self.left)

    def _mandatory_members(self: "Pair",
                           ctype: ContentType) -> list[InstanceName]:
        if self.left._mandatory_members(ctype) is None:
            return self.right._mandatory_members(ctype)
        elif self.right._mandatory_members(ctype) is None:
            return self.left._mandatory_members(ctype)
        else:
            return (self.left._mandatory_members(ctype) +
                    self.right._mandatory_members(ctype))
