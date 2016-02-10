from enum import Enum
from typing import List, Dict, Optional
from .exception import YangsonException
from .typealiases import ModuleId, RevisionDate, Uri, YangIdentifier
from .modparser import from_file

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
    def basename(name: YangIdentifier, rev: RevisionDate = None) -> str:
        """Base name of a module file.

        :param name: module name
        :param rev: optional revision date
        """
        if rev is None:
            return name
        else:
            return "{}@{}".format(name, rev)

    @staticmethod
    def revision(rev: str) -> RevisionDate:
        """Decode revision.

        :param rev: revision date or ``""`` (= revision not specified)
        """
        return rev if rev else None

    def __init__(self, url: Optional[Uri]) -> None:
        """Initialize the instance.

        :param url: URL from which the module can be retrieved
        """
        self.url = url
        self.content = None # type: S
        self.prefix_map = {} # type: Dict[YangIdentifier, ModuleId]

    def _to_dict(self, name: YangIdentifier,
                 rev: RevisionDate) -> Dict[str, str]:
        """Convert receiver's data to a dictionary.

        :param name: module name
        :param rev: revision date
        """
        res = { "name": name }
        res["revision"] =  rev if rev else ""
        if self.url:
            res["schema"] = self.url
        return res

    def _load(self, name: YangIdentifier, rev: RevisionDate) -> None:
        """Load the module content.

        :param name: module name
        :param rev: revision date
        """
        fn = "{}/{}.yang".format(self.module_dir, self.basename(name, rev))
        self.content = from_file(fn)

    def _resolve_imports(self, schema: "Schema") -> None:
        """Assign `ModuleId` to each prefix used in the receiver.

        :param schema: data model schema
        :raises UnresolvableImport: if the receiver doesn't contain the module
        """
        for imp in self.content.find_all("import"):
            name = imp.argument
            prefix = imp.find1("prefix", required=True).argument
            revst = imp.find1("revision-date")
            rev = revst.argument if revst else None
            modid = schema.find_module_id(name, rev)
            if modid:
                self.prefix_map[prefix] = modid
            else:
                raise UnresolvableImport(name, rev)

class Submodule(Module):
    """Submodule data.
    """

    def __init__(self,
                 name: YangIdentifier,
                 revision: str,
                 url: Optional[Uri] = None) -> None:
        """Initialize the instance.

        :param name: module name
        :param revision: revision date or ``""`` (= revision not specified)
        """
        super().__init__(url)
        self.name = name
        self.revision = self.revision(revision)

    def _to_dict(self):
        """Convert receiver's data to a dictionary."""
        return super()._to_dict(self.name, self.revision)

class MainModule(Module):
    """Main module data."""

    def __init__(self,
                 ct: str,
                 namespace: Uri,
                 feature: List[YangIdentifier] = [],
                 submodules: Dict[str, List[Submodule]] = {"submodule": []},
                 deviation: List[ModuleId] = [],
                 url: Optional[Uri] = None) -> None:
        """Initialize the instance.

        :param ct: conformance type string ("implement" or "import")
        :param namespace: module namespace URI
        :param feature: supported features
        :param submodules: object containing a list of submodules
        :param deviation: list of deviation modules
        :param url: URL from which the module is available
        """
        super().__init__(url)
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
        res = super()._to_dict(name, rev)
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
        super()._load(name, rev)
        for s in self.submodule:
            s._load(s.name, s.rev)

    def _resolve_imports(self, schema: "YangLibrary") -> None:
        """Assign `ModuleId` to each prefix used in the receiver and submodules.

        :param schema: YANG Library containing all avaliable modules.
        :raises UnresolvableImport: if the receiver doesn't contain the module
        """
        super()._resolve_imports(schema)
        for s in self.submodule:
            s._resolve_imports(schema)

class UnresolvableImport(YangsonException):
    """Exception to be raised if an imported module isn't found."""

    def __init__(self, name: YangIdentifier, rev: RevisionDate) -> None:
        self.name = name
        self.revision = rev

    def __str__(self) -> str:
        return Module.basename(self.name, self.revision)
