from enum import Enum
from typing import List, Dict, Optional
from .exception import YangsonException
from .typealiases import *
from .modparser import from_file

# Type aliases
ModuleDict = Dict[YangIdentifier, List["MainModule"]]

class SchemaNode(object):
    """Abstract superclass for schema nodes."""

    def __init__(self) -> None:
        """Initialize the instance:"""

        self.parent = None

class Internal(SchemaNode):
    """Abstract superclass for schema nodes that have children."""

    def __init__(self) -> None:
        """Initialize the instance."""
        super().__init__()
        self.children = {}

    def add_child(self, name: NodeName,
                  node: "SchemaNode") -> None:
        """Add `sn` as a child of the receiver.

        :param name: name of the child
        :param node: schema node
        """
        self.children[name] = node
        node.parent = self

class SchemaRoot(Internal):
    """Class for the global schema root."""

    def __init__(self, modules: ModuleDict) -> None:
        """Initialize the instance.

        :param modules: dictionary of modules comprising the schema
        """
        self.modules = modules

    def get_module_revision(
            self, name: YangIdentifier,
            rev: Optional[RevisionDate] = None) -> "MainModule":
        """Return module with the given parameters.

        :param name: module name
        :param rev: optional revision
        """
        rlist = self.modules[name]
        for m in rlist:
            if rev == m.revision: return m
        if rev is None: return rlist[0]
        
class Terminal(SchemaNode):
    """Abstract superclass for leaves in the schema tree."""
    pass

class Container(Internal):
    """Container node."""
    pass

class Leaf(Terminal):
    """Leaf node."""
    pass

class ConformanceType(Enum):
    implemented = 0
    imported = 1

    def __str__(self):
        """Return string representation of the receiver."""
        return "import" if self.value else "implement"

class Module(object):
    """Class for data common to both modules and submodules."""

    module_dir = "/usr/local/share/yang"
    """Local filesystem directory from which YANG modules can be retrieved."""

    def __init__(self,
                 name: YangIdentifier,
                 revision: str,
                 schema: Optional[Uri]) -> None:
        """Initialize the instance.

        :param name: module name
        :param revision: revision date or ``""`` (= revision not specified)
        :param schema: URL from which the module can be retrieved
        """
        self.name = name
        self.revision = revision if revision else None
        self.url = schema
        self.content = None # type: Optional[Statement]
        self.prefix_map = {} # type: Dict[YangIdentifier, ModuleId]

    def basename(self) -> str:
        """Canonical base name of the module file."""
        if self.revision:
            return self.name + "@" + self.revision
        else:
            return self.name

    def _to_dict(self) -> Dict[str, str]:
        """Convert receiver's data to a dictionary."""
        res = { "name": name,
                "revision": self.revision if self.revision else "" }
        if self.url:
            res["schema"] = self.url
        return res

    def _load(self) -> None:
        """Load the module content."""
        fn = "{}/{}.yang".format(self.module_dir, self.basename())
        self.content = from_file(fn)

    def _resolve_imports(self, root: SchemaRoot) -> None:
        """Assign `ModuleId` to each prefix used in the receiver.

        :param root: schema root (with module dictionary)
        :raises UnresolvableImport: if the receiver doesn't contain the module
        """
        for imp in self.content.find_all("import"):
            name = imp.argument
            prefix = imp.find1("prefix", required=True).argument
            revst = imp.find1("revision-date")
            rev = revst.argument if revst else None
            modid = root.get_module_revision(name, rev)
            if modid:
                self.prefix_map[prefix] = modid
            else:
                raise UnresolvableImport(name, rev)

class MainModule(Module):
    """Main module data."""

    def __init__(self,
                 name: YangIdentifier,
                 revision: str,
                 ct: str,
                 namespace: Uri,
                 feature: List[YangIdentifier] = [],
                 submodules: Dict[str, List[Module]] = {"submodule": []},
                 deviation: List[ModuleId] = [],
                 schema: Optional[Uri] = None) -> None:
        """Initialize the instance.

        :param name: module name
        :param revision: revision date or ``""`` (= revision not specified)
        :param ct: conformance type string ("implement" or "import")
        :param namespace: module namespace URI
        :param feature: supported features
        :param submodules: object containing a list of submodules
        :param deviation: list of deviation modules
        :param schema: URL from which the module is available
        """
        super().__init__(name, revision, schema)
        self.namespace = namespace
        self.feature = feature
        self.deviation = [ (d["name"], d["revision"] if d["revision"] else None)
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

    def normalize_path(self, sni: str) -> SchemaNodeId:
        """Normalize the schema node identifier to JSON format.

        :param sni: schema node identifier in YANG format (with prefixes)
        """
        mod = None
        res = []
        for n in sni.split("/"):
            (p, s, loc) = n.partition(":")
            if s:
                nmod = self.prefix_map[p].name
            else:
                nmod = self.name
                loc = n
            res.append(loc if nmod == mod else nmod + ":" + loc)
            mod = nmod
        return "/".join(res)

    def _to_dict(self, name: YangIdentifier,
                 rev: RevisionDate) -> Dict[str, str]:
        """Convert the receiver to a dictionary.

        :param name: module name
        :param rev: revision date
        """
        res = super()._to_dict()
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

    def _load(self) -> None:
        """Load the content of the module and all its submodules."""
        super()._load()
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
