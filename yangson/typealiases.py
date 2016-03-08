"""Type aliases (for type hints)."""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

RevisionDate = Optional[str]
Uri = str
YangIdentifier = str
QName = str # [YangIdentifier:]YangIdentifier
ScalarValue = Union[int, Decimal, str]
NodeName = Tuple[YangIdentifier, YangIdentifier] # (namespace, name)
SchemaAddress = List[NodeName]
ModuleId = Tuple[YangIdentifier, Optional[RevisionDate]]
