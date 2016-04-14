"""Type aliases (for type hints)."""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

RevisionDate = Optional[str]
Uri = str
YangIdentifier = str
JsonName = str # [YangIdentifier:]YangIdentifier
PrefName = str # [Prefix:]YangIdentifier
ScalarValue = Union[int, Decimal, str]
QualName = Tuple[YangIdentifier, YangIdentifier] # (name, namespace)
SchemaRoute = List[QualName]
ModuleId = Tuple[YangIdentifier, Optional[RevisionDate]]
