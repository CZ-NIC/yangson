"""This module contains classes for working with YANG Library data.
"""

from enum import Enum
from json import dumps, loads
from typing import List, Dict, Optional
from yangson.types import ModuleId, RevisionDate, Uri, YangIdentifier

class ConformanceType(Enum):
    implemented = 0
    imported = 1

    def __str__(self):
        """Return string representation of the receiver."""
        return "import" if self.value else "implement"

class DeviationMetadata(object):
    """Deviation module metadata.
    """
    def __init__(self,
                 name: YangIdentifier,
                 rev: RevisionDate) -> None:
        """Initialize the instance.

        :param name: YANG module name
        :param rev: revision date
        """
        self.name = name
        self.revision = rev

    def jsonify(self) -> Dict[str, str]:
        """Convert the receiver to a dictionary.
        """
        return { "name": self.name,
                 "revision": self.revision }

class SubmoduleMetadata(DeviationMetadata):
    """Submodule metadata.
    """

    def __init__(self,
                 name: YangIdentifier,
                 rev: RevisionDate,
                 sch: Optional[Uri] = None) -> None:
        """Initialize the instance.

        :param name: YANG module name
        :param rev: revision date
        :param sch: URL from which the module is available
        """
        super(SubmoduleMetadata, self).__init__(name, rev)
        self.schema = sch

    def jsonify(self) -> Dict[str, str]:
        """Convert the receiver to a dictionary.
        """
        res = super(SubmoduleMetadata, self).jsonify()
        res["schema"] = self.schema if self.schema else ""
        return res

class ModuleMetadata(SubmoduleMetadata):
    """Main module metadata.
    """

    def __init__(self,
                 name: YangIdentifier,
                 rev: RevisionDate,
                 ns: Uri,
                 ct: ConformanceType,
                 fs: List[YangIdentifier] = [],
                 sub: List[SubmoduleMetadata] = [],
                 dev: List[DeviationMetadata] = []
                 sch: Optional[Uri] = None) -> None:
        """Initialize the instance.

        :param name: YANG module name
        :param rev: revision date
        :param ns: module namespace URI
        :param ct: conformance type
        :param fs: supported features
        :param sub: metadata for submodules
        :param dev: deviation modules
        :param sch: URL from which the module is available
        """
        super(ModuleMetadata, self).__init__(name, rev, sch)
        self.namespace = ns
        self.conformance_type = ct
        self.feature = fs
        self.submodule = sub
        self.deviation = dev

    def jsonify(self) -> Dict[str, str]:
        """Convert the receiver to a dictionary.
        """
        res = super(ModuleMetadata, self).jsonify()
        res.update({ "namespace": self.namespace,
                     "conformance-type": str(self.conformance_type) })
        if self.feature:
            res["feature"] = self.feature
        if self.submodule:
            res["submodule"] = self.submodule
        if self.deviation:
            res["deviation"] = self.deviation
        return res

class YangLibrary(list):
    """YANG Library data.
    """

    def to_json(self) -> str:
        """Serialize YANG Library information in JSON format.
        """
        val = [ m.jsonify() for m in self ]
        return dumps(val)
