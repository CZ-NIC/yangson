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

"""Type aliases for use with type hints [PEP484]_."""

from decimal import Decimal
from typing import Dict, List, Tuple, Union

RevisionDate = str
"""RevisionDate in the format ``YYYY-MM-DD``, or empty string."""

YangIdentifier = str
"""YANG identifier, see sec. `6.2`_ of [RFC7950]_."""

InstanceName = str
"""Object member name (simple or qualified), see sec. `4`_ of [RFC7951]_."""

PrefName = str
"""Name with optional prefix – [YangIdentifier ":"] YangIdentifier."""

InstanceIdentifier = str
"""YANG instance identifier, see sec. `6.11`_ of [RFC7951]_."""

JSONPointer = str
"""JSON Pointer [RFC6901]_."""

ResourceIdentifier = str
"""RESTCONF resource identifier, see sec. `3.5.3`_ of [RFC8040]_."""

ScalarValue = Union[int, Decimal, str, Tuple[None]]
"""Scalar value of an InstanceNode."""

QualName = Tuple[YangIdentifier, YangIdentifier]
"""Qualified name, tuple of name and module name."""

SchemaNodeId = str
"""Schema node identifier, see. sec. `6.5`_ in [RFC7950]_."""

SchemaRoute = List[QualName]
"""Schema route, a list of qualified names of schema nodes."""

SchemaPath = str
"""Schema path similar to instance identifier containing names of schema nodes."""

DataPath = str  # same syntax as SchemaPath but containing only data nodes
"""SchemaPath containing only names of data nodes."""

ModuleId = Tuple[YangIdentifier, RevisionDate]
"""Module identifier: (YangIdentifier, RevisionDate)."""

RawScalar = Union[bool, int, str, List[None]]
"""Raw scalar value as produced by JSON parser."""

RawObject = Dict[InstanceName, "RawValue"]
"""Raw object as returned by JSON parser."""

RawMetadataObject = Dict[PrefName, RawScalar]
"""Raw metadata object as returned by JSON parser."""

RawEntry = Union[RawScalar, RawObject]
"""Raw entry of a leaf-list or list."""

RawList = List[RawObject]
"""List of raw objects."""

RawLeafList = List[RawScalar]
"""List of raw scalars."""

RawValue = Union[RawScalar, RawObject, RawList, RawLeafList]
"""Raw value of any type."""


class _Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
