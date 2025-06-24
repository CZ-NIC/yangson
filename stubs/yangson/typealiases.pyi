from decimal import Decimal
from typing import Union
from .instance import InstanceNode

RevisionDate = str
YangIdentifier = str
InstanceName = str
PrefName = str
InstanceIdentifier = str
JSONPointer = str
ResourceIdentifier = str
ScalarValue = Union[int, Decimal, str, tuple[None]]
QualName = tuple[YangIdentifier, YangIdentifier]
SchemaNodeId = str
SchemaRoute = list[QualName]
SchemaPath = str
DataPath = str
ModuleId = tuple[YangIdentifier, RevisionDate]
RawScalar = Union[bool, int, str, list[None]]
RawObject = dict[InstanceNode, "RawValue"]
RawMetadataObject = dict[PrefName, RawScalar]
RawEntry = Union[RawScalar, RawObject]
RawList = list[RawObject]
RawLeafList = list[RawScalar]
RawValue = Union[RawScalar, RawObject, RawList, RawLeafList]

class _Singleton(type):
    def __call__(cls, *args, **kwargs): ... # type: ignore[no-untyped-def]
