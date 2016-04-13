import json
from typing import Dict, List, Optional
from urllib.parse import unquote
from .constants import qname_re, YangsonException
from .context import Context
from .instance import (Crumb, EntryKeys, Instance, InstanceIdentifier,
                       MemberName)
from .modparser import from_file
from .schema import (BadSchemaNodeType, InternalNode, NonexistentSchemaNode,
                     RawObject)
from .statement import Statement
from .typealiases import *

class DataModel:
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
                Context.ns_map[name] = name
                if "feature" in item:
                    Context.features.update(
                        [ name + ":" + f for f in item["feature"] ])
                rev = item["revision"] if item["revision"] else None
                mid = (name, rev)
                ct = item["conformance-type"]
                if ct == "implement": implement.append(mid)
                revisions.setdefault(name, []).append(rev)
                mod = cls.load_module(name, rev, mod_dir)
                locpref = mod.find1("prefix", required=True).argument
                Context.prefix_map[mid] = { locpref: mid }
                if "submodules" in item and "submodule" in item["submodules"]:
                    for s in item["submodules"]["submodule"]:
                        sname = s["name"]
                        Context.ns_map[sname] = name
                        rev = s["revision"] if s["revision"] else None
                        smid = (sname, rev)
                        if ct == "implement": implement.append(smid)
                        revisions.setdefault(sname, []).append(rev)
                        submod = cls.load_module(sname, rev, mod_dir)
                        bt = submod.find1("belongs-to", name, required=True)
                        locpref = bt.find1("prefix", required=True).argument
                        Context.prefix_map[smid] = { locpref: mid }
        except (json.JSONDecodeError, KeyError, AttributeError):
            raise BadYangLibraryData()
        res = cls(revisions, implement)
        res._build_schema()
        return res

    @classmethod
    def load_module(cls, name: YangIdentifier, rev: RevisionDate,
                    mod_dir: str = ".") -> Statement:
        """Read, parse and register YANG module or submodule.

        :param name: module or submodule name
        :param rev: revision date or `None`
        :param mod_dir: local filesystem directory from the module
            can be retrieved (current directory is the default).
        """
        fn = "{}/{}".format(mod_dir, name)
        if rev: fn += "@" + rev
        Context.modules[(name, rev)] = res = from_file(fn + ".yang")
        return res

    def __init__(self,
                 revisions: Dict[YangIdentifier, List[RevisionDate]],
                 implement: List[ModuleId]) -> None:
        """Initialize the class instance.

        :param revisions: dictionary mapping module name to all its revisions
        :param implement: list of implemented modules
        """
        self.revisions = revisions
        self.implement = implement
        self.schema = InternalNode() # type: Internal
        self.schema._nsswitch = self.schema._config = True

    def from_raw(self, robj: RawObject) -> Instance:
        """Return an instance created from a raw object.

        :param robj: raw object
        """
        cooked = self.schema.from_raw(robj)
        return Instance(cooked, Crumb(None, cooked.last_modified))

    def _build_schema(self) -> None:
        """Build the schema."""
        self.setup_context()
        for mid in self.implement:
            self.schema.handle_substatements(Context.modules[mid], mid)
        self.apply_augments()

    def setup_context(self) -> None:
        """Set up context for schema construction."""
        mods = Context.modules
        for mid in mods:
            mod = mods[mid]
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
                if imid is None and rev is None:   # use last revision
                    imid = (iname, self.revisions[iname][-1])
                Context.prefix_map[mid][prefix] = imid
                if pos is None: continue
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
        for p in addr:
            node = node.get_data_child(*p)
            if node is None: return None
        return node

    def apply_augments(self) -> None:
        """Apply top-level augments from all implemented modules."""
        for mid in self.implement:
            mod = Context.modules[mid]
            for aug in mod.find_all("augment"):
                self.schema.augment_refine(aug, mid, True)

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

    def parse_resource_id(self, rid: str) -> InstanceIdentifier:
        """Parse RESTCONF data resource identifier.

        :param rid: data resource identifier
        """
        inp = rid[1:] if rid[0] == "/" else rid
        res = InstanceIdentifier()
        sn = self.schema
        for p in inp.split("/"):
            apiid, eq, keys = p.partition("=")
            mo = qname_re.match(unquote(apiid))
            if mo is None:
                raise BadInstanceIdentifier(rid)
            ns = mo.group("prf")
            name = mo.group("loc")
            sn = sn.get_data_child(name, ns)
            if sn is None:
                raise NonexistentSchemaNode(name, ns)
            res.append(MemberName(sn.qname))
            if eq:                        # list instance
                ks = keys.split(",")
                try:
                    if len(ks) != len(sn.keys):
                        raise BadInstanceIdentifier(rid)
                except AttributeError:
                    raise BadSchemaNodeType(sn, "list") from None
                sel = {}
                for i in range(len(ks)):
                    klf = sn.get_child(*sn.keys[i])
                    val = klf.type.parse_value(unquote(ks[i]))
                    sel[klf.qname] = val
                res.append(EntryKeys(sel))
        return res

    def ascii_data_tree(self) -> str:
        """Return ascii-art representation of the main data tree."""
        return self.schema.ascii_tree("")

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
