"""Type aliases (for type hints)."""

from typing import Any, Dict, List, Optional, Tuple, Union

RevisionDate = Optional[str]
Uri = str
YangIdentifier = str
Value = Any
QName = str # [YangIdentifier:]YangIdentifier
NodeName = Tuple[YangIdentifier, YangIdentifier] # (namespace, name)
SchemaAddress = List[NodeName]
ModuleId = Tuple[YangIdentifier, Optional[RevisionDate]]
Range = List[List[Any]]
PrefixMap = Dict[YangIdentifier, ModuleId]
