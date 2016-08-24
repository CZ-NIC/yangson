"""Type aliases (for type hints)."""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

RevisionDate = str # YYYY-MM-DD or empty string
Uri = str
YangIdentifier = str
InstanceName = str # [YangIdentifier ":"] YangIdentifier
PrefName = str # [Prefix ":"]YangIdentifier
InstanceIdentifier = str # YANG instance identifier
ResourceIdentifier = str # RESTCONF resource identifier
ScalarValue = Union[int, Decimal, str]
QualName = Tuple[YangIdentifier, YangIdentifier] # (name, namespace)
SchemaNodeId = str # [/] PrefName *("/" PrefName)
SchemaRoute = List[QualName]
SchemaPath = str # ["/"] ModuleName ":" NodeName *("/" [ModuleName ":"] NodeName)
DataPath = str # same syntax as SchemaPath but containing only data nodes
ModuleId = Tuple[YangIdentifier, RevisionDate]
RawScalar = Union[int, str]
RawObject = Dict[InstanceName, "RawValue"]
RawList = List[RawObject]
RawLeafList = List[RawScalar]
RawValue = Union[RawScalar, RawObject, RawList, RawLeafList]
