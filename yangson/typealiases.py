from typing import Any, Dict, List, Optional, Tuple, Union

# Type aliases

NodeName = str
RevisionDate = Optional[str]
Uri = str
YangIdentifier = str
ModuleId = Tuple[YangIdentifier, Optional[RevisionDate]]
Range = List[Tuple[Any, Any]]
QName = Tuple[YangIdentifier, YangIdentifier]
PrefixMap = Dict[YangIdentifier, ModuleId]
