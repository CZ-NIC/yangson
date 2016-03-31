"""Classes for schema nodes."""

from typing import Dict, List, Optional, Tuple, Union
from .constants import DefaultDeny, pred_re, YangsonException
from .context import Context
from .datatype import DataType, RawScalar
from .instance import (ArrayValue, EntryIndex, EntryValue,
                       EntryKeys, InstanceIdentifier, MemberName,
                       ObjectValue, Value)
from .statement import Statement
from .typealiases import *

# Local type aliases
RawObject = Dict[QName, "RawValue"]
RawList = List["RawObject"]
RawLeafList = List["RawScalar"]
RawValue = Union[RawScalar, RawObject, RawList, RawLeafList]

class SchemaNode:
    """Abstract superclass for schema nodes."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        self.name = None # type: YangIdentifier
        self.ns = None # type: YangIdentifier
        self.parent = None # type: "InternalNode"

    @property
    def config(self) -> bool:
        """Is the receiver configuration?"""
        try:
            return self._config
        except AttributeError:
            return self.parent.config

    @property
    def qname(self) -> QName:
        """Return qualified name of the receiver."""
        return (self.name if self.ns == self.parent.ns
                else self.ns + ":" + self.name)

    @staticmethod
    def unqname(qn: QName) -> Tuple[YangIdentifier, Optional[YangIdentifier]]:
        """Translate qualified name to (name, namespace) tuple.

        :param qn: qualified name
        """
        p, s, loc = qn.partition(":")
        if s: return (loc, p)
        return (p, None)

    def handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        """Dispatch actions for substatements of `stmt`.

        :param stmt: parsed YANG statement
        :param mid: YANG module context
        """
        for s in stmt.substatements:
            if s.prefix:
                key = Context.prefix_map[mid][s.prefix][0] + ":" + s.keyword
            else:
                key = s.keyword
            mname = SchemaNode.handler.get(key, "noop")
            method = getattr(self, mname)
            method(s, mid)

    def noop(self, stmt: Statement, mid: ModuleId) -> None:
        """Do nothing."""
        pass

    def config_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        if stmt.argument == "false": self._config = False

    def mandatory_stmt(self, stmt, mid: ModuleId) -> None:
        if stmt.argument == "true":
            self.mandatory = True
            self.parent.mandatory_child()
        else:
            self.mandatory = False

    def _tree_line_prefix(self) -> str:
        return "+--"

    handler = {
        "anydata": "anydata_stmt",
        "anyxml": "anyxml_stmt",
        "case": "case_stmt",
        "choice": "choice_stmt",
        "config": "config_stmt",
        "container": "container_stmt",
        "default": "default_stmt",
        "ietf-netconf-acm:default-deny-all": "nacm_default_deny_stmt",
        "ietf-netconf-acm:default-deny-write": "nacm_default_deny_stmt",
        "leaf": "leaf_stmt",
        "leaf-list": "leaf_list_stmt",
        "list": "list_stmt",
        "mandatory": "mandatory_stmt",
        "max-elements": "max_elements_stmt",
        "min-elements": "min_elements_stmt",
        "presence": "presence_stmt",
        "uses": "uses_stmt",
        }
    """Map of statement keywords to names of handler methods."""


class InternalNode(SchemaNode):
    """Abstract superclass for schema nodes that have children."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.children = [] # type: List[SchemaNode]
        self._nsswitch = False # type: bool

    def mandatory_child(self) -> None:
        """A child of the receiver is mandatory; perform necessary actions."""
        pass

    def add_child(self, node: SchemaNode) -> None:
        """Add child node to the receiver.

        :param node: child node
        """
        node.parent = self
        self.children.append(node)

    def get_child(self, name: YangIdentifier,
                  ns: YangIdentifier = None) -> Optional["SchemaNode"]:
        """Return receiver's child.
        :param name: child's name
        :param ns: child's namespace (= `self.ns` if absent)
        """
        ns = ns if ns else self.ns
        for c in self.children:
            if c.name == name and c.ns == ns: return c

    def get_schema_descendant(
            self, path: SchemaAddress) -> Optional["SchemaNode"]:
        """Return descendant schema node or ``None``.

        :param path: schema address of the descendant node
        """
        node = self
        for p in path:
            node = node.get_child(*p)
            if node is None: return None
        return node

    def get_data_child(
            self, name: YangIdentifier,
            ns: YangIdentifier = None) -> Optional["DataNode"]:
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
            elif isinstance(c, (ChoiceNode, CaseNode)):
                cands.append(c)
        if cands:
            for c in cands:
                res = c.get_data_child(name, ns)
                if res: return res

    def get_data_descendant(
            self, ii: InstanceIdentifier) -> Optional["DataNode"]:
        """Return descendant data node.

        :param ii: instance identifier (relative to the receiver)
        """
        node = self
        for sel in ii:
            if not isinstance(sel, MemberName): continue
            node = node.get_child(*self.unqname(sel.name))
            if node is None: return None
        return node

    def handle_child(
            self, node: SchemaNode, stmt: Statement, mid: ModuleId) -> None:
        """Add child node to the receiver and handle substatements.

        :param node: child node
        :param stmt: YANG statement defining the child node
        :param mid: module context
        """
        node.name = stmt.argument
        node.ns = Context.ns_map[mid[0]] if self._nsswitch else self.ns
        self.add_child(node)
        node.handle_substatements(stmt, mid)

    def augment_refine(self, stmt: Statement, mid: ModuleId,
                       nsswitch: bool = False) -> None:
        path = Context.sid2address(mid, stmt.argument)
        target = self.get_schema_descendant(path)
        target._nsswitch = nsswitch
        target.handle_substatements(stmt, mid)

    def uses_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle uses statement."""
        grp, gid = Context.get_definition(stmt, mid)
        self.handle_substatements(grp, gid)
        for augref in stmt.find_all("augment") + stmt.find_all("refine"):
            self.augment_refine(augref, mid, False)

    def container_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle container statement."""
        self.handle_child(ContainerNode(), stmt, mid)

    def list_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle list statement."""
        node = ListNode()
        node.key_stmt(stmt, mid)
        self.handle_child(node, stmt, mid)

    def choice_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle choice statement."""
        self.handle_child(ChoiceNode(), stmt, mid)

    def case_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle case statement."""
        self.handle_child(CaseNode(), stmt, mid)

    def leaf_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle leaf statement."""
        node = LeafNode()
        node.type_stmt(stmt, mid)
        self.handle_child(node, stmt, mid)

    def leaf_list_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle leaf-list statement."""
        node = LeafListNode()
        node.type_stmt(stmt, mid)
        self.handle_child(node, stmt, mid)

    def anydata_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle anydata statement."""
        self.handle_child(AnydataNode(), stmt, mid)

    def anyxml_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle anyxml statement."""
        self.handle_child(AnyxmlNode(), stmt, mid)

    def from_raw(self, val: RawObject) -> ObjectValue:
        """Transform a raw dictionary into object value.

        :param val: raw dictionary
        """
        res = ObjectValue()
        for qn in val:
            cn = self.get_data_child(*self.unqname(qn))
            if cn is None:
                raise NonexistentSchemaNode(*self.unqname(qn))
            res[cn.qname] = cn.from_raw(val[qn])
        res.time_stamp()
        return res

    def ascii_tree(self, indent: str) -> str:
        """Return the receiver's ascii-art subtree."""
        res = ""
        if not self.children: return res
        for c in self.children[:-1]:
            res += indent + c.tree_line() + c.ascii_tree(indent + "|  ")
        return (res + indent + self.children[-1].tree_line() +
                self.children[-1].ascii_tree(indent + "   "))

class DataNode(SchemaNode):
    """Abstract superclass for data nodes."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self.default_deny = DefaultDeny.none # type: "DefaultDeny"

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + ("rw" if self.config else "ro")

    def _parse_entry_selector(self, iid: str, offset: int) -> Any:
        """This method is applicable only to a list or leaf-list."""
        raise BadSchemaNodeType(self, "list or leaf-list")

    @property
    def type(self):
        """This method is applicable only to a terminal node."""
        raise BadSchemaNodeType(self, "leaf or leaf-list")

    @type.setter
    def type(self, typ: DataType) -> None:
        """This method is applicable only to a terminal node."""
        raise BadSchemaNodeType(self, "leaf or leaf-list")

    def min_elements_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.min_elements = int(stmt.argument)
        if self.min_elements > 0:
            self.parent.mandatory_child()

    def max_elements_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        arg = stmt.argument
        if arg == "unbounded":
            self.max_elements = None
        else:
            self.max_elements = int(arg)

    def nacm_default_deny_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Set NACM default access."""
        if stmt.keyword == "default-deny-all":
            self.default_deny = DefaultDeny.all
        elif stmt.keyword == "default-deny-write":
            self.default_deny = DefaultDeny.write

class TerminalNode(DataNode):
    """Abstract superclass for leaves in the schema tree."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.default = None
        self.mandatory = False # type: bool
        self._type = None # type: DataType

    @property
    def type(self) -> Optional[DataType]:
        """Return receiver's type."""
        return self._type

    @type.setter
    def type(self, typ: DataType) -> None:
        """Set receiver's type."""
        self._type = typ

    def type_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Assign data type to the terminal node defined by `stmt`.

        :param stmt: YANG ``leaf`` or ``leaf-list`` statement
        :param mid: id of the context module
        """
        self.type = DataType.resolve_type(
            stmt.find1("type", required=True), mid)

    def from_raw(self, val: RawScalar) -> ScalarValue:
        """Transform a scalar entry.

        :param val: raw lis
        :param ns: current namespace
        """
        return self.type.from_raw(val)

    def ascii_tree(self, indent: str) -> str:
        """Return the receiver's ascii-art subtree."""
        return ""

class ContainerNode(InternalNode, DataNode):
    """Container node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.presence = False # type: bool
        self.mandatory = False # type: bool

    def mandatory_child(self) -> None:
        """A child of the receiver is mandatory; perform necessary actions."""
        if self.presence: return
        self.mandatory = True
        self.parent.mandatory_child()

    def presence_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.presence = True

    def tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        if self.presence:
            suff = "!"
        elif self.mandatory:
            suff = ""
        else:
            suff = "?"
        return "{} {}{}\n".format(
            self._tree_line_prefix(), self.qname, suff)

class ListNode(InternalNode, DataNode):
    """List node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.keys = [] # type: List[NodeName]
        self.min_elements = 0 # type: int
        self.max_elements = None # type: Optional[int]

    def key_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        kst = stmt.find1("key")
        if kst is None: return
        self.keys = [
            Context.translate_qname(mid, k) for k in kst.argument.split() ]

    def leaf_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle leaf statement."""
        node = LeafNode()
        node.type_stmt(stmt, mid)
        self.handle_child(node, stmt, mid)
        if (node.name, node.ns) in self.keys:
            node.mandatory = True

    def _parse_entry_selector(self, iid: str, offset: int) -> Tuple[
            Union[EntryIndex, EntryKeys], int]:
        """Parse selector for a list entry.

        :param iid: instance identifier string
        :param offset:
        """
        res = {}
        key_expr = False
        while offset < len(iid) and iid[offset] == "[":
            mo = pred_re.match(iid, offset)
            if mo is None:
                raise BadInstanceIdentifier(iid)
            pos = mo.group("pos")
            if pos:
                if key_expr:
                    raise BadEntrySelector(self, iid)
                return (EntryIndex(int(pos) - 1), mo.end())
            key_expr = True
            name = mo.group("loc")
            ns = mo.group("prf")
            kn = self.get_data_child(name, ns)
            if kn is None:
                raise NonexistentSchemaNode(name, ns)
            drhs = mo.group("drhs")
            val = kn.type.parse_value(drhs if drhs else mo.group("srhs"))
            res[kn.qname] = val
            offset = mo.end()
        if res:
            return (EntryKeys(res), mo.end())
        raise BadEntrySelector(self, iid)

    def from_raw(self, val: RawList) -> ArrayValue:
        """Transform a raw list array into array value.

        :param val: raw list array
        :param ns: current namespace
        """
        res = ArrayValue()
        for en in val:
            res.append(self.entry_from_raw(en))
        res.time_stamp()
        return res

    def entry_from_raw(self, val: RawValue) -> Value:
        """Transform a raw list entry into a value.

        :param val: raw list entry
        """
        return super().from_raw(val)

    def tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        keys = (" [" + " ".join([ k[0] for k in self.keys ]) + "]"
                if self.keys else "")
        return "{} {}*{}\n".format(
            self._tree_line_prefix(), self.qname, keys)

class ChoiceNode(InternalNode):
    """Choice node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.default = None # type: NodeName
        self.mandatory = False # type: bool

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + ("rw" if self.config else "ro")

    def handle_child(self, node: SchemaNode, stmt: SchemaNode,
                     mid: ModuleId) -> None:
        """Handle a child node to be added to the receiver.

        :param node: child node
        :param stmt: YANG statement defining the child node
        :param mid: module context
        """
        if isinstance(node, CaseNode):
            super().handle_child(node, stmt, mid)
        else:
            cn = CaseNode()
            cn.name = stmt.argument
            cn.ns = mid[0]
            self.add_child(cn)
            cn.handle_child(node, stmt, mid)

    def default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.default = Context.translate_qname(mid, stmt.argument)

    def tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} ({}){}\n".format(
            self._tree_line_prefix(), self.qname,
            "" if self.mandatory else "?")

class CaseNode(InternalNode):
    """Case node."""

    def tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{}:({})\n".format(
            self._tree_line_prefix(), self.qname)

class LeafNode(TerminalNode):
    """Leaf node."""

    def default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.default = self.type.parse_value(stmt.argument)

    def tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}{}\n".format(
            self._tree_line_prefix(), self.qname,
            "" if self.mandatory else "?")

class LeafListNode(TerminalNode):
    """Leaf-list node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.min_elements = 0 # type: int
        self.max_elements = None # type: Optional[int]

    def default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        if self.default is None:
            self.default = []
        self.default.append(self.type.parse_value(stmt.argument))

    def _parse_entry_selector(self, iid: str, offset: int) -> Tuple[
            Union[EntryIndex, EntryValue], int]:
        """Parse selector for a leaf-list entry.

        :param iid: instance identifier string
        :param offset:
        """
        if iid[offset] != "[":
            raise BadEntrySelector(self, iid)
        mo = pred_re.match(iid, offset)
        if mo is None:
            raise BadEntrySelector(self, iid)
        pos = mo.group("pos")
        if pos:
            return (EntryIndex(int(pos) - 1), mo.end())
        else:
            if mo.group("loc"):
                raise BadEntrySelector(self, iid)
            drhs = mo.group("drhs")
            val = self.type.parse_value(drhs if drhs else mo.group("srhs"))
            return (EntryValue(val), mo.end())

    def from_raw(self, val: RawLeafList) -> ArrayValue:
        """Transform a raw list array into array value.

        :param val: raw list array
        :param ns: current namespace
        """
        res = ArrayValue()
        for en in val:
            res.append(self.entry_from_raw(en))
        res.time_stamp()
        return res

    def entry_from_raw(self, val: RawValue) -> Value:
        """Transform a raw leaf-list entry into a value.

        :param val: raw list entry
        """
        return super().from_raw(val)

    def tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}*\n".format(
            self._tree_line_prefix(), self.qname)

class AnydataNode(TerminalNode):
    """Anydata node."""

    def tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}{}\n".format(
            self._tree_line_prefix(), self.qname,
            "" if self.mandatory else "?")

class AnyxmlNode(TerminalNode):
    """Anyxml node."""

    def tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}{}\n".format(
            self._tree_line_prefix(), self.qname,
            "" if self.mandatory else "?")

class NonexistentSchemaNode(YangsonException):
    """Exception to be raised when a schema node doesn't exist."""

    def __init__(self, name: YangIdentifier,
                 ns: YangIdentifier = None) -> None:
        self.qname = (ns + ":" if ns else "") + name

    def __str__(self) -> str:
        return self.qname

class SchemaNodeError(YangsonException):
    """Abstract exception class for schema node errors."""

    def __init__(self, sn: SchemaNode) -> None:
        self.schema_node = sn

    def __str__(self) -> str:
        return self.schema_node.qname

class BadSchemaNodeType(SchemaNodeError):
    """Exception to be raised when a schema node is of a wrong type."""

    def __init__(self, sn: SchemaNode, expected: str) -> None:
        super().__init__(sn)
        self.expected = expected

    def __str__(self) -> str:
        return super().__str__() + " is not a " + self.expected

class BadEntrySelector(SchemaNodeError):
    """Exception to be raised when a schema node is of a wrong type."""

    def __init__(self, sn: SchemaNode, iid: str) -> None:
        super().__init__(sn)
        self.iid = iid

    def __str__(self) -> str:
        return "in '" + self.iid + "' for " + super().__str__()
