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
RawObject = Dict[InstanceName, "RawValue"]
RawList = List["RawObject"]
RawLeafList = List[RawScalar]
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

    @staticmethod
    def uniname(iname: InstanceName) -> Tuple[YangIdentifier,
                                       Optional[YangIdentifier]]:
        """Translate instance name to a qualified name.

        If `iname` isn't prefixed with module name, the second
        component of the returned tuple is ``None``.

        :param iname: instance name
        """
        p, s, loc = iname.partition(":")
        if s: return (loc, p)
        return (p, None)

    def instance_name(self) -> InstanceName:
        """Return the instance name corresponding to the receiver."""
        return (self.name if self.ns == self.parent.ns
                else self.ns + ":" + self.name)

    def instance_route(self) -> InstanceRoute:
        """Return the instance route corresponding to the receiver."""
        return (self.parent.instance_route() + [self.instance_name()]
                if self.parent else [])

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

    def _mandatory_stmt(self, stmt, mid: ModuleId) -> None:
        if stmt.argument == "true":
            self.mandatory = True
            self.parent._mandatory_child()

    def _tree_line_prefix(self) -> str:
        return "+--"

    _stmt_callback = {
        "action": "_rpc_action_stmt",
        "anydata": "_anydata_stmt",
        "anyxml": "_anyxml_stmt",
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
        "output": "_output_stmt",
        "ordered-by": "_ordered_by_stmt",
        "presence": "_presence_stmt",
        "rpc": "_rpc_action_stmt",
        "uses": "_uses_stmt",
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
                  ns: YangIdentifier = None) -> Optional["SchemaNode"]:
        """Return receiver's child.

        :param name: child's name
        :param ns: child's namespace (= `self.ns` if absent)
        """
        ns = ns if ns else self.ns
        for c in self.children:
            if c.name == name and c.ns == ns: return c

    def get_schema_descendant(
            self, route: SchemaRoute) -> Optional["SchemaNode"]:
        """Return descendant schema node or ``None``.

        :param path: schema route of the descendant node
                     (relative to the receiver).
        """
        node = self
        for p in route:
            node = node.get_child(*p)
            if node is None: return None
        return node

    def get_data_child(
            self, name: YangIdentifier,
            ns: YangIdentifier = None) -> Optional["DataNode"]:
        """Return data node directly under receiver.

        Compared to :meth:`get_schema_descendant`, this method
        bypasses **choice** and **case** nodes.

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
        """Return descendant data node in the schema.

        :param ii: instance identifier (relative to the receiver)
        """
        node = self
        for sel in ii:
            if not isinstance(sel, MemberName): continue
            node = node.get_child(*self.uniname(sel.name))
            if node is None: return None
        return node

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}\n".format(self._tree_line_prefix(), self.instance_name())

    def _state_roots(self) -> List[SchemaNode]:
        if hasattr(self,"_config") and not self._config:
            return [self]
        res = []
        for c in self.children:
            res.extend(c._state_roots())
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

    def _leaf_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle leaf statement."""
        if Context.if_features(stmt, mid):
            node = LeafNode()
            node._type_stmt(stmt, mid)
            self._handle_child(node, stmt, mid)

    def _leaf_list_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle leaf-list statement."""
        if Context.if_features(stmt, mid):
            node = LeafListNode()
            node._type_stmt(stmt, mid)
            self._handle_child(node, stmt, mid)

    def _rpc_action_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle anydata statement."""
        if Context.if_features(stmt, mid):
            self._handle_child(RpcActionNode(), stmt, mid)

    def _anydata_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle anydata statement."""
        if Context.if_features(stmt, mid):
            self._handle_child(AnydataNode(), stmt, mid)

    def _anyxml_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle anyxml statement."""
        if Context.if_features(stmt, mid):
            self._handle_child(AnyxmlNode(), stmt, mid)

    def _from_raw(self, val: RawObject) -> ObjectValue:
        """Transform a raw dictionary into object value.

        :param val: raw dictionary
        """
        res = ObjectValue()
        for qn in val:
            cn = self.get_data_child(*self.uniname(qn))
            if cn is None:
                raise NonexistentSchemaNode(*self.uniname(qn))
            res[cn.instance_name()] = cn._from_raw(val[qn])
        res.time_stamp()
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

    def _parse_entry_selector(self, iid: str, offset: int) -> Any:
        """This method is applicable only to a list or leaf-list."""
        raise BadSchemaNodeType(self, "list or leaf-list")

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

    def _type_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Assign data type to the terminal node defined by `stmt`.

        :param stmt: YANG ``leaf`` or ``leaf-list`` statement
        :param mid: id of the context module
        """
        self.type = DataType.resolve_type(
            stmt.find1("type", required=True), mid)

    def _from_raw(self, val: RawScalar) -> ScalarValue:
        """Transform a scalar entry.

        :param val: raw lis
        :param ns: current namespace
        """
        return self.type._from_raw(val)

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
            self._tree_line_prefix(), self.instance_name(), suff)

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

class ListNode(InternalNode, SequenceNode):
    """List node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.keys = [] # type: List[QualName]

    def _key_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        kst = stmt.find1("key")
        if kst is None: return
        self.keys = [
            Context.translate_pname(k, mid) for k in kst.argument.split() ]

    def _leaf_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle leaf statement."""
        node = LeafNode()
        node._type_stmt(stmt, mid)
        self._handle_child(node, stmt, mid)
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
            res[kn.instance_name()] = val
            offset = mo.end()
        if res:
            return (EntryKeys(res), mo.end())
        raise BadEntrySelector(self, iid)

    def _from_raw(self, val: RawList) -> ArrayValue:
        """Transform a raw list array into array value.

        :param val: raw list array
        :param ns: current namespace
        """
        res = ArrayValue()
        for en in val:
            res.append(self._entry_from_raw(en))
        res.time_stamp()
        return res

    def _entry_from_raw(self, val: RawValue) -> Value:
        """Transform a raw list entry into a value.

        :param val: raw list entry
        """
        return super()._from_raw(val)

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        keys = (" [" + " ".join([ k[0] for k in self.keys ]) + "]"
                if self.keys else "")
        return "{} {}*{}\n".format(
            self._tree_line_prefix(), self.instance_name(), keys)

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
        """Handle a child node to be added to the receiver.

        :param node: child node
        :param stmt: YANG statement defining the child node
        :param mid: module context
        """
        if isinstance(node, CaseNode):
            super()._handle_child(node, stmt, mid)
        else:
            cn = CaseNode()
            cn.name = stmt.argument
            cn.ns = mid[0]
            self.add_child(cn)
            cn._handle_child(node, stmt, mid)

    def _default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.default = Context.translate_pname(stmt.argument, mid)

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} ({}){}\n".format(
            self._tree_line_prefix(), self.instance_name(),
            "" if self.mandatory else "?")

class CaseNode(InternalNode):
    """Case node."""

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{}:({})\n".format(
            self._tree_line_prefix(), self.instance_name())

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
            self._tree_line_prefix(), self.instance_name(),
            "" if self.mandatory else "?")

class LeafListNode(TerminalNode, SequenceNode):
    """Leaf-list node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.min_elements = 0 # type: int
        self.max_elements = None # type: Optional[int]

    @property
    def default(self):
        """Return the default value of the receiver or its type."""
        return self._default if self._default else [self.type.default]

    def _default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        val = self.type.parse_value(stmt.argument)
        if self._default is None:
            self._default = [val]
        else:
            self._default.append(val)

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

    def _from_raw(self, val: RawLeafList) -> ArrayValue:
        """Transform a raw list array into array value.

        :param val: raw list array
        :param ns: current namespace
        """
        res = ArrayValue()
        for en in val:
            res.append(self._entry_from_raw(en))
        res.time_stamp()
        return res

    def _entry_from_raw(self, val: RawValue) -> Value:
        """Transform a raw leaf-list entry into a value.

        :param val: raw list entry
        """
        return super()._from_raw(val)

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}*\n".format(
            self._tree_line_prefix(), self.instance_name())

class AnydataNode(TerminalNode, DataNode):
    """Anydata node."""

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}{}\n".format(
            self._tree_line_prefix(), self.instance_name(),
            "" if self.mandatory else "?")

class AnyxmlNode(TerminalNode, DataNode):
    """Anyxml node."""

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}{}\n".format(
            self._tree_line_prefix(), self.instance_name(),
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

class BadEntrySelector(SchemaNodeError):
    """Exception to be raised when a schema node is of a wrong type."""

    def __init__(self, sn: SchemaNode, iid: str) -> None:
        super().__init__(sn)
        self.iid = iid

    def __str__(self) -> str:
        return "in '" + self.iid + "' for " + super().__str__()
