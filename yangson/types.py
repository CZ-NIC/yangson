from typing import Optional

# Type aliases

RevisionDate = str
Uri = str
YangIdentifier = str
ModuleId = (YangIdentifier, Optional[RevisionDate])
QName = (YangIdentifier, Optional[YangIdentifier]) # (local name, module)
