"""This module contains classes for working with YANG Library data.
"""

from enum import Enum
from json import dumps, loads
from json.decoder import JSONDecodeError
from typing import List, Dict, Optional
from yangson.exception import YangsonException
from yangson.types import ModuleId, RevisionDate, Uri, YangIdentifier
from yangson.module import from_file, Statement, StatementNotFound

class ConformanceType(Enum):
    implemented = 0
    imported = 1

    def __str__(self):
        """Return string representation of the receiver."""
        return "import" if self.value else "implement"

class Module(object):
    """Abstract class for data common to both modules and submodules."""

    module_dir = "/usr/local/share/yang"
    """Local filesystem directory from which YANG modules can be retrieved."""

    @staticmethod
    def revision(rev: str) -> RevisionDate:
        """Decode revision.

        :param rev: revision date or ``""`` (= revision not specified)
        """
        return rev if rev else None

    def __init__(self, sch: Optional[Uri]) -> None:
        """Initialize the instance.

        :param sch: URL from which the module can be retrieved
        """
        self.schema = sch
        self.content = None

    def _to_dict(self, name: YangIdentifier,
                 rev: RevisionDate) -> Dict[str, str]:
        """Convert receiver's data to a dictionary.

        :param name: module name
        :param rev: revision date
        """
        res = { "name": name }
        res["revision"] =  rev if rev else ""
        if self.schema:
            res["schema"] = self.schema
        return res

    def _load(self, name: YangIdentifier, rev: RevisionDate) -> None:
        """Load the module content.

        :param name: module name
        :param rev: revision date
        """
        fn = "{}/{}{}.yang".format(self.module_dir, name,
                                   ("@" + rev) if rev else "")
        self.content = from_file(fn)

class Submodule(Module):
    """Submodule data.
    """

    def __init__(self,
                 name: YangIdentifier,
                 revision: str,
                 schema: Optional[Uri] = None) -> None:
        """Initialize the instance.

        :param name: module name
        :param revision: revision date or ``""`` (= revision not specified)
        """
        super(Submodule, self).__init__(schema)
        self.name = name
        self.revision = self.revision(revision)
        self.schema = schema

    def _to_dict(self):
        """Convert receiver's data to a dictionary."""
        return super(Submodule, self)._to_dict(self.name, self.revision)

class MainModule(Module):
    """Main module data."""

    def __init__(self,
                 ct: str,
                 namespace: Uri,
                 feature: List[YangIdentifier] = [],
                 submodules: Dict[str, List[Submodule]] = {"submodule": []},
                 deviation: List[ModuleId] = [],
                 schema: Optional[Uri] = None) -> None:
        """Initialize the instance.

        :param ct: conformance type string ("implement" or "import")
        :param namespace: module namespace URI
        :param feature: supported features
        :param submodules: object containing a list of submodules
        :param deviation: list of deviation modules
        :param schema: URL from which the module is available
        """
        super(MainModule, self).__init__(schema)
        self.namespace = namespace
        self.feature = feature
        self.deviation = [ (d["name"], self.revision(d["revision"]))
                           for d in deviation ]
        if ct == "implement":
            self.conformance_type = ConformanceType.implemented
        elif ct == "import":
            self.conformance_type = ConformanceType.imported
        else:
            raise BadYangLibraryData("unknown conformance type")
        try:
            sub = submodules["submodule"]
        except:
            raise BadYangLibraryData("bad specification of submodules")
        self.submodule = [ Submodule(**s) for s in sub ]

    def _to_dict(self, name: YangIdentifier,
                 rev: RevisionDate) -> Dict[str, str]:
        """Convert the receiver to a dictionary.

        :param name: module name
        :param rev: revision date
        """
        res = super(MainModule, self)._to_dict(name, rev)
        res.update({ "namespace": self.namespace,
                     "conformance-type": str(self.conformance_type) })
        if self.feature:
            res["feature"] = self.feature
        if self.submodule:
            res["submodules"] = { "submodule":
                                  [ s._to_dict() for s in self.submodule ] }
        if self.deviation:
            res["deviation"] = self.deviation
        return res

    def _load(self, name: YangIdentifier, rev: RevisionDate) -> None:
        """Load the content of the module and all its submodules.

        :param name: module name
        :param rev: revision date
        """
        super(MainModule, self)._load(name, rev)
        for s in self.submodule:
            s._load(s.name, s.rev)

class YangLibrary(dict):
    """YANG Library data.
    """

    @classmethod
    def from_json(cls, txt: str) -> "YangLibrary":
        """Return an instance initialized from JSON text.

        :param txt: YANG Library information as JSON text
        :raises BadYangLibraryData: if `txt` is broken
        """
        res = cls()
        try:
            json = loads(txt)["ietf-yang-library:modules-state"]["module"]
            for item in json:
                name = item.pop("name")
                revstr = item.pop("revision")
                rev = Module.revision(revstr)
                ctstr = item.pop("conformance-type")
                m = MainModule(ctstr, **item)
                res[(name, rev)] = m
        except (JSONDecodeError, KeyError, AttributeError):
            raise BadYangLibraryData()
        return res

    def to_json(self) -> str:
        """Serialize YANG Library information in JSON format.
        """
        val = [ self[k]._to_dict(*k) for k in self ]
        return dumps(val)

    def load(self) -> None:
        """Load contents of all YANG modules."""
        for k in self:
            self[k]._load(*k)

class BadYangLibraryData(YangsonException):
    "Exception to be raised for broken YANG Library data."""

    def __init__(self, reason: str = "broken yang-library data") -> None:
        self.reason = reason

    def __str__(self) -> str:
        return self.reason
