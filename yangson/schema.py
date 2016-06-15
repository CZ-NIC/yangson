"""Classes for schema nodes."""

from typing import Dict, List, Optional, Tuple, Union
from .constants import DefaultDeny, YangsonException
from .context import Context
from .datatype import DataType, RawScalar
from .instvalue import ArrayValue, ObjectValue, Value
from .statement import Statement
from .typealiases import *

# Local type aliases
class SchemaNode:
    """Abstract superclass for schema nodes."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        self.name = None # type: YangIdentifier
        self.ns = None # type: YangIdentifier
        self.parent = None # type: "InternalNode"
        self.must = None # type: "Expr"
        self.when = None # type: "Expr"

    @property
    def config(self) -> bool:
        """Is the receiver configuration?"""
        try:
            return self._config
        except AttributeError:
            return self.parent.config

    def iname2qname(self, iname: InstanceName) -> QualName:
        """Translate instance name to a qualified name.

        :param iname: instance name
        """
        p, s, loc = iname.partition(":")
        return (loc, p) if s else (p, self.ns)

    def data_parent(self) -> Optional["SchemaNode"]:
        """Return the closest ancestor data node."""
        parent = self.parent
        while parent:
            if isinstance(parent, DataNode):
                return parent
            parent = parent.parent

    def iname(self) -> InstanceName:
        """Return the instance name corresponding to the receiver."""
        dp = self.data_parent()
        return (self.name if dp and self.ns == dp.ns
                else self.ns + ":" + self.name)

    def instance_route(self) -> InstanceRoute:
        """Return the instance route corresponding to the receiver."""
        return (self.parent.instance_route() + [self.iname()]
                if self.parent else [])

    def get_data_child(self, name: YangIdentifier,
                       ns: YangIdentifier) -> Optional["DataNode"]:
        """Return data node directly under the receiver.

        Compared to :meth:`get_schema_descendant`, this method
        bypasses **choice** and **case** nodes.

        :param name: data node name
        :param ns: data node namespace (= `self.ns` if absent)
        """
        return None

    def state_roots(self) -> List[InstanceRoute]:
        """Return a list of instance routes to descendant state data roots.

        If the receiver itself is state data, then the resulting list
        contains only the receiver's instance route.
        """
        if self.config:
            return [r.instance_route() for r in self._state_roots()]
        return [self.instance_route()]

    def _handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        """Dispatch actions for substatements of `stmt`."""
        for s in stmt.substatements:
            if s.prefix:
                key = Context.prefix_map[mid][s.prefix][0] + ":" + s.keyword
            else:
                key = s.keyword
            mname = SchemaNode._stmt_callback.get(key, "_noop")
            method = getattr(self, mname)
            method(s, mid)

    def _noop(self, stmt: Statement, mid: ModuleId) -> None:
        pass

    def _config_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        if stmt.argument == "false": self._config = False

    def _must_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.must = XPathParser(stmt.argument, mid).parse()

    def _when_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.when = XPathParser(stmt.argument, mid).parse()

    def _mandatory_stmt(self, stmt, mid: ModuleId) -> None:
        if stmt.argument == "true":
            self.mandatory = True
            self.parent._mandatory_child()

    def _tree_line_prefix(self) -> str:
        return "+--"

    _stmt_callback = {
        "action": "_rpc_action_stmt",
        "anydata": "_anydata_stmt",
        "anyxml": "_anydata_stmt",
        "case": "_case_stmt",
        "choice": "_choice_stmt",
        "config": "_config_stmt",
        "container": "_container_stmt",
        "default": "_default_stmt",
        "ietf-netconf-acm:default-deny-all": "_nacm_default_deny_stmt",
        "ietf-netconf-acm:default-deny-write": "_nacm_default_deny_stmt",
        "input": "_input_stmt",
        "leaf": "_leaf_stmt",
        "leaf-list": "_leaf_list_stmt",
        "list": "_list_stmt",
        "mandatory": "_mandatory_stmt",
        "max-elements": "_max_elements_stmt",
        "min-elements": "_min_elements_stmt",
        "must": "_must_stmt",
        "notification": "_notification_stmt",
        "output": "_output_stmt",
        "ordered-by": "_ordered_by_stmt",
        "presence": "_presence_stmt",
        "rpc": "_rpc_action_stmt",
        "unique": "_unique_stmt",
        "uses": "_uses_stmt",
        "when": "_when_stmt",
        }
    """Map of statement keywords to callback methods."""


class InternalNode(SchemaNode):
    """Abstract superclass for schema nodes that have children."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.children = [] # type: List[SchemaNode]
        self._nsswitch = False # type: bool

    def _mandatory_child(self) -> None:
        """A child of the receiver is mandatory; perform necessary actions."""
        pass

    def add_child(self, node: SchemaNode) -> None:
        """Add child node to the receiver.

        :param node: child node
        """
        node.parent = self
        self.children.append(node)

    def get_child(self, name: YangIdentifier,
                  ns: YangIdentifier) -> Optional["SchemaNode"]:
        """Return receiver's child.

        :param name: child's name
        :param ns: child's namespace (= `self.ns` if absent)
        """
        for c in self.children:
            if c.name == name and c.ns == ns: return c

    def get_schema_descendant(
            self, route: SchemaRoute) -> Optional["SchemaNode"]:
        """Return descendant schema node or ``None``.

        :param route: schema route of the descendant node
                     (relative to the receiver).
        """
        node = self
        for p in route:
            node = node.get_child(*p)
            if node is None: return None
        return node

    def get_data_child(self, name: YangIdentifier,
                       ns: YangIdentifier) -> Optional["DataNode"]:
        """Return data node directly under the receiver.

        This method overrides the superclass method.
        """
        todo = []
        for c in self.children:
            if c.name ==name and c.ns == ns:
                if isinstance(c, DataNode):
                    return c
                todo.insert(0,c)
            elif isinstance(c, (ChoiceNode, CaseNode)):
                todo.append(c)
        for c in todo:
            res = c.get_data_child(name, ns)
            if res: return res

    def data_children(self) -> List["DataNode"]:
        """Return the list of all data nodes directly under the receiver."""
        res = []
        for c in self.children:
            if isinstance(c, DataNode):
                res.append(c)
            else:
                res.extend(c.data_children())
        return res

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}\n".format(self._tree_line_prefix(), self.iname())

    def _state_roots(self) -> List[SchemaNode]:
        if hasattr(self,"_config") and not self._config:
            return [self]
        res = []
        for c in self.children:
            res += c._state_roots()
        return res

    def _handle_child(
            self, node: SchemaNode, stmt: Statement, mid: ModuleId) -> None:
        """Add child node to the receiver and handle substatements."""
        node.name = stmt.argument
        node.ns = Context.ns_map[mid[0]] if self._nsswitch else self.ns
        self.add_child(node)
        node._handle_substatements(stmt, mid)

    def _augment_refine(self, stmt: Statement, mid: ModuleId,
                       nsswitch: bool = False) -> None:
        """Handle an augment or refine statement.""" 
        if Context.if_features(stmt, mid):
            path = Context.sid2route(stmt.argument, mid)
            target = self.get_schema_descendant(path)
            target._nsswitch = nsswitch
            target._handle_substatements(stmt, mid)

    def _uses_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle uses statement."""
        if Context.if_features(stmt, mid):
            grp, gid = Context.get_definition(stmt, mid)
            self._handle_substatements(grp, gid)
            for augref in stmt.find_all("augment") + stmt.find_all("refine"):
                self._augment_refine(augref, mid, False)

    def _container_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle container statement."""
        if Context.if_features(stmt, mid):
            self._handle_child(ContainerNode(), stmt, mid)

    def _list_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle list statement."""
        if Context.if_features(stmt, mid):
            node = ListNode()
            node._key_stmt(stmt, mid)
            self._handle_child(node, stmt, mid)

    def _choice_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle choice statement."""
        if Context.if_features(stmt, mid):
            self._handle_child(ChoiceNode(), stmt, mid)

    def _case_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle case statement."""
        if Context.if_features(stmt, mid):
            self._handle_child(CaseNode(), stmt, mid)

    def _leaf_stmt(self, stmt: Statement,
                   mid: ModuleId) -> Optional["LeafNode"]:
        """Handle leaf statement."""
        if Context.if_features(stmt, mid):
            node = LeafNode()
            node.type = DataType.resolve_type(
                stmt.find1("type", required=True), mid)
            self._handle_child(node, stmt, mid)
            return node

    def _leaf_list_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle leaf-list statement."""
        if Context.if_features(stmt, mid):
            node = LeafListNode()
            node.type = DataType.resolve_type(
                stmt.find1("type", required=True), mid)
            self._handle_child(node, stmt, mid)

    def _rpc_action_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle rpc or action statement."""
        if Context.if_features(stmt, mid):
            self._handle_child(RpcActionNode(), stmt, mid)

    def _notification_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle notification statement."""
        if Context.if_features(stmt, mid):
            self._handle_child(NotificationNode(), stmt, mid)

    def _anydata_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle anydata statement."""
        if Context.if_features(stmt, mid):
            self._handle_child(AnydataNode(), stmt, mid)

    def from_raw(self, val: RawObject) -> ObjectValue:
        """Transform a raw dictionary into object value.

        :param val: raw dictionary
        """
        res = ObjectValue({})
        for qn in val:
            cn = self.iname2qname(qn)
            ch = self.get_data_child(*cn)
            if ch is None:
                raise NonexistentSchemaNode(*cn)
            res[ch.iname()] = ch.from_raw(val[qn])
        return res

    def _ascii_tree(self, indent: str) -> str:
        """Return the receiver's subtree as ASCII art."""
        res = ""
        if not self.children: return res
        for c in self.children[:-1]:
            res += indent + c._tree_line() + c._ascii_tree(indent + "|  ")
        return (res + indent + self.children[-1]._tree_line() +
                self.children[-1]._ascii_tree(indent + "   "))

class DataNode(SchemaNode):
    """Abstract superclass for data nodes."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self.default_deny = DefaultDeny.none # type: "DefaultDeny"

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + ("rw" if self.config else "ro")

    def _nacm_default_deny_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Set NACM default access."""
        if stmt.keyword == "default-deny-all":
            self.default_deny = DefaultDeny.all
        elif stmt.keyword == "default-deny-write":
            self.default_deny = DefaultDeny.write

class TerminalNode(SchemaNode):
    """Abstract superclass for terminal nodes in the schema tree."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self._default = None
        self.mandatory = False # type: bool
        self.type = None # type: DataType

    def from_raw(self, val: RawScalar) -> ScalarValue:
        """Transform a scalar value.

        :param val: raw scalar value
        """
        return self.type.from_raw(val)

    def _ascii_tree(self, indent: str) -> str:
        """Return the receiver's ascii-art subtree."""
        return ""

    def _state_roots(self) -> List[SchemaNode]:
        if hasattr(self,"_config") and not self._config:
            return [self]
        return []

class ContainerNode(InternalNode, DataNode):
    """Container node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.presence = False # type: bool
        self.mandatory = False # type: bool

    def _mandatory_child(self) -> None:
        """A child of the receiver is mandatory; perform necessary actions."""
        if self.presence: return
        self.mandatory = True
        self.parent._mandatory_child()

    def _presence_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.presence = True

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        if self.presence:
            suff = "!"
        elif self.mandatory:
            suff = ""
        else:
            suff = "?"
        return "{} {}{}\n".format(
            self._tree_line_prefix(), self.iname(), suff)

class SequenceNode(DataNode):
    """Abstract class for data nodes that represent a sequence."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.keys = [] # type: List[QualName]
        self.min_elements = 0 # type: int
        self.max_elements = None # type: Optional[int]
        self.user_ordered = False # type: bool

    def _min_elements_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.min_elements = int(stmt.argument)
        if self.min_elements > 0:
            self.parent._mandatory_child()

    def _max_elements_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        arg = stmt.argument
        if arg == "unbounded":
            self.max_elements = None
        else:
            self.max_elements = int(arg)

    def _ordered_by_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.user_ordered = stmt.argument == "user"

    def from_raw(self, val: RawList) -> ArrayValue:
        """Transform a raw array into array value.

        :param val: raw array
        """
        res = ArrayValue([])
        for en in val:
            res.append(self._entry_from_raw(en))
        return res

    def _entry_from_raw(self, val: RawValue) -> Value:
        """Transform a raw list entry into a value.

        :param val: raw list entry
        """
        return super().from_raw(val)

class ListNode(SequenceNode, InternalNode):
    """List node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.keys = [] # type: List[QualName]
        self.unique = [] # type: List[List[SchemaRoute]]

    def _key_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        kst = stmt.find1("key")
        if kst is None: return
        self.keys = [
            Context.translate_pname(k, mid) for k in kst.argument.split() ]

    def _unique_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.unique.append(
            [ Context.sid2route(sid, mid) for sid in stmt.argument.split() ])

    def _leaf_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle leaf statement."""
        node = super()._leaf_stmt(stmt, mid)
        if node and (node.name, node.ns) in self.keys:
            node.mandatory = True

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        keys = (" [" + " ".join([ k[0] for k in self.keys ]) + "]"
                if self.keys else "")
        return "{} {}*{}\n".format(
            self._tree_line_prefix(), self.iname(), keys)

class ChoiceNode(InternalNode):
    """Choice node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.default = None # type: QualName
        self.mandatory = False # type: bool

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + ("rw" if self.config else "ro")

    def _handle_child(self, node: SchemaNode, stmt: SchemaNode,
                     mid: ModuleId) -> None:
        if isinstance(node, CaseNode):
            super()._handle_child(node, stmt, mid)
        else:
            cn = CaseNode()
            cn.name = stmt.argument
            cn.ns = Context.ns_map[mid[0]] if self._nsswitch else self.ns
            self.add_child(cn)
            cn._handle_child(node, stmt, mid)

    def _default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.default = Context.translate_pname(stmt.argument, mid)

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} ({}){}\n".format(
            self._tree_line_prefix(), self.iname(),
            "" if self.mandatory else "?")

class CaseNode(InternalNode):
    """Case node."""

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{}:({})\n".format(
            self._tree_line_prefix(), self.iname())

class RpcActionNode(InternalNode):
    """RPC or action node."""

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + "-x"

    def state_roots(self) -> List[InstanceRoute]:
        """Return a list of routes to descendant state data roots (or self)."""
        return []

    def _state_roots(self) -> List[SchemaNode]:
        return []

    def _input_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle RPC or action input statement."""
        inp = InputNode()
        inp.name = "input"
        inp.ns = self.ns
        inp._config = False
        self.add_child(inp)
        inp._handle_substatements(stmt, mid)

    def _output_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle RPC or action output statement."""
        outp = OutputNode()
        outp.name = "output"
        outp.ns = self.ns
        outp._config = False
        self.add_child(outp)
        outp._handle_substatements(stmt, mid)

class InputNode(InternalNode):
    """RPC or action input node."""

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + "ro"

class OutputNode(InternalNode):
    """RPC or action output node."""

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + "ro"

class NotificationNode(InternalNode):
    """Notification node."""

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + "-n"

    def state_roots(self) -> List[InstanceRoute]:
        """Return a list of routes to descendant state data roots (or self)."""
        return []

    def _state_roots(self) -> List[SchemaNode]:
        return []

class LeafNode(TerminalNode, DataNode):
    """Leaf node."""

    @property
    def default(self):
        """Return the default value of the receiver or its type."""
        return self._default if self._default else self.type.default

    def _default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self._default = self.type.parse_value(stmt.argument)

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}{}\n".format(
            self._tree_line_prefix(), self.iname(),
            "" if self.mandatory else "?")

class LeafListNode(SequenceNode, TerminalNode):
    """Leaf-list node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.min_elements = 0 # type: int
        self.max_elements = None # type: Optional[int]

    @property
    def default(self):
        """Return the default value of the receiver or its type."""
        if self._default:
            return self._default
        if self.type.default is None:
            return None
        return [self.type.default]

    def _default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        val = self.type.parse_value(stmt.argument)
        if self._default is None:
            self._default = [val]
        else:
            self._default.append(val)

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}*\n".format(
            self._tree_line_prefix(), self.iname())

class AnydataNode(TerminalNode, DataNode):
    """Anydata or anyxml node."""

    def from_raw(self, val: RawValue) -> Value:
        """Transform an anydata or anyxml value.

        :param val: raw value
        """
        def convert(val):
            if isinstance(val, list):
                res = ArrayValue([convert(x) for x in val])
                res.stamp()
            elif isinstance(val, dict):
                res = ObjectValue({ x:convert(val[x]) for x in val })
                res.stamp()
            else:
                res = val
            return res
        return convert(val)

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}{}\n".format(
            self._tree_line_prefix(), self.iname(),
            "" if self.mandatory else "?")

class NonexistentSchemaNode(YangsonException):
    """Exception to be raised when a schema node doesn't exist."""

    def __init__(self, name: YangIdentifier,
                 ns: YangIdentifier = None) -> None:
        self.name = name
        self.ns = ns

    def __str__(self) -> str:
        return "{} in module {}".format(self.name, self.ns)

class SchemaNodeError(YangsonException):
    """Abstract exception class for schema node errors."""

    def __init__(self, sn: SchemaNode) -> None:
        self.schema_node = sn

    def __str__(self) -> str:
        return "{} in module {}".format(self.schema_node.name,
                                        self.schema_node.ns)

class BadSchemaNodeType(SchemaNodeError):
    """Exception to be raised when a schema node is of a wrong type."""

    def __init__(self, sn: SchemaNode, expected: str) -> None:
        super().__init__(sn)
        self.expected = expected

    def __str__(self) -> str:
        return super().__str__() + " is not a " + self.expected

from .xpath import Expr, XPathParser
