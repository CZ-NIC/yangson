from typing import Any, List, Optional, Tuple, Union

# Type aliases

RevisionDate = Optional[str]
Uri = str
SchemaNodeId = str
YangIdentifier = str
ModuleId = Tuple[YangIdentifier, Optional[RevisionDate]]
Range = List[Tuple[Any, Any]]
QName = Tuple[YangIdentifier, YangIdentifier]
NodeName = Union[YangIdentifier, QName]
