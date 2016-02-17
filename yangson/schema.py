"""Classes for schema nodes."""

from typing import Dict, List, Optional
from .context import Context
from .enumerations import DefaultDeny
from .exception import YangsonException
from .statement import Statement
from .typealiases import *

# Type aliases
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

class SchemaNode(object):
    """Abstract superclass for schema nodes."""

    def __init__(self, name: Optional[YangIdentifier],
                 ns: Optional[YangIdentifier]) -> None:
        """Initialize the instance."""

        self.name = name
        self.ns = ns
        self.parent = None # type: Optional["Internal"]
        self.default_deny = DefaultDeny.none # type: "DefaultDeny"

    def is_config(self) -> bool:
        """Is the receiver configuration?"""
        try:
            return getattr(self, "_config")
        except AttributeError:
            return self.parent.is_config()

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
                key = Context.prefix_map[mid][s.prefix][0] + ":" + s.keyword
            else:
                key = s.keyword
            mname = SchemaNode.handler.get(key, key)
            method = getattr(self, mname, self.noop)
            method(s, mid, changes)

    def noop(self, stmt: Statement, mid: ModuleId,
             changes: OptChangeSet) -> None:
        """Do nothing."""
        pass

    def config(self, stmt: Statement,
               mid: ModuleId,
               changes: Optional[ChangeSet]) -> None:
        if stmt.argument == "false": self._config = False

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
            gid = Context.prefix_map[mid][p]
            if gid == mid:
                grp = stmt.get_grouping(loc)
            else:
                grp = Context.modules[gid].find1("grouping", loc,
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
