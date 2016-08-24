"""Type aliases for use with type hints [PEP484]_."""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

RevisionDate = str
"""RevisionDate in the format ``YYYY-MM-DD``, or empty string."""

YangIdentifier = str
"""YANG identifier, see sec. `6.2`_ of [Bjo16]_."""

InstanceName = str
"""Object member name (simple or qualified), see sec. `4`_ of [Lho16]_."""

PrefName = str
"""Name with optional prefix – [YangIdentifier ":"] YangIdentifier."""

InstanceIdentifier = str
"""YANG instance identifier, see sec. `6.11`_ of [Lho16]_."""

ResourceIdentifier = str
"""RESTCONF resource identifier, see sec. `3.5.3`_ of [BBW16]_."""

ScalarValue = Union[int, Decimal, str]
"""Scalar value of an InstanceNode."""

QualName = Tuple[YangIdentifier, YangIdentifier]
"""Qualified name, tuple of name and module name."""

SchemaNodeId = str
"""Schema node identifier, see. sec. `6.5`_ in [Bjo16]_."""

SchemaRoute = List[QualName]
"""Schema route, a list of qualified names of schema nodes."""

SchemaPath = str
"""Schema path similar to instance identifier containing names of schema nodes."""

DataPath = str # same syntax as SchemaPath but containing only data nodes
"""SchemaPath containing only names of data nodes."""

ModuleId = Tuple[YangIdentifier, RevisionDate]
"""Module identifier: (YangIdentifier, RevisionDate)."""

RawScalar = Union[bool, int, str]
"""Raw scalar value as produced by JSON parser."""

RawObject = Dict[InstanceName, "RawValue"]
"""Raw object as returned by JSON parser."""

RawList = List[RawObject]
"""List of raw objects."""

RawLeafList = List[RawScalar]
"""List of raw scalars."""

RawValue = Union[RawScalar, RawObject, RawList, RawLeafList]
"""Raw value of any type."""
