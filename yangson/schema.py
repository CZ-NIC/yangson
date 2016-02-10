import json
from json.decoder import JSONDecodeError
from typing import Optional
from .module import MainModule
from yangson.exception import YangsonException
from yangson.typealiases import ModuleId, RevisionDate, YangIdentifier

class Schema(object):
    """YANG data model schema."""

    @classmethod
    def read_yang_library(cls, txt: str) -> "YangLibrary":
        """Return an instance initialized from JSON text.

        :param txt: YANG Library information as JSON text
        :raises BadYangLibraryData: if `txt` is broken
        """
        res = cls()
        try:
            yl = json.loads(txt)
            for item in yl["ietf-yang-library:modules-state"]["module"]:
                name = item.pop("name")
                revstr = item.pop("revision")
                rev = revstr if revstr else None
                ctstr = item.pop("conformance-type")
                m = MainModule(ctstr, **item)
                res.modules[(name, rev)] = m
        except (JSONDecodeError, KeyError, AttributeError):
            raise BadYangLibraryData()
        return res

    def __init__(self) -> None:
        """Initialize the instance."""
        self.modules = {}
        self.patches = {}

    def write_yang_library(self) -> str:
        """Serialize YANG Library information in JSON format.
        """
        val = [ self.modules[k]._to_dict(*k) for k in self.modules ]
        return json.dumps(val)

    def find_module_id(self, name: YangIdentifier,
             rev: RevisionDate = None) -> Optional[ModuleId]:
        """Return a key in the receiver or ``None``.

        :param name: module name
        :param rev: revision date
        """
        if (name, rev) in self.modules: return (name, rev)
        if rev is None:
            for k in self.modules:
                if k[0] == name: return k

    def complete(self) -> None:
        """Find and fill in all missing data."""
        self.load_modules()
        self.resolve_imports()

    def load_modules(self) -> None:
        """Load contents of all YANG modules."""
        for k in self.modules:
            self.modules[k]._load(*k)

    def resolve_imports(self):
        """Assign modules & revisions to prefixes."""
        for k in self.modules:
            self.modules[k]._resolve_imports(self)

class BadYangLibraryData(YangsonException):
    """Exception to be raised for broken YANG Library data."""

    def __init__(self, reason: str = "broken yang-library data") -> None:
        self.reason = reason

    def __str__(self) -> str:
        return self.reason
