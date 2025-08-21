# Copyright © 2016–2025 CZ.NIC, z. s. p. o.
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

"""A route into an instance value that is also used as the cooked value
of the instance-identifier type.

This module implements the following classes:

* InstanceRouteItem: Protocol class defining API for instance route items.
* InstanceRoute: Route into an instance value.
"""
from typing import Optional, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .instance import InstanceNode
    from .instvalue import ObjectValue, Value
    from .schemanode import DataNode

class InstanceRouteItem(Protocol):
    """This protocol class defines a required API for instance route items."""

    def __eq__(self, other: object) -> bool:
        """Return True if the receiver is equal to other."""

    def __str__(self) -> str:
        """Return string representation of the receiver."""

    def peek_step(self, val: "ObjectValue",
                  sn: "DataNode") -> tuple[Optional["Value"], "DataNode"]:
        """Return value addressed by the receiver relative to the current
        position together with its schema node.

        Args:
            val: Value at the current position.
            sn:  Schema node corresponding to the current position.
        """

    def goto_step(self, inst: "InstanceNode") -> "InstanceNode":
        """Return instance node addressed by the receiver.

        Args:
            inst: Current instance node.
        """
    

class InstanceRoute(tuple[InstanceRouteItem, ...]):
    """This class represents a route into an instance value."""

    def __str__(self) -> str:
        """Return instance-id as the string representation of the receiver."""
        if self:
            return "".join([str(c) for c in self])
        else:
            return "/"

    def __hash__(self) -> int:
        """Return the hash value of the receiver."""
        return self.__str__().__hash__()
