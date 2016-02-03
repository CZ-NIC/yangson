from enum import Enum
from typing import List, Dict, Optional
from yangson.types import ModuleId, Uri, YangIdentifier

class ConformanceType(Enum):
    implemented = 0
    imported = 1

class ModuleMetadata(object):
    """YANG module metadata contained in yang-library.
    """

    def __init__(self,
                 ns: Uri,
                 ct: ConformanceType,
                 fs: List[YangIdentifier] = [],
                 sch: Optional[Uri] = None) -> None:
        """Initialize the instance.

        :param ns: module namespace URI
        :param ct: conformance type
        :param fs: supported features
        :param sch: URL from which the module is available
        """
        self.namespace = ns
        self.conformance_type = ct
        self.feature = fs
        self.schema = sch

    def jsonify(self) -> Dict[str, str]:
        """Convert the receiver to a dictionary.
        """
        return { "namespace": self.namespace,
                 "conformance-type": self.conformance_type.name,
                 "feature": self.feature,
                 "schema": self.schema if self.schema else "" }

class YangLibrary(dict):
    """YANG Library data.
    """
    pass
