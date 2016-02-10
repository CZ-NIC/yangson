from typing import Any, List, Optional, Tuple

# Type aliases

RevisionDate = Optional[str]
Uri = str
YangIdentifier = str
ModuleId = Tuple[YangIdentifier, Optional[RevisionDate]]
QName = Tuple[YangIdentifier, Optional[YangIdentifier]] # (local name, module)
Range = List[Tuple[Any, Any]]
