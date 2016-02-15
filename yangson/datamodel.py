import json
from typing import Dict, List, Optional
from .enumerations import DefaultDeny
from .exception import YangsonException
from .modparser import from_file
from .statement import Statement
from .typealiases import *

ModuleDict = Dict[ModuleId, Statement]
OptChangeSet = Optional["ChangeSet"]

class ChangeSet(object):
    """Set of changes to be applied to a node and its children."""

    @classmethod
    def from_statement(cls, stmt: Statement) -> "ChangeSet":
        """Construct an instance from a statement.

        :param stmt: YANG statement (``refine`` or ``uses-augment``)
        """
        path = stmt.argument.split("/")
        cs = cls([stmt])
        while path:
            last = path.pop()
            cs = cls(subset={last: cs})
        return cs

    def __init__(self, patch: List[Statement] = [],
                 subset: Dict[NodeName, "ChangeSet"] = {}) -> None:
        self.patch = patch
        self.subset = subset

    def get_subset(self, name: NodeName) -> OptChangeSet:
        return self.subset.get(name)

    def join(self, cs: "ChangeSet") -> "ChangeSet":
        """Join the receiver with another change set.

        :param cs: change set
        """
        res = ChangeSet(self.patch + cs.patch, self.subset.copy())
        for n in cs.subset:
            if n in self.subset:
                res.subset[n] = self.subset[n].join(cs.subset[n])
            else:
                res.subset[n] = cs.subset[n]
        return res

class DataModel(object):
    """YANG data model."""

    module_dir = "/usr/local/share/yang" # type: str
    """Local filesystem directory from which YANG modules can be retrieved."""

    _modules = {} # type: ModuleDict
    """Dictionary of parsed modules comprising the data model."""

    _groupings = {} # type: Dict[ModuleId, Dict[YangIdentifier, Statement]]
    """Dictionary of all global groupings."""
    
    _prefix_map = {} # type: Dict[ModuleId, Dict[YangIdentifier, ModuleId]]
    """Dictionary mapping of prefix assignments in all modules.""" 
    
    @classmethod
    def from_yang_library(cls, txt: str) -> "DataModel":
        """Return an instance initialized from JSON text.

        :param txt: YANG Library information as JSON text
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
                cls.load_module(name, rev)
                if "submodules" in item and "submodule" in item["submodules"]:
                    for s in item["submodules"]["submodule"]:
                        rev = s["revision"] if s["revision"] else None
                        cls.load_module(s["name"], rev)
        except (json.JSONDecodeError, KeyError, AttributeError):
            raise BadYangLibraryData()
        res = cls(revisions, implement)
        res._build_schema()
        return res

    @classmethod
    def load_module(cls, name: YangIdentifier, rev: RevisionDate) -> None:
        """Read, parse and register YANG module or submodule.

        :param name: module or submodule name
        :param rev: revision date or `None`
        """
        fn = "{}/{}".format(cls.module_dir, name)
        if rev: fn += "@" + rev
        cls._modules[(name, rev)] = from_file(fn + ".yang")

    @classmethod
    def translate_qname(cls, mid: ModuleId, qname: QName) -> QName:
        """Translate prefix-based QName to (namespace, locname) tuple.

        :param mid: identifier of the context module
        :param qname: qualified name in prefix form
        """
        (p, s, loc) = qname.partition(":")
        return ((cls._prefix_map[mid][p][0], loc) if s else (mid[0], p))

    @classmethod
    def schema_path(cls, mid: ModuleId, sid: str) -> List[QName]:
        """Construct schema path from schema node identifier.

        :param mid: identifier of the context module
        :param sid: schema node identifier (absolute or relative)
        """
        nlist = sid.split("/")
        oldpref = None
        res = []
        for qn in (nlist[1:] if sid[0] == "/" else nlist):
            pref, loc = cls.translate_qname(mid, qn)
            res.append(loc if pref == oldpref else pref + ":" + loc)
            oldpref = pref
        return res

    @classmethod
    def register_groupings(cls, mid: ModuleId, stmt: Statement) -> None:
        """Register recuresively all groupings defined under `stmt`.

        :param mid: module context
        :param stmt: parsed YANG statement
        """
        for g in stmt.find_all("grouping"):
            cls._groupings.setdefault(mid, {})[g.argument] = g
        for s in stmt.substatements:
            cls.register_groupings(mid, s)

    def __init__(self,
                 revisions: Dict[YangIdentifier, List[RevisionDate]],
                 implement: List[ModuleId]) -> None:
        """Initialize the instance.

        :param revisions: dictionary mapping module name to all its revisions
        :param implement: list of implemented modules
        """
        self.revisions = revisions
        self.implement = implement
        self.schema = Internal() # type: Internal

    def _build_schema(self) -> None:
        """Build the schema."""
        self.setup_context()
        for mid in self.implement:
            self.schema.handle_substatements(DataModel._modules[mid], mid, None)
        self.apply_augments()

    def setup_context(self) -> None:
        """Set up context for schema construction."""
        mods = DataModel._modules
        for mid in mods:
            mod = mods[mid]
            DataModel.register_groupings(mid, mod)
            locpref = mod.find1("prefix", required=True).argument
            DataModel._prefix_map[mid] = pmap = { locpref: mid }
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

    def get_schema_node(self, asid: str) -> Optional["SchemaNode"]:
        """Return schema node addressed by `asid`.

        :param asid: absolute schema node identifier
        """
        return self.schema.get_descendant(asid.split("/")[1:])

    def apply_augments(self) -> None:
        """Apply top-level augments from all implemented modules."""
        for mid in self.implement:
            mod = DataModel._modules[mid]
            for aug in mod.find_all("augment"):
                path = DataModel.schema_path(mid, aug.argument)
                target = self.schema.get_descendant(path)
                target.handle_substatements(aug, mid, None)

class SchemaNode(object):
    """Abstract superclass for schema nodes."""

    def __init__(self) -> None:
        """Initialize the instance:"""

        self.parent = None # type: "Internal"
        self._namespace = None # type: YangIdentifier
        self.default_deny = DefaultDeny.none
        
    def noop(self, stmt: Statement, mid: ModuleId,
             changes: OptChangeSet) -> None:
        """Do nothing."""
        pass

    def get_descendant(self, path: List[NodeName]) -> Optional["SchemaNode"]:
        """Return descendant schema node.
        
        :param path: relative path to the descendant node
        """
        node = self
        try:
            for n in path:
                node = node.children[n]
        except KeyError:
            return None
        return node

    def handle_substatements(self, stmt: Statement,
                             mid: ModuleId,
                             changes: Optional[ChangeSet]) -> None:
        """Dispatch actions for all substatements of `stmt`.

        :param stmt: parsed YANG statement
        :param mid: module context
        :param changes: change set
        """
        for s in stmt.substatements:
            if s.prefix:
                key = DataModel._prefix_map[mid][s.prefix][0] + s.keyword
            else:
                key = s.keyword
            mname = SchemaNode.handler.get(key, key)
            method = getattr(self, mname, self.noop)
            method(s, mid, changes)

    def nacm_default_deny(self, stmt: Statement,
                          mid: ModuleId,
                          changes: Optional[ChangeSet]) -> None:
        """Set NACM default access."""
        if stmt.keyword == "default-deny-all":
            self.default_deny = DefaultDeny.all
        elif stmt.keyword == "default-deny-write":
            self.default_deny = DefaultDeny.write

    handler = {
        "ietf-netconf-acm:default-deny-all": "nacm_default_deny",
        "ietf-netconf-acm:default-deny-write": "nacm_default_deny",
        "leaf-list": "leaf_list",
        }
    """Map of statement keywords to names of handler methods."""    


class Internal(SchemaNode):
    """Abstract superclass for schema nodes that have children."""

    def __init__(self) -> None:
        """Initialize the instance."""
        super().__init__()
        self.children = {} # type: Dict[YangIdentifier, SchemaNode]

    def add_child(self, node: SchemaNode, name: NodeName) -> None:
        """Add child node to the receiver.

        :param node: child node
        :param name: node name (local or qualified)
        """
        node.parent = self
        self.children[name] = node

    def handle_child(self, node: SchemaNode, stmt: Statement,
                     mid: ModuleId, changes: OptChangeSet) -> None:
        """Add child node to the receiver and handle substatements.

        :param node: child node
        :param stmt: YANG statement defining the child node
        :param mid: module context
        :param changes: change set
        """
        node._namespace = mid[0]
        if self._namespace == node._namespace:
            name = stmt.argument
        else:
            name = node._namespace + ":" + stmt.argument
        self.add_child(node, name)
        node.handle_substatements(stmt, mid,
                                  changes.get_subset(name) if changes else None)

    def uses(self, stmt: Statement,
             mid: ModuleId, changes: OptChangeSet) -> None:
        """Handle uses statement.

        :raises GroupingNotFound: if the corresponding grouping doesn't exist
        """
        p, s, loc = stmt.argument.partition(":")
        if s:
            gid = DataModel._prefix_map[mid][p]
            gname = loc
        else:
            gid = mid
            gname = p
        try:
            grp = DataModel._groupings[gid][gname]
        except KeyError:
            raise GroupingNotFound(gid, gname)
        self.handle_substatements(grp, mid, changes)

    def container(self, stmt: Statement,
                  mid: ModuleId, changes: OptChangeSet) -> None:
        """Handle container statement."""
        self.handle_child(Container(), stmt, mid, changes)

    def list(self, stmt: Statement,
             mid: ModuleId, changes: OptChangeSet) -> None:
        """Handle container statement."""
        self.handle_child(List(), stmt, mid, changes)

    def choice(self, stmt: Statement,
               mid: ModuleId, changes: OptChangeSet) -> None:
        """Handle choice statement."""
        self.handle_child(Choice(), stmt, mid, changes)

    def case(self, stmt: Statement,
             mid: ModuleId, changes: OptChangeSet) -> None:
        """Handle case statement."""
        self.handle_child(Case(), stmt, mid, changes)

    def leaf(self, stmt: Statement,
             mid: ModuleId, changes: OptChangeSet) -> None:
        """Handle leaf statement."""
        self.handle_child(Leaf(), stmt, mid, changes)

    def leaf_list(self, stmt: Statement,
                  mid: ModuleId, changes: OptChangeSet) -> None:
        """Handle leaf-list statement."""
        self.handle_child(LeafList(), stmt, mid, changes)

    def anydata(self, stmt: Statement,
             mid: ModuleId, changes: OptChangeSet) -> None:
        """Handle anydata statement."""
        self.handle_child(Leaf(), stmt, mid, changes)

    def anyxml(self, stmt: Statement,
             mid: ModuleId, changes: OptChangeSet) -> None:
        """Handle anyxml statement."""
        self.handle_child(Leaf(), stmt, mid, changes)

class Terminal(SchemaNode):
    """Abstract superclass for leaves in the schema tree."""
    pass

class Container(Internal):
    """Container node."""
    pass

class List(Internal):
    """List node."""
    pass

class Choice(Internal):
    """Choice node."""

    def handle_child(self, node: SchemaNode, stmt: SchemaNode,
                     mid: ModuleId, changes: OptChangeSet) -> None:
        """Handle a child node to be added to the receiver.

        :param node: child node
        :param stmt: YANG statement defining the child node
        :param mid: module context
        :param changes: change set
        """
        if isinstance(node, Case):
            super().handle_child(node, stmt, mid, changes)
        else:
            cn = Case()
            cn._namespace = mid[0]
            if self._namespace == cn._namespace:
                name = stmt.argument
            else:
                name = cn._namespace + ":" + stmt.argument
            self.add_child(cn, name)
            cn.handle_child(node, stmt, mid,
                            changes.get_subset(name) if changes else None)

class Case(Internal):
    """Case node."""
    pass

class Leaf(Terminal):
    """Leaf node."""
    pass

class LeafList(Terminal):
    """Leaf-list node."""
    pass

class Anydata(Terminal):
    """Leaf-list node."""
    pass

class Anyxml(Terminal):
    """Leaf-list node."""
    pass

class UnresolvableImport(YangsonException):
    """Exception to be raised if an imported module isn't found."""

    def __init__(self, name: YangIdentifier, rev: RevisionDate) -> None:
        self.name = name
        self.revision = rev

    def __str__(self) -> str:
        return Module.basename(self.name, self.revision)

class BadYangLibraryData(YangsonException):
    """Exception to be raised for broken YANG Library data."""

    def __init__(self, reason: str = "broken yang-library data") -> None:
        self.reason = reason

    def __str__(self) -> str:
        return self.reason

class GroupingNotFound(YangsonException):
    """Exception to be raised when a used grouping doesn't exist."""

    def __init__(self, mid: ModuleId, gname: YangIdentifier) -> None:
        self.gname = gname
        self.mid = mid

    def __str__(self) -> str:
        return "grouping {} not found in {}".format(self.gname, self.mid[0])
