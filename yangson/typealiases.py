"""Type aliases (for type hints)."""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

RevisionDate = Optional[str]
Uri = str
YangIdentifier = str
InstanceName = str # [YangIdentifier ":"] YangIdentifier
InstanceRoute = List[InstanceName]
PrefName = str # [Prefix ":"]YangIdentifier
InstanceIdentifier = str # YANG instance identifier
ResourceIdentifier = str # RESTCONF resource identifier
ScalarValue = Union[int, Decimal, str]
QualName = Tuple[YangIdentifier, Optional[YangIdentifier]] # (name, namespace)
SchemaRoute = List[QualName]
SchemaPath = str # ["/"] ModuleName ":" NodeName *("/" [ModuleName ":"] NodeName)
ModuleId = Tuple[YangIdentifier, RevisionDate]
RawScalar = Union[int, str]
RawObject = Dict[InstanceName, "RawValue"]
RawList = List[RawObject]
RawLeafList = List[RawScalar]
RawValue = Union[RawScalar, RawObject, RawList, RawLeafList]
