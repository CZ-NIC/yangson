from _typeshed import Incomplete
from decimal import Decimal

RevisionDate = str
YangIdentifier = str
InstanceName = str
PrefName = str
InstanceIdentifier = str
JSONPointer = str
ResourceIdentifier = str
ScalarValue = int | Decimal | str | tuple[None]
QualName = tuple[YangIdentifier, YangIdentifier]
SchemaNodeId = str
SchemaRoute = list[QualName]
SchemaPath = str
DataPath = str
ModuleId = tuple[YangIdentifier, RevisionDate]
RawScalar = bool | int | str | list[None]
RawObject: Incomplete
RawMetadataObject = dict[PrefName, RawScalar]
RawEntry = RawScalar | RawObject
RawList = list[RawObject]
RawLeafList = list[RawScalar]
RawValue = RawScalar | RawObject | RawList | RawLeafList

class _Singleton(type):
    def __call__(cls, *args, **kwargs): ... # type: ignore[no-untyped-def]
