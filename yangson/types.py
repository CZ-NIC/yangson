from typing import Optional, Tuple

# Type aliases

RevisionDate = Optional[str]
Uri = str
YangIdentifier = str
ModuleId = Tuple[YangIdentifier, Optional[RevisionDate]]
QName = Tuple[YangIdentifier, Optional[YangIdentifier]] # (local name, module)
