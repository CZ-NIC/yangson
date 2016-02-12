import json
from json.decoder import JSONDecodeError
from typing import Dict, List, Optional
from yangson.exception import YangsonException
from .typealiases import *
from .statement import Statement
import yangson.components as yc

class Schema(object):
    """YANG schema."""

    @classmethod
    def from_yang_library(cls, txt: str) -> "YangLibrary":
        """Return an instance initialized from JSON text.

        :param txt: YANG Library information as JSON text
        :raises BadYangLibraryData: if `txt` is broken
        """
        modules = {}
        try:
            yl = json.loads(txt)
            for item in yl["ietf-yang-library:modules-state"]["module"]:
                ctstr = item.pop("conformance-type")
                m = yc.MainModule(ct=ctstr, **item)
                modules.setdefault(m.name, []).append(m)
        except (JSONDecodeError, KeyError, AttributeError):
            raise BadYangLibraryData()
        return cls(modules)

    def __init__(self, modules: yc.ModuleDict) -> None:
        """Initialize the instance.

        :param modules: dictionary of modules comprising the schema
        """
        self.root = yc.SchemaRoot(modules)

    def write_yang_library(self) -> str:
        """Serialize YANG Library information in JSON format.
        """
        modules = self.root.modules
        val = [ modules[k]._to_dict() for k in modules ]
        return json.dumps(val)

    def build(self) -> None:
        """Find and fill in all missing data."""
        self.load_modules()
        self.resolve_imports()

    def load_modules(self) -> None:
        """Load contents of all YANG modules."""
        mods = self.root.modules
        for m in mods:
            for modrev in mods[m]:
                modrev._load()

    def resolve_imports(self):
        """Assign modules & revisions to prefixes."""
        mods = self.root.modules
        for m in mods:
            for modrev in mods[m]:
                modrev._resolve_imports(self.root)

    def handle_substatements(self, stmt: Statement,
                             parent: yc.SchemaNode,
                             ns: YangIdentifier,
                             path: SchemaNodeId) -> None:
        """Dispatch actions for all substatements of `stmt`.

        :param stmt: parsed YANG statement 
        """
        for s in stmt.substatements:
            key = (s.prefix, s.keyword) if s.prefix else s.keyword
            mname = self.handler.get(key, key)
            method = getattr(self, mname, self.noop)
            method(s, parent, ns, path)

    def noop(self, stmt: Statement, parent: yc.SchemaNode,
             ns: YangIdentifier, path: SchemaNodeId) -> None:
        """Do nothing."""
        pass

    def container(self, stmt: Statement, parent: yc.SchemaNode,
                  ns: YangIdentifier, path: SchemaNodeId) -> None:
        """Handle container statement."""
        name = stmt.argument
        cont = yc.Container()
        parent.add_child(name, cont)
        self.handle_substatements(stmt, cont, ns, path + "/" + name)

    def leaf(self, stmt: Statement, parent: yc.SchemaNode,
             ns: YangIdentifier, path: SchemaNodeId) -> None:
        """Handle leaf statement."""
        name = stmt.argument
        leaf = yc.Leaf()
        parent.add_child(stmt.argument, leaf)
        self.handle_substatements(stmt, leaf, ns, path + "/" + name)

    handler = {
        }
    """Map of statement keywords to corresponding handler methods."""    

class BadYangLibraryData(YangsonException):
    """Exception to be raised for broken YANG Library data."""

    def __init__(self, reason: str = "broken yang-library data") -> None:
        self.reason = reason

    def __str__(self) -> str:
        return self.reason
