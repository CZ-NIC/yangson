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

"""Structured values of instance nodes.

This module implements the following classes:

* StructuredValue: Abstract class for structured values of instance nodes.
* ArrayValue: Cooked array value of an instance node.
* ObjectValue: Cooked object value of an instance node.
"""

from datetime import datetime
from typing import Dict, List, Union
from .typealiases import InstanceName, PrefName, ScalarValue

# Type aliases
Value = Union[ScalarValue, "ArrayValue", "ObjectValue"]
"""All possible types of cooked values (scalar and structured)."""

EntryValue = Union[ScalarValue, "ObjectValue"]
"""Type of the value a list ot leaf-list entry."""

InstanceKey = Union[InstanceName, int]
"""Index of an array entry or name of an object member."""

MetadataObject = Dict[PrefName, ScalarValue]
"""Metadata object [RFC 7952]_."""


class StructuredValue:
    """Abstract class for array and object values."""

    def __init__(self, ts: datetime):
        """Initialize class instance.

        Args:
        :param ts: creation timestamp
        """
        self.timestamp = ts if ts else datetime.now()

    def copy(self) -> "StructuredValue":
        """Return a shallow copy of the receiver."""
        return self.__class__(super().copy(), datetime.now())

    def __setitem__(self, key: InstanceKey, value: Value) -> None:
        super().__setitem__(key, value)
        self.timestamp = datetime.now()

    def __eq__(self, val: "StructuredValue") -> bool:
        """Return ``True`` if the receiver equal to `val`.

        Args:
        :param val: value to compare
        """
        return self.__class__ == val.__class__ and hash(self) == hash(val)

    def __hash__(self) -> int:
        """Return hash value for the receiver."""
        raise NotImplementedError()


class ArrayValue(StructuredValue, list):
    """This class represents cooked array values."""

    def __init__(self, val: List[EntryValue] = [], ts: datetime = None):
        StructuredValue.__init__(self, ts)
        list.__init__(self, val)

    def __hash__(self) -> int:
        """Return hash value for the receiver."""
        return tuple([x.__hash__() for x in self]).__hash__()


class ObjectValue(StructuredValue, dict):
    """This class represents cooked object values."""

    def __init__(self, val: Dict[InstanceName, Value] = {},
                 ts: datetime = None):
        StructuredValue.__init__(self, ts)
        dict.__init__(self, val)

    def __hash__(self) -> int:
        """Return hash value for the receiver."""
        sks = sorted(self.keys())
        return tuple([(k, self[k].__hash__()) for k in sks]).__hash__()
