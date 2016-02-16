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
    def translate_qname(cls, mid: ModuleId, qname: QName) -> NodeName:
        """Translate prefix-based QName to absolute node name.

        :param mid: identifier of the context module
        :param qname: qualified name in prefix form
        """
        (p, s, loc) = qname.partition(":")
        return ((cls._prefix_map[mid][p][0], loc) if s else (mid[0], p))

    @classmethod
    def sid2address(cls, mid: ModuleId, sid: str) -> SchemaAddress:
        """Construct schema address from a schema node identifier.

        :param mid: identifier of the context module
        :param sid: schema node identifier (absolute or relative)
        """
        nlist = sid.split("/")
        return [ cls.translate_qname(mid, qn)
                 for qn in (nlist[1:] if sid[0] == "/" else nlist) ]

    @classmethod
    def path2address(cls, path: str) -> SchemaAddress:
        """Translate path to schema address.

        :param path: schema or data path
        """
        nlist = path.split("/")
        prevns = None
        res = []
        for n in (nlist[1:] if path[0] == "/" else nlist):
            p, s, loc = n.partition(":")
            if s:
                if p == prevns: raise BadPath(path)
                res.append((p, loc))
                prevns = p
            elif prevns:
                res.append((prevns, p))
            else:
                raise BadPath(path)
        return res

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
        self.schema._nsswitch = True

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

    def get_schema_node(self, path: str) -> Optional["SchemaNode"]:
        """Return a schema node.

        :param path: schema node path
        """
        return self.schema.get_schema_descendant(self.path2address(path))

    def get_data_node(self, path: str) -> Optional["DataNode"]:
        """Return a data node.

        :param path: data node path
        """
        addr = self.path2address(path)
        node = self.schema
        for ns, name in addr:
            node = node.get_data_child(name, ns)
            if node is None: return None
        return node

    def apply_augments(self) -> None:
        """Apply top-level augments from all implemented modules."""
        for mid in self.implement:
            mod = DataModel._modules[mid]
            for aug in mod.find_all("augment"):
                path = DataModel.sid2address(mid, aug.argument)
                target = self.schema.get_schema_descendant(path)
                target._nsswitch = True
                target.handle_substatements(aug, mid, None)

class SchemaNode(object):
    """Abstract superclass for schema nodes."""

    def __init__(self, name: Optional[YangIdentifier],
                 ns: Optional[YangIdentifier]) -> None:
        """Initialize the instance."""

        self.name = name
        self.ns = ns
        self.parent = None # type: Optional["Internal"]
        self.default_deny = DefaultDeny.none # type: "DefaultDeny"
        
    def noop(self, stmt: Statement, mid: ModuleId,
             changes: OptChangeSet) -> None:
        """Do nothing."""
        pass

    def handle_substatements(self, stmt: Statement,
                             mid: ModuleId,
                             changes: Optional[ChangeSet]) -> None:
        """Dispatch actions for all substatements of `stmt`.

        :param stmt: parsed YANG statement
        :param mid: YANG module context
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

    def __init__(self, name: Optional[YangIdentifier] = None,
                 ns: Optional[YangIdentifier] = None) -> None:
        """Initialize the instance."""
        super().__init__(name, ns)
        self.children = [] # type: List[SchemaNode]
        self._nsswitch = False # type: bool

    def add_child(self, node: SchemaNode) -> None:
        """Add child node to the receiver.

        :param node: child node
        """
        node.parent = self
        self.children.append(node)

    def get_child(self, name: YangIdentifier,
                  ns: Optional[YangIdentifier] = None):
        """Return receiver's child.
        :param name: child's name
        :param ns: child's namespace (= `self.ns` if absent)
        """
        ns = ns if ns else self.ns
        for c in self.children:
            if c.name == name and c.ns == ns: return c

    def get_schema_descendant(self,
                              path: SchemaAddress) -> Optional["SchemaNode"]:
        """Return descendant schema node or ``None``.

        :param path: schema address of the descendant node
        """
        node = self
        for ns, name in path:
            node = node.get_child(name, ns)
            if node is None: return None
        return node

    def get_data_child(self, name: YangIdentifier,
                      ns: Optional[YangIdentifier] = None) -> Optional["DataNode"]:
        """Return data node directly under receiver.

        :param name: data node name
        :param ns: data node namespace (= `self.ns` if absent)
        """
        ns = ns if ns else self.ns
        cands = []
        for c in self.children:
            if c.name ==name and c.ns == ns:
                if isinstance(c, DataNode):
                    return c
                cands.insert(0,c)
            elif isinstance(c, (Choice, Case)):
                cands.append(c)
        if cands:
            for c in cands:
                res = c.get_data_child(name, ns)
                if res: return res

    def handle_child(self, node: SchemaNode, stmt: Statement,
                     mid: ModuleId, changes: OptChangeSet) -> None:
        """Add child node to the receiver and handle substatements.

        :param node: child node
        :param stmt: YANG statement defining the child node
        :param mid: module context
        :param changes: change set
        """
        node.name = stmt.argument
        node.ns = mid[0] if self._nsswitch else self.ns
        self.add_child(node)
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
            if gid == mid:
                grp = stmt.get_grouping(loc)
            else:
                grp = DataModel._modules[gid].find1("grouping", loc,
                                                    required=True)
        else:
            gid = mid
            grp = stmt.get_grouping(p)
        self.handle_substatements(grp, gid, changes)

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

class DataNode(object):
    """Abstract superclass for data nodes."""
    pass

class Terminal(SchemaNode, DataNode):
    """Abstract superclass for leaves in the schema tree."""

    def __init__(self, name: Optional[YangIdentifier] = None,
                 ns: Optional[YangIdentifier] = None) -> None:
        """Initialize the instance."""
        SchemaNode.__init__(self, name, ns)

class Container(Internal, DataNode):
    """Container node."""
    pass

class List(Internal, DataNode):
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
            cn = Case(stmt.argument, mid[0])
            self.add_child(cn)
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

class BadPath(YangsonException):
    """Exception to be raised for invalid schema or data path."""

    def __init__(self, path: str) -> None:
        self.path = path

    def __str__(self) -> str:
        return self.path
