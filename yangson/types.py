from typing import Optional, Tuple

# Type aliases

RevisionDate = str
Uri = str
YangIdentifier = str
ModuleId = Tuple[YangIdentifier, Optional[RevisionDate]]
QName = Tuple[YangIdentifier, Optional[YangIdentifier]] # (local name, module)
