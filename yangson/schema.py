"""Classes for schema nodes."""

from typing import Dict, List, MutableSet, Optional, Set, Tuple, Union
from .constants import DefaultDeny, NonexistentSchemaNode, YangsonException
from .context import Context
from .datatype import DataType, RawScalar
from .instvalue import ArrayValue, ObjectValue, Value
from .statement import Statement, WrongArgument
from .typealiases import *
from .xpathparser import XPathParser

# Local type aliases
class SchemaNode:
    """Abstract superclass for schema nodes."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        self.name = None # type: YangIdentifier
        self.ns = None # type: YangIdentifier
        self.parent = None # type: "InternalNode"
        self.must = [] # type: List["Expr"]
        self.when = None # type: "Expr"

    @property
    def qual_name(self) -> QualName:
        """Return qualified name of the receiver."""
        return (self.name, self.ns)

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

        :param name: data child's name
        :param ns: data child's namespace
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

    def _if_feature_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        if Context.translate_pname(stmt.argument, mid) not in Context.features:
            del self.parent.children[self.qual_name]

    def _config_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        if stmt.argument == "false": self._config = False

    def _must_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        xpp = XPathParser(stmt.argument, mid)
        mex = xpp.parse()
        if not xpp.at_end():
            raise WrongArgument(stmt)
        self.must.append(mex)

    def _when_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        xpp = XPathParser(stmt.argument, mid)
        wex = xpp.parse()
        if not xpp.at_end():
            raise WrongArgument(stmt)
        self.when = wex

    def _mandatory_stmt(self, stmt, mid: ModuleId) -> None:
        if stmt.argument == "true":
            self.mandatory = True
        elif stmt.argument == "false":
            self.mandatory = False

    def _post_process(self) -> None:
        pass

    def _default_nodes(self, inst: "InstanceNode") -> List["InstanceNode"]:
        return []

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
        "identity": "_identity_stmt",
        "ietf-netconf-acm:default-deny-all": "_nacm_default_deny_stmt",
        "ietf-netconf-acm:default-deny-write": "_nacm_default_deny_stmt",
        "if-feature": "_if_feature_stmt",
        "input": "_input_stmt",
        "key": "_key_stmt",
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
        self.children = {} # type: Dict[QualName, SchemaNode]
        self._nsswitch = False # type: bool
        self.default_children = [] # type: List["SchemaNode"]
        self.mandatory_children = [] # type: List["SchemaNode"]

    def add_child(self, node: SchemaNode) -> None:
        """Add child node to the receiver.

        :param node: child node
        """
        node.parent = self
        self.children[node.qual_name] = node

    def get_child(self, name: YangIdentifier,
                  ns: YangIdentifier = None) -> Optional["SchemaNode"]:
        """Return receiver's child.

        :param name: child's name
        :param ns: child's namespace (= `self.ns` if absent)
        """
        return self.children.get((name, ns if ns else self.ns))

    def get_schema_descendant(
            self, route: SchemaRoute) -> Optional["SchemaNode"]:
        """Return descendant schema node or ``None``.

        :param route: schema route of the descendant node
                     (relative to the receiver).
        """
        node = self
        for p in route:
            node = node.children.get(p)
            if node is None: return None
        return node

    def get_data_child(self, name: YangIdentifier,
                       ns: YangIdentifier) -> Optional["DataNode"]:
        """Return data node directly under the receiver.

        This method overrides the superclass method.
        """
        todo = []
        for cn, child in self.children.items():
            if cn == (name, ns):
                if isinstance(child, DataNode): return child
                todo.insert(0, child)
            elif isinstance(child, (ChoiceNode, CaseNode)):
                todo.append(child)
        for c in todo:
            res = c.get_data_child(name, ns)
            if res: return res

    def data_children(self) -> MutableSet["DataNode"]:
        """Return the set of all data nodes directly under the receiver."""
        res = set()
        for c in self.children.values():
            if isinstance(c, DataNode):
                res.add(c)
            else:
                res.update(c.data_children())
        return res

    def child_inst_names(self) -> Set[InstanceName]:
        """Return the set of instance names under the receiver."""
        return frozenset([c.iname() for c in self.data_children()])

    def _post_process(self) -> None:
        super()._post_process()
        for c in [x for x in self.children.values()]:
            c._post_process()

    def _add_default_child(self, node: SchemaNode) -> None:
        """Add `node` to the list of default children."""
        self.default_children.append(node)

    def _add_mandatory_child(self, node: SchemaNode) -> None:
        """Add `node` to the set of mandatory children."""
        self.mandatory_children.append(node)

    def default_value(self) -> Optional[ObjectValue]:
        """Return the receiver's default content."""
        res = ObjectValue()
        for c in self.default_children:
            dflt = c.default_value()
            if dflt is not None:
                res[c.iname()] = dflt
        return res

    def _apply_defaults(self, value: ObjectValue) -> None:
        """Return a copy of `value` with added default contents."""
        for c in self.default_children:
            if isinstance(c, ChoiceNode):
                ac = c.active_case(value)
                if ac:
                    ac._apply_defaults(value)
                elif c.default_case:
                    value.update(c.children.get(c.default_case).default_value())
            else:
                cn = c.iname()
                if cn not in value:
                    value[cn] = c.default_value()

    def _check_mandatory(self, value: ObjectValue) -> bool:
        """Does `value` contains all members required by the receiver?"""
        for c in self.mandatory_children:
            if isinstance(c, ChoiceNode):
                ac = c.active_case(value)
                if ac is None or not ac._check_mandatory(value):
                    return False
            else:
                if c.iname() not in value: return False
        return True

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}\n".format(self._tree_line_prefix(), self.iname())

    def _state_roots(self) -> List[SchemaNode]:
        if hasattr(self,"_config") and not self._config:
            return [self]
        res = []
        for c in self.children.values():
            res += c._state_roots()
        return res

    def _handle_child(
            self, node: SchemaNode, stmt: Statement, mid: ModuleId) -> None:
        """Add child node to the receiver and handle substatements."""
        node.name = stmt.argument
        node.ns = Context.ns_map[mid[0]] if self._nsswitch else self.ns
        self.add_child(node)
        node._handle_substatements(stmt, mid)

    def _augment_stmt(self, stmt: Statement, mid: ModuleId,
                      nsswitch: bool = False) -> None:
        """Handle **augment** statement."""
        if Context.if_features(stmt, mid):
            path = Context.sid2route(stmt.argument, mid)
            target = self.get_schema_descendant(path)
            target._nsswitch = nsswitch
            target._handle_substatements(stmt, mid)

    def _refine_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle **refine** statement."""
        path = Context.sid2route(stmt.argument, mid)
        self.get_schema_descendant(path)._handle_substatements(stmt, mid)

    def _uses_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle uses statement."""
        if Context.if_features(stmt, mid):
            grp, gid = Context.get_definition(stmt, mid)
            self._handle_substatements(grp, gid)
            for augst in stmt.find_all("augment"):
                self._augment_stmt(augst, mid, False)
            for refst in stmt.find_all("refine"):
                self._refine_stmt(refst, mid)

    def _container_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle container statement."""
        self._handle_child(ContainerNode(), stmt, mid)

    def _identity_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle identity statement."""
        if Context.if_features(stmt, mid):
            bases = stmt.find_all("base")
            Context.identity_bases[(stmt.argument, mid[0])] = set(
                [Context.translate_pname(ist.argument, mid) for ist in bases])

    def _list_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle list statement."""
        self._handle_child(ListNode(), stmt, mid)

    def _choice_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle choice statement."""
        self._handle_child(ChoiceNode(), stmt, mid)

    def _case_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle case statement."""
        self._handle_child(CaseNode(), stmt, mid)

    def _leaf_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle leaf statement."""
        node = LeafNode()
        node.type = DataType.resolve_type(
            stmt.find1("type", required=True), mid)
        self._handle_child(node, stmt, mid)

    def _leaf_list_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle leaf-list statement."""
        node = LeafListNode()
        node.type = DataType.resolve_type(
            stmt.find1("type", required=True), mid)
        self._handle_child(node, stmt, mid)

    def _rpc_action_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle rpc or action statement."""
        self._handle_child(RpcActionNode(), stmt, mid)

    def _notification_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle notification statement."""
        self._handle_child(NotificationNode(), stmt, mid)

    def _anydata_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle anydata statement."""
        self._handle_child(AnydataNode(), stmt, mid)

    def from_raw(self, val: RawObject) -> ObjectValue:
        """Transform a raw dictionary into object value.

        :param val: raw dictionary
        """
        res = ObjectValue()
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
        cns = sorted(self.children.keys())
        for cn in cns[:-1]:
            c = self.children[cn]
            res += indent + c._tree_line() + c._ascii_tree(indent + "|  ")
        lc = self.children[cns[-1]]
        return res + indent + lc._tree_line() + lc._ascii_tree(indent + "   ")

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
        self.default = None
        self.type = None # type: DataType

    def from_raw(self, val: RawScalar) -> ScalarValue:
        """Transform a scalar value.

        :param val: raw scalar value
        """
        return self.type.from_raw(val)

    def default_value(self) -> None:
        return None

    def _default_nodes(self, inst: "InstanceNode") -> List["InstanceNode"]:
        dflt = self.default_value()
        if dflt is None: return []
        iname = self.iname()
        ni = inst.put_member(iname, (None,))
        res = ni.member(iname)
        if self.when is None or self.when.evaluate(res):
            res.value = dflt
            return res.xpath_nodes()
        return []

    def _ascii_tree(self, indent: str) -> str:
        """Return the receiver's ascii-art subtree."""
        return ""

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        res = "{} {}".format(self._tree_line_prefix(), self.iname())
        if not self.mandatory: res += "?"
        return res + "\n"

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

    def _add_default_child(self, node: SchemaNode) -> None:
        """Extend the superclass method."""
        if not (self.presence or self.default_children):
            self.parent._add_default_child(self)
        super()._add_default_child(node)

    def _add_mandatory_child(self, node: SchemaNode):
        if not (self.presence or self.mandatory_children):
            self.parent._add_mandatory_child(self)
        super()._add_mandatory_child(node)

    def _default_nodes(self, inst: "InstanceNode") -> List["InstanceNode"]:
        if self.presence: return []
        iname = self.iname()
        ni = inst.put_member(iname, ObjectValue())
        res = ni.member(iname)
        if self.when is None or self.when.evaluate(res):
            return [res]
        return []

    def _presence_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.presence = True

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        res = "{} {}".format(self._tree_line_prefix(), self.iname())
        if self.presence: res += "!"
        return res + "\n"

class SequenceNode(DataNode):
    """Abstract class for data nodes that represent a sequence."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.min_elements = 0 # type: int
        self.max_elements = None # type: Optional[int]
        self.user_ordered = False # type: bool

    def _post_process(self) -> None:
        super()._post_process()
        if self.min_elements > 0:
            self.parent._add_mandatory_child(self)

    def _min_elements_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.min_elements = int(stmt.argument)

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
        res = ArrayValue()
        for en in val:
            res.append(super().from_raw(en))
        return res

class ListNode(SequenceNode, InternalNode):
    """List node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.keys = [] # type: List[QualName]
        self.unique = [] # type: List[List[SchemaRoute]]

    def _add_default_child(self, node: SchemaNode) -> None:
        if node.qual_name not in self.keys:
            super()._add_default_child(node)

    def _post_process(self) -> None:
        super()._post_process()
        for k in self.keys:
            kn = self.children[k]
            if not kn.mandatory:
                kn.mandatory = True
                self.mandatory_children.append(kn)

    def _key_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.keys = [
            Context.translate_pname(k, mid) for k in stmt.argument.split()]

    def _unique_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.unique.append(
            [Context.sid2route(sid, mid) for sid in stmt.argument.split()])

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
        self.default_case = None # type: QualName
        self.mandatory = False # type: bool

    def _add_default_child(self, node: "CaseNode") -> None:
        """Extend the superclass method."""
        if not (self.mandatory or self.default_children):
            self.parent._add_default_child(self)
        super()._add_default_child(node)

    def _post_process(self) -> None:
        super()._post_process()
        if self.mandatory:
            self.parent._add_mandatory_child(self)

    def _default_nodes(self, inst: "InstanceNode") -> List["InstanceNode"]:
        res = []
        if self.default_case is None: return res
        for cn in self.children[self.default_case].children.values():
            res.extend(cn._default_nodes(inst))
        return res

    def default_value(self) -> Optional[ObjectValue]:
        """Return the receiver's default content."""
        if self.default_case in [c.qual_name for c in self.default_children]:
            return self.children.get(self.default_case).default_value()

    def active_case(self, value: ObjectValue) -> Optional["CaseNode"]:
        """Return receiver's case that's active in `value`."""
        for case in self.children.values():
            for cc in case.children.values():
                if (isinstance(cc, ChoiceNode) and cc.active_case(value)
                    or cc.iname() in value):
                        return case

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
        self.default_case = Context.translate_pname(stmt.argument, mid)

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} ({}){}\n".format(
            self._tree_line_prefix(), self.iname(),
            "" if self.mandatory else "?")

class CaseNode(InternalNode):
    """Case node."""

    def competing_instances(self) -> List[InstanceName]:
        """Return list of names of all instances from sibling cases."""
        res = []
        for case in self.parent.children.values():
            if case is not self:
                res.extend([c.iname() for c in case.data_children()])
        return res

    def _add_default_child(self, node: SchemaNode) -> None:
        """Extend the superclass method."""
        if not self.default_children:
            self.parent._add_default_child(self)
        super()._add_default_child(node)

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

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.mandatory = False # type: bool

    def _post_process(self) -> None:
        if self.mandatory:
            self.parent._add_mandatory_child(self)
        elif self.default_value() is not None:
            self.parent._add_default_child(self)

    def default_value(self) -> Optional[ScalarValue]:
        """Return the default value of the receiver or its type."""
        return self.default if self.default else self.type.default

    def _default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.default = self.type.from_yang(stmt.argument, mid)

class LeafListNode(SequenceNode, TerminalNode):
    """Leaf-list node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.min_elements = 0 # type: int
        self.max_elements = None # type: Optional[int]

    def _post_process(self) -> None:
        super()._post_process()
        if self.min_elements == 0 and self.default_value() is not None:
            self.parent._add_default_child(self)

    def default_value(self) -> Optional[ArrayValue]:
        """Return the default value of the receiver or its type."""
        if self.default:
            return self.default
        if self.type.default is not None:
            return ArrayValue([self.type.default])

    def _default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        val = self.type.parse_value(stmt.argument)
        if self.default is None:
            self.default = ArrayValue([val])
        else:
            self.default.append(val)

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} {}*\n".format(
            self._tree_line_prefix(), self.iname())

class AnydataNode(TerminalNode, DataNode):
    """Anydata or anyxml node."""

    def __init__(self) -> None:
        """Initialize the class instance."""
        super().__init__()
        self.mandatory = False # type: bool

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

    def _post_process(self) -> None:
        if self.mandatory:
            self.parent._add_mandatory_child(self)

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

from .xpathast import Expr
from .instance import InstanceNode
