from typing import Any, Dict, List, Optional, Tuple, Union

# Type aliases

RevisionDate = Optional[str]
Uri = str
YangIdentifier = str
NodeName = Tuple[YangIdentifier, YangIdentifier]
SchemaAddress = List[NodeName]
ModuleId = Tuple[YangIdentifier, Optional[RevisionDate]]
Range = List[Tuple[Any, Any]]
QName = Tuple[YangIdentifier, YangIdentifier]
PrefixMap = Dict[YangIdentifier, ModuleId]
