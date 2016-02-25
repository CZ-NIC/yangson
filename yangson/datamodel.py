import json
from typing import Dict, List, Optional
from .context import Context
from .exception import YangsonException
from .instance import InstanceIdentifier, MemberName
from .modparser import from_file
from .schema import Internal, NonexistentSchemaNode
from .typealiases import *
from .regex import *

class DataModel(object):
    """YANG data model."""

    @classmethod
    def from_yang_library(cls, txt: str,
                          mod_dir: str = ".") -> "DataModel":
        """Return an instance initialized from JSON text.

        :param txt: YANG Library information as JSON text
        :param mod_dir: local filesystem directory from which YANG modules
            can be retrieved (current directory is the default).
        :raises BadYangLibraryData: if `txt` is broken
        """
        revisions = {}
        implement = []
        try:
            yl = json.loads(txt)
            for item in yl["ietf-yang-library:modules-state"]["module"]:
                name = item["name"]
                rev = item["revision"] if item["revision"] else None
                mid = (name, rev)
                ct = item["conformance-type"]
                if ct == "implement": implement.append(mid)
                revisions.setdefault(name, []).append(rev)
                cls.load_module(name, rev, mod_dir)
                if "submodules" in item and "submodule" in item["submodules"]:
                    for s in item["submodules"]["submodule"]:
                        rev = s["revision"] if s["revision"] else None
                        cls.load_module(s["name"], rev, mod_dir)
        except (json.JSONDecodeError, KeyError, AttributeError):
            raise BadYangLibraryData()
        res = cls(revisions, implement)
        res._build_schema()
        return res

    @classmethod
    def load_module(cls, name: YangIdentifier, rev: RevisionDate,
                    mod_dir: str = ".") -> None:
        """Read, parse and register YANG module or submodule.

        :param name: module or submodule name
        :param rev: revision date or `None`
        :param mod_dir: local filesystem directory from the module
            can be retrieved (current directory is the default).
        """
        fn = "{}/{}".format(mod_dir, name)
        if rev: fn += "@" + rev
        Context.modules[(name, rev)] = from_file(fn + ".yang")

    def __init__(self,
                 revisions: Dict[YangIdentifier, List[RevisionDate]],
                 implement: List[ModuleId]) -> None:
        """Initialize the class instance.

        :param revisions: dictionary mapping module name to all its revisions
        :param implement: list of implemented modules
        """
        self.revisions = revisions
        self.implement = implement
        self.schema = Internal() # type: Internal
        self.schema._nsswitch = self.schema._config = True

    def _build_schema(self) -> None:
        """Build the schema."""
        self.setup_context()
        for mid in self.implement:
            self.schema.handle_substatements(Context.modules[mid], mid, None)
        self.apply_augments()

    def setup_context(self) -> None:
        """Set up context for schema construction."""
        mods = Context.modules
        for mid in mods:
            mod = mods[mid]
            locpref = mod.find1("prefix", required=True).argument
            Context.prefix_map[mid] = pmap = { locpref: mid }
            try:
                pos = self.implement.index(mid)
            except ValueError:            # mod not implemented
                pos = None
            for imp in mod.find_all("import"):
                iname = imp.argument
                prefix = imp.find1("prefix", required=True).argument
                revst = imp.find1("revision-date")
                rev = revst.argument if revst else None
                imid = None
                for r in self.revisions[iname]:
                    if r == rev:
                        imid = (iname, rev)
                        break
                if imid is None and rev is None:   # use last revision in the list
                    imid = (iname, self.revisions[iname][-1])
                pmap[prefix] = imid
                if pos is None: return
                i = pos
                while i < len(self.implement):
                    if self.implement[i] == imid:
                        self.implement[pos] = imid
                        self.implement[i] = mid
                        pos = i
                        break
                    i += 1

    def get_schema_node(self, path: str) -> Optional["SchemaNode"]:
        """Return a schema node.

        :param path: schema node path
        """
        return self.schema.get_schema_descendant(Context.path2address(path))

    def get_data_node(self, path: str) -> Optional["DataNode"]:
        """Return a data node.

        :param path: data node path
        """
        addr = Context.path2address(path)
        node = self.schema
        for ns, name in addr:
            node = node.get_data_child(name, ns)
            if node is None: return None
        return node

    def apply_augments(self) -> None:
        """Apply top-level augments from all implemented modules."""
        for mid in self.implement:
            mod = Context.modules[mid]
            for aug in mod.find_all("augment"):
                path = Context.sid2address(mid, aug.argument)
                target = self.schema.get_schema_descendant(path)
                target._nsswitch = True
                target.handle_substatements(aug, mid, None)

    def parse_instance_id(self, iid: str) -> InstanceIdentifier:
        """Parse instance identifier."""
        end = len(iid)
        offset = 0
        res = InstanceIdentifier()
        sn = self.schema
        while True:
            if iid[offset] != "/":
                raise BadInstanceIdentifier(iid)
            mo = qname_re.match(iid, offset+1)
            if mo is None:
                raise BadInstanceIdentifier(iid)
            ns = mo.group("prf")
            name = mo.group("loc")
            sn = sn.get_data_child(name, ns)
            if sn is None:
                raise NonexistentSchemaNode(name, ns)
            res.append(MemberName(sn.qname))
            offset = mo.end()
            if offset < end and iid[offset] != "/":
                sel, offset = sn._parse_entry_selector(iid, offset)
                res.append(sel)
            if offset >= end: return res

class BadYangLibraryData(YangsonException):
    """Exception to be raised for broken YANG Library data."""

    def __init__(self, reason: str = "broken yang-library data") -> None:
        self.reason = reason

    def __str__(self) -> str:
        return self.reason

class BadInstanceIdentifier(YangsonException):
    """Exception to be raised for malformed instance identifier."""

    def __init__(self, iid: str) -> None:
        self.iid = iid

    def __str__(self) -> str:
        return self.iid
