"""This module contains classes for working with YANG Library data.
"""

from enum import Enum
from json import dumps, loads
from typing import List, Dict, Optional
from yangson.types import ModuleId, RevisionDate, Uri, YangIdentifier
from yangson.module import from_file, Statement, StatementNotFound

class ConformanceType(Enum):
    implemented = 0
    imported = 1

    def __str__(self):
        """Return string representation of the receiver."""
        return "import" if self.value else "implement"

class ModuleData(object):
    """Abstract class for data common to both modules and submodules."""

    module_dir = "/usr/local/share/yang"
    """Local filesystem directory from which YANG modules can be retrieved."""

    def __init__(self,
                 name: YangIdentifier,
                 rev: Optional[RevisionDate] = None,
                 sch: Optional[Uri] = None) -> None:
        """Initialize the instance.

        :param name: YANG module name
        :param rev: revision date
        :param sch: URL from which the module can be retrieved
        """
        self.name = name
        self.revision = rev
        self.schema = sch
        self.content = None

    def jsonify(self) -> Dict[str, str]:
        """Convert receiver's metadata to a dictionary."""
        res = { "name": self.name }
        res["revision"] =  self.revision if self.revision else ""
        if self.schema:
            res["schema"] = self.schema
        return res

    def file_name(self) -> str:
        """Return the name of module file."""
        return "{}/{}{}.yang".format(self.module_dir, self.name,
                              ("@" + self.revision) if self.revision else "")

    def load(self) -> None:
        """Load the module content."""
        fn = self.module_dir + "/" + self.name
        if self.revision:
            fn += "@" + self.revision
        self.content = from_file(self.file_name())

class SubmoduleData(ModuleData):
    """Submodule data.
    """

    pass

class MainModuleData(ModuleData):
    """Main module data."""

    def __init__(self,
                 name: YangIdentifier,
                 rev: Optional[RevisionDate] = None,
                 ct: ConformanceType = ConformanceType.implemented,
                 fs: List[YangIdentifier] = [],
                 sub: List[SubmoduleData] = [],
                 dev: List[ModuleId] = [],
                 sch: Optional[Uri] = None) -> None:
        """Initialize the instance.

        :param name: YANG module name
        :param rev: revision date
        :param ct: conformance type
        :param fs: supported features
        :param sub: metadata for submodules
        :param dev: names and revisions of deviation modules
        :param sch: URL from which the module is available
        """
        super(MainModuleData, self).__init__(name, rev, sch)
        self.conformance_type = ct
        self.feature = fs
        self.submodule = sub
        self.deviation = dev

    def jsonify(self) -> Dict[str, str]:
        """Convert the receiver to a dictionary.
        """
        if self.content is None: self.load()
        res = super(MainModuleData, self).jsonify()
        res.update({ "namespace": self.namespace,
                     "conformance-type": str(self.conformance_type) })
        if self.feature:
            res["feature"] = self.feature
        if self.submodule:
            res["submodule"] = self.submodule
        if self.deviation:
            res["deviation"] = self.deviation
        return res

    def load(self) -> None:
        """Load the module content and read other data form it."""
        super(MainModuleData, self).load()
        self.namespace = self.content.find1("namespace").argument

class YangLibrary(list):
    """YANG Library data.
    """

    def to_json(self) -> str:
        """Serialize YANG Library information in JSON format.
        """
        val = [ m.jsonify() for m in self ]
        return dumps(val)
