# Copyright © 2016 CZ.NIC, z. s. p. o.
#
# This file is part of Yangson.
#
# Yangson is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Yangson is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with Yangson.  If not, see <http://www.gnu.org/licenses/>.

"""Classes representing YANG schema nodes.

This module implements the following classes:

* SchemaNode: Abstract class for schema nodes.
* InternalNode: Abstract class for schema nodes that have children.
* GroupNode: Anonymous group of schema nodes.
* DataNode: Abstract class for data nodes.
* TerminalNode: Abstract class for schema nodes that have no children.
* ContainerNode: YANG container node.
* SequenceNode: Abstract class for schema nodes that represent a sequence.
* ListNode: YANG list node.
* ChoiceNode: YANG choice node.
* CaseNode: YANG case node.
* RpcActionNode: YANG rpc or action node.
* InputNode: YANG input node.
* OutputNode: YANG output node.
* NotificationNode: YANG notification node.
* LeafNode: YANG leaf node.
* LeafListNode: YANG leaf-list node.
* AnydataNode: YANG anydata or anyxml node.

This module defines the following exceptions:

* SchemaNodeException: Abstract exception class for schema node errors.
* NonexistentSchemaNode: A schema node doesn't exist.
* BadSchemaNodType: A schema node is of a wrong type.
* BadLeafrefPath: A leafref path is incorrect.
* ValidationError: Abstract exeption class for instance validation errors.
* SchemaError: An instance violates a schema constraint.
* SemanticError: An instance violates a semantic rule.
"""

from typing import Dict, List, MutableSet, Optional, Set, Tuple, Union
from .exceptions import YangsonException
from .context import Context
from .datatype import (DataType, LeafrefType, LinkType,
                       RawScalar, IdentityrefType)
from .enumerations import Axis, ContentType, DefaultDeny
from .instvalue import ArrayValue, EntryValue, ObjectValue, Value
from .schpattern import *
from .statement import Statement, WrongArgument
from .typealiases import *
from .xpathparser import XPathParser

class SchemaNode:
    """Abstract class for all schema nodes."""

    def __init__(self):
        """Initialize the class instance."""
        self.name = None # type: Optional[YangIdentifier]
        """Name of the schema node."""
        self.ns = None # type: Optional[YangIdentifier]
        """Namespace of the schema node."""
        self.parent = None # type: Optional["InternalNode"]
        """Parent schema node."""
        self.must = [] # type: List[Tuple["Expr", Optional[str]]]
        """List of "must" expressions attached to the schema node."""
        self.when = None # type: Optional["Expr"]
        """Optional "when" expression that makes the schema node conditional."""
        self._ctype = None
        """Content type of the schema node."""

    @property
    def qual_name(self) -> QualName:
        """Qualified name of the receiver."""
        return (self.name, self.ns)

    @property
    def config(self) -> bool:
        """Does the receiver (also) represent configuration?"""
        return self.content_type().value & ContentType.config.value != 0

    @property
    def mandatory(self) -> bool:
        """Is the receiver a mandatory node?"""
        return False

    def content_type(self) -> ContentType:
        """Return receiver's content type."""
        return self._ctype if self._ctype else self.parent.content_type()

    def data_parent(self) -> Optional["InternalNode"]:
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

    def data_path(self) -> DataPath:
        """Return the receiver's data path."""
        dp = self.data_parent()
        return (dp.data_path() if dp else "") + "/" + self.iname()

    def state_roots(self) -> List[DataPath]:
        """Return a list of data paths to descendant state data roots."""
        return [r.data_path() for r in self._state_roots()]

    def validate(self, inst: "InstanceNode", ctype: ContentType) -> None:
        """Validate instance against the receiver.

        Args:
            inst: Instance node to be validated.
            ctype: Content type of the instance.

        Returns:
            ``None`` if validation succeeds.

        Raises:
            SchemaError: if `inst` violates the schema.
            SemanticError: If a "must" expression evaluates to ``False``.
        """
        pass

    def from_raw(self, rval: RawValue) -> Value:
        """Return instance value transformed from a raw value using receiver.

        Args:
            rval: Raw value.

        Raises:
            NonexistentSchemaNode: If a member inside `rval` is not defined
                in the schema.
            YangTypeError: If a scalar value inside `rval` is of incorrect type.
        """
        raise NotImplementedError

    def _iname2qname(self, iname: InstanceName) -> QualName:
        """Translate instance name to qualified name in the receiver's context.
        """
        p, s, loc = iname.partition(":")
        return (loc, p) if s else (p, self.ns)

    def _flatten(self) -> List["SchemaNode"]:
        return [self]

    def _handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        """Dispatch actions for substatements of `stmt`."""
        for s in stmt.substatements:
            if s.prefix:
                key = Context.modules[mid].prefix_map[s.prefix][0] + ":" + s.keyword
            else:
                key = s.keyword
            mname = SchemaNode._stmt_callback.get(key, "_noop")
            method = getattr(self, mname)
            method(s, mid)

    def _follow_leafref(self, xpath: "Expr") -> Optional["DataNode"]:
        """Return the data node referred to by a leafref path.

        Args:
            xpath: XPath expression compiled from a leafref path.
        """
        if isinstance(xpath, LocationPath):
            lft = self._follow_leafref(xpath.left)
            if lft is None: return None
            return lft._follow_leafref(xpath.right)
        elif isinstance(xpath, Step):
            if xpath.axis == Axis.parent:
                return self.data_parent()
            elif xpath.axis == Axis.child:
                if isinstance(self, InternalNode) and xpath.qname:
                    return self.get_data_child(*xpath.qname)
        elif isinstance(xpath, Root):
            return Context.schema
        return None

    def _noop(self, stmt: Statement, mid: ModuleId) -> None:
        pass

    def _config_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        if stmt.argument == "true" and self.parent.config:
            self._ctype = ContentType.all
        elif stmt.argument == "false":
            self._ctype = ContentType.nonconfig

    def _must_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        xpp = XPathParser(stmt.argument, mid)
        mex = xpp.parse()
        if not xpp.at_end():
            raise WrongArgument(stmt)
        ems = stmt.find1("error-message")
        self.must.append((mex, ems.argument if ems else None))

    def _when_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        xpp = XPathParser(stmt.argument, mid)
        wex = xpp.parse()
        if not xpp.at_end():
            raise WrongArgument(stmt)
        self.when = wex

    def _mandatory_stmt(self, stmt, mid: ModuleId) -> None:
        if stmt.argument == "true":
            self._mandatory = True
        elif stmt.argument == "false":
            self._mandatory = False

    def _post_process(self) -> None:
        pass

    def _is_identityref(self) -> bool:
        return False

    def _default_nodes(self, inst: "InstanceNode") -> List["InstanceNode"]:
        return []

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return self._tree_line_prefix() + " " + self.iname()

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
    """Abstract class for schema nodes that have children."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self.children = [] # type: List[SchemaNode]
        self._new_ns = None # type: Optional[ModuleId]
        self._mandatory_children = set() # type: MutableSet[SchemaNode]

    @property
    def mandatory(self) -> bool:
        """Is the receiver a mandatory node?"""
        return len(self._mandatory_children) > 0

    def get_child(self, name: YangIdentifier,
                  ns: YangIdentifier = None) -> Optional[SchemaNode]:
        """Return receiver's schema child.

        Args:
            name: Child's name.
            ns: Child's namespace (= `self.ns` if absent).
        """
        ns = ns if ns else self.ns
        todo = []
        for child in self.children:
            if child.name is None:
                todo.append(child)
            elif child.name == name and child.ns == ns:
                return child
        for c in todo:
            return c.get_child(name, ns)

    def get_schema_descendant(
            self, route: SchemaRoute) -> Optional[SchemaNode]:
        """Return descendant schema node or ``None`` if not found.

        Args:
            route: Schema route to the descendant node
                   (relative to the receiver).
        """
        node = self
        for p in route:
            node = node.get_child(*p)
            if node is None: return None
        return node

    def get_data_child(self, name: YangIdentifier,
                       ns: YangIdentifier = None) -> Optional["DataNode"]:
        """Return data node directly under the receiver."""
        ns = ns if ns else self.ns
        todo = []
        for child in self.children:
            if child.name == name and child.ns == ns:
                if isinstance(child, DataNode): return child
                todo.insert(0, child)
            elif not isinstance(child, DataNode):
                todo.append(child)
        for c in todo:
            res = c.get_data_child(name, ns)
            if res: return res

    def filter_children(self, ctype: ContentType = None) -> List[SchemaNode]:
        """Return receiver's children based on content type.

        Args:
            ctype: Content type.
        """
        if ctype is None:
            ctype = self.content_type()
        return [c for c in self.children if
                not isinstance(c, (RpcActionNode, NotificationNode)) and
                c.content_type().value & ctype.value != 0]

    def data_children(self) -> List["DataNode"]:
        """Return the set of all data nodes directly under the receiver."""
        res = []
        for child in self.children:
            if isinstance(child, DataNode):
                res.append(child)
            else:
                res.extend(child.data_children())
        return res

    def validate(self, inst: "InstanceNode", ctype: ContentType) -> None:
        """Extend the superclass method."""
        if not isinstance(inst.value, ObjectValue):
            raise SchemaError(inst, "non-object value")
        self._check_schema_pattern(inst, ctype)
        super().validate(inst, ctype)
        for m in inst.value:
            inst._member(m).validate(ctype)

    def from_raw(self, rval: RawObject) -> ObjectValue:
        """Override the superclass method."""
        res = ObjectValue()
        for qn in rval:
            cn = self._iname2qname(qn)
            ch = self.get_data_child(*cn)
            if ch is None:
                raise NonexistentSchemaNode(self, *cn)
            res[ch.iname()] = ch.from_raw(rval[qn])
        return res

    def _add_child(self, node: SchemaNode) -> None:
        node.parent = self
        self.children.append(node)

    def _child_inst_names(self) -> Set[InstanceName]:
        """Return the set of instance names under the receiver."""
        return frozenset([c.iname() for c in self.data_children()])

    def _check_schema_pattern(self, inst: "InstanceNode",
                             ctype: ContentType) -> None:
        """Match instance value against receiver's schema pattern.

        Args:
            inst: Instance node to be chancked.
            ctype: Content type of the instance.

        Raises:
            SchemaError: if `inst` doesn't match the schema pattern.
        """
        p = self.schema_pattern
        p._eval_when(inst)
        for m in inst.value:
            p = p.deriv(m, ctype)
            if isinstance(p, NotAllowed):
                raise SchemaError(inst, "not allowed: member {}{}".format(
                    m, ("" if ctype == ContentType.all else
                        " (" + ctype.name + ")")))
        if not p.nullable(ctype):
            raise SchemaError(inst, "missing: " + str(p))

    def _make_schema_patterns(self) -> None:
        """Build schema pattern for the receiver and its data descendants."""
        self.schema_pattern = self._schema_pattern()
        for dc in self.data_children():
            if isinstance(dc, InternalNode):
                dc._make_schema_patterns()

    def _schema_pattern(self) -> SchemaPattern:
        todo = [c for c in self.children
                if not isinstance(c, (RpcActionNode, NotificationNode))]
        if not todo: return Empty()
        prev = todo[0]._pattern_entry()
        for c in todo[1:]:
            prev = Pair(c._pattern_entry(), prev)
        return ConditionalPattern(prev, self.when) if self.when else prev

    def _post_process(self) -> None:
        super()._post_process()
        for c in self.children:
            c._post_process()

    def _add_mandatory_child(self, node: SchemaNode) -> None:
        """Add `node` to the set of mandatory children."""
        self._mandatory_children.add(node)

    def _add_defaults(self, inst: "InstanceNode", ctype: ContentType,
                      lazy: bool = False) -> "InstanceNode":
        for c in self.filter_children(ctype):
            if isinstance(c, DataNode):
                inst = c._default_instance(inst, ctype, lazy)
            elif not isinstance(c, (RpcActionNode, NotificationNode)):
                inst = c._add_defaults(inst, ctype)
        return inst

    def _state_roots(self) -> List[SchemaNode]:
        if self.content_type() == ContentType.nonconfig:
            return [self]
        res = []
        for c in self.data_children():
            res.extend(c._state_roots())
        return res

    def _handle_child(
            self, node: SchemaNode, stmt: Statement, mid: ModuleId) -> None:
        """Add child node to the receiver and handle substatements."""
        if not Context.if_features(stmt, mid): return
        node.name = stmt.argument
        node.ns = self._new_ns if self._new_ns else self.ns
        self._add_child(node)
        node._handle_substatements(stmt, mid)

    def _augment_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle **augment** statement."""
        if not Context.if_features(stmt, mid): return
        path = Context.sni2route(stmt.argument, mid)
        target = self.get_schema_descendant(path)
        if stmt.find1("when"):
            gr = GroupNode()
            target._add_child(gr)
            target = gr
        myns = Context.namespace(mid)
        target._new_ns = None if target.ns == myns else myns
        target._handle_substatements(stmt, mid)

    def _refine_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle **refine** statement."""
        target = self.get_schema_descendant(
            Context.sni2route(stmt.argument, mid))
        if not Context.if_features(stmt, mid):
            target.parent.children.remove(target)
        else:
            target._handle_substatements(stmt, mid)

    def _uses_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle uses statement."""
        if not Context.if_features(stmt, mid): return
        grp, gid = Context.get_definition(stmt, mid)
        if stmt.find1("when"):
            sn = GroupNode()
            self._add_child(sn)
        else:
            sn = self
        sn._handle_substatements(grp, gid)
        for augst in stmt.find_all("augment"):
            sn._augment_stmt(augst, mid)
        for refst in stmt.find_all("refine"):
            sn._refine_stmt(refst, mid)

    def _container_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle container statement."""
        self._handle_child(ContainerNode(), stmt, mid)

    def _identity_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle identity statement."""
        if not Context.if_features(stmt, mid): return
        bases = stmt.find_all("base")
        Context.identity_bases[
            (stmt.argument, Context.namespace(mid))] = set(
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
        node.type = DataType._resolve_type(
            stmt.find1("type", required=True), mid)
        self._handle_child(node, stmt, mid)

    def _leaf_list_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle leaf-list statement."""
        node = LeafListNode()
        node.type = DataType._resolve_type(
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

    def _ascii_tree(self, indent: str) -> str:
        """Return the receiver's subtree as ASCII art."""
        if not self.children: return ""
        cs = []
        for c in self.children:
            cs.extend(c._flatten())
        cs.sort(key=lambda x: x.qual_name)
        res = ""
        for c in cs[:-1]:
            res += (indent + c._tree_line() + "\n" +
                    c._ascii_tree(indent + "|  "))
        return (res + indent + cs[-1]._tree_line() + "\n" +
                cs[-1]._ascii_tree(indent + "   "))

class GroupNode(InternalNode):
    """Anonymous group of schema nodes."""

    def state_roots(self) -> List[DataPath]:
        """Override superclass method."""
        return []

    def _state_roots(self) -> List[SchemaNode]:
        return []

    def _handle_child(self, node: SchemaNode, stmt: Statement,
                     mid: ModuleId) -> None:
        if not isinstance(self.parent, ChoiceNode) or isinstance(node, CaseNode):
            super()._handle_child(node, stmt, mid)
        else:
            cn = CaseNode()
            cn.name = stmt.argument
            cn.ns = self._new_ns if self._new_ns else self.ns
            self._add_child(cn)
            cn._handle_child(node, stmt, mid)

    def _pattern_entry(self) -> SchemaPattern:
        return super()._schema_pattern()

    def _flatten(self) -> List[SchemaNode]:
        res = []
        for c in self.children:
            res.extend(c._flatten())
        return res

class DataNode(SchemaNode):
    """Abstract superclass for all data nodes."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self.default_deny = DefaultDeny.none # type: "DefaultDeny"

    def validate(self, inst: "InstanceNode", ctype: ContentType) -> None:
        """Extend the superclass method."""
        self._check_must(inst)
        super().validate(inst, ctype)

    def _default_instance(self, pnode: "InstanceNode", ctype: ContentType,
                          lazy: bool = False) -> "InstanceNode":
        iname = self.iname()
        if iname in pnode.value: return pnode
        nm = pnode.put_member(iname, (None,))
        if not self.when or self.when.evaluate(nm):
            wd = self._default_value(nm, ctype, lazy)
            if wd.value is not None:
                return wd.up()
        return pnode

    def _check_must(self, inst: "InstanceNode") -> None:
        """Check that all receiver's "must" constraints for the instance.

        Args:
            inst: Instance node to be checked.

        Raises:
            SemanticError: If a "must" expression evaluates to ``False``.
        """
        for mex in self.must:
            if not mex[0].evaluate(inst):
                msg = "'must' expression is false" if mex[1] is None else mex[1]
                raise SemanticError(inst, msg)

    def _pattern_entry(self) -> SchemaPattern:
        m = Member(self.iname(), self.content_type(), self.when)
        return m if self.mandatory else SchemaPattern.optional(m)

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + (
            "ro" if self.content_type() == ContentType.nonconfig else "rw")

    def _nacm_default_deny_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Set NACM default access."""
        if stmt.keyword == "default-deny-all":
            self.default_deny = DefaultDeny.all
        elif stmt.keyword == "default-deny-write":
            self.default_deny = DefaultDeny.write

class TerminalNode(SchemaNode):
    """Abstract superclass for terminal nodes in the schema tree."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self.type = None # type: DataType
        self._default = None # type: Optional[Value]

    def content_type(self) -> ContentType:
        """Override superclass method."""
        if self._ctype:
            return self._ctype
        return (ContentType.config if self.parent.config else
                ContentType.nonconfig)

    def validate(self, inst: "InstanceNode", ctype: ContentType) -> None:
        """Extend the superclass method."""
        self._check_type(inst)
        super().validate(inst, ctype)

    def from_raw(self, rval: RawScalar) -> ScalarValue:
        """Override the superclass method."""
        return self.type.from_raw(rval)

    def _default_value(self, inst: "InstanceNode", ctype: ContentType,
                       lazy: bool) -> "InstanceNode":
        inst.value = self.default
        return inst

    def _check_type(self, inst: "InstanceNode"):
        """Check whether receiver's type matches the instance value.

        Args:
            inst: Instance node to be checked.

        Raises:
            SchemaError: If the instance value doesn't match the type.
            SemanticError: If the instance violates referential integrity.
        """
        if not self.type.contains(inst.value):
            raise SchemaError(inst, "invalid type: " + repr(inst.value))
        if (isinstance(self.type, LinkType) and self.type.require_instance and
            not inst._deref()):
            raise SemanticError(inst, "required instance missing")

    def _post_process(self) -> None:
        super()._post_process()
        if isinstance(self.type, LeafrefType):
            ref = self._follow_leafref(self.type.path)
            if ref is None:
                raise BadLeafrefPath(self)
            self.type.ref_type = ref.type

    def _is_identityref(self) -> bool:
        return isinstance(self.type, IdentityrefType)

    def _default_nodes(self, inst: "InstanceNode") -> List["InstanceNode"]:
        di = self._default_instance(inst, ContentType.all)
        return [] if di is None else [self]
        return inst.put_member(self.iname(), dflt)._node_set()

    def _ascii_tree(self, indent: str) -> str:
        return ""

    def _state_roots(self) -> List[SchemaNode]:
        return [] if self.content_type() == ContentType.config else [self]

class ContainerNode(DataNode, InternalNode):
    """Container node."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self.presence = False # type: bool

    @property
    def mandatory(self) -> bool:
        """Is the receiver a mandatory node?"""
        return not self.presence and super().mandatory

    def _add_mandatory_child(self, node: SchemaNode):
        if not (self.presence or self.mandatory):
            self.parent._add_mandatory_child(self)
        super()._add_mandatory_child(node)

    def _default_instance(self, pnode: "InstanceNode", ctype: ContentType,
                          lazy: bool = False) -> "InstanceNode":
        if self.presence:
            return pnode
        return super()._default_instance(pnode, ctype, lazy)

    def _default_value(self, inst: "InstanceNode", ctype: ContentType,
                       lazy: bool) -> Optional["InstanceNode"]:
        inst.value = ObjectValue()
        return inst if lazy else self._add_defaults(inst, ctype)

    def _default_nodes(self, inst: "InstanceNode") -> List["InstanceNode"]:
        if self.presence: return []
        res = inst.put_member(self.iname(), ObjectValue())
        if self.when is None or self.when.evaluate(res):
            return [res]
        return []

    def _presence_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.presence = True

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return super()._tree_line() + ("!" if self.presence else "")

class SequenceNode(DataNode):
    """Abstract class for data nodes that represent a sequence."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self.min_elements = 0 # type: int
        self.max_elements = None # type: Optional[int]
        self.user_ordered = False # type: bool

    @property
    def mandatory(self) -> bool:
        """Is the receiver a mandatory node?"""
        return self.min_elements > 0

    def validate(self, inst: "InstanceNode", ctype: ContentType) -> None:
        """Extend the superclass method."""
        if isinstance(inst, ArrayEntry):
            super().validate(inst, ctype)
        elif isinstance(inst.value, ArrayValue):
            self._check_list_props(inst)
            self._check_cardinality(inst)
            for e in inst:
                super().validate(e, ctype)
        else:
            raise SchemaError(inst, "non-array value")

    def _check_cardinality(self, inst: "InstanceNode") -> None:
        """Check that the instance satisfies cardinality constraints.

        Args:
            inst: Instance node to be checked.

        Raises:
            SchemaError: It the cardinality of `inst` isn't correct.
        """
        if len(inst.value) < self.min_elements:
            raise SemanticError(inst,
                              "number of entries < min-elements ({})".format(
                                  self.min_elements))
        if (self.max_elements is not None and
            len(inst.value) > self.max_elements):
            raise SemanticError(inst,
                              "number of entries > max-elements ({})".format(
                                  self.max_elements))

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

    def _tree_line(self) -> str:
        """Extend the superclass method."""
        return super()._tree_line() + "*"

    def from_raw(self, rval: RawList) -> ArrayValue:
        """Override the superclass method."""
        res = ArrayValue()
        for en in rval:
            res.append(self.entry_from_raw(en))
        return res

    def entry_from_raw(self, rval: RawEntry) -> EntryValue:
        """Transform a raw (leaf-)list entry into the cooked form.

        Args:
            rval: raw entry (scalar or object)

        Raises:
            NonexistentSchemaNode: If a member inside `rval` is not defined
                in the schema.
            YangTypeError: If a scalar value inside `rval` is of incorrect type.
        """
        return super().from_raw(rval)

class ListNode(SequenceNode, InternalNode):
    """List node."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self.keys = [] # type: List[QualName]
        self._key_members = []
        self.unique = [] # type: List[List[SchemaRoute]]

    def _check_list_props(self, inst: "InstanceNode") -> None:
        """Check uniqueness of keys and "unique" properties, if applicable."""
        if self.keys:
            self._check_keys(inst)
        for u in self.unique:
            self._check_unique(u, inst)

    def _check_keys(self, inst: "InstanceNode") -> None:
        ukeys = set()
        for i in range(len(inst.value)):
            en = inst.value[i]
            try:
                kval = tuple([en[k] for k in self._key_members])
            except KeyError as e:
                raise SchemaError(
                    inst._entry(i),
                    "missing list key '{}'".format(e.args[0])) from None
            if kval in ukeys:
                raise SchemaError(inst, "non-unique list key: " + repr(kval))
            ukeys.add(kval)

    def _check_unique(self, unique: List[SchemaRoute],
                          inst: "InstanceNode") -> None:
        uvals = set()
        for en in inst:
            den = en.add_defaults()
            uval = tuple([den._peek_schema_route(sr) for sr in unique])
            if None not in uval:
                if uval in uvals:
                    raise SemanticError(inst, "unique constraint violated")
                else:
                    uvals.add(uval)

    def _default_instance(self, pnode: "InstanceNode", ctype: ContentType,
                          lazy: bool = False) -> "InstanceNode":
        return pnode

    def _post_process(self) -> None:
        super()._post_process()
        for k in self.keys:
            kn = self.get_data_child(*k)
            self._key_members.append(kn.iname())
            if not kn._mandatory:
                kn._mandatory = True
                self._mandatory_children.add(kn)

    def _key_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.keys = []
        for k in stmt.argument.split():
            self.keys.append(Context.translate_pname(k, mid) if ":" in k
                             else (k, self.ns))

    def _unique_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.unique.append(
            [Context.sni2route(sid, mid) for sid in stmt.argument.split()])

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        keys = (" [" + " ".join([ k[0] for k in self.keys ]) + "]"
                if self.keys else "")
        return super()._tree_line() + keys

class ChoiceNode(InternalNode):
    """Choice node."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self.default_case = None # type: QualName
        self._mandatory = False # type: bool

    @property
    def mandatory(self) -> bool:
        """Is the receiver a mandatory node?"""
        return self._mandatory

    def _add_defaults(self, inst: "InstanceNode",
                      ctype: ContentType) -> "InstanceNode":
        if self.when and not self.when.evaluate(inst):
            return inst
        ac = self._active_case(inst.value)
        if ac:
            return ac._add_defaults(inst, ctype)
        elif self.default_case:
            n = dc = self.get_child(*self.default_case)
            while n is not self:
                if n.when and not n.when.evaluate(inst):
                    return inst
                n = n.parent
            return dc._add_defaults(inst, ctype)
        else:
            return inst

    def _active_case(self, value: ObjectValue) -> Optional["CaseNode"]:
        """Return receiver's case that's active in an instance node value."""
        for c in self.children:
            for cc in c.data_children():
                if cc.iname() in value:
                    return c

    def _pattern_entry(self) -> SchemaPattern:
        if not self.children:
            return Empty()
        prev = self.children[0]._schema_pattern()
        for c in self.children[1:]:
            prev = ChoicePattern(c._schema_pattern(), prev, self.name)
        prev.ctype = self.content_type()
        if not self.mandatory:
            prev = SchemaPattern.optional(prev)
        return ConditionalPattern(prev, self.when) if self.when else prev

    def _post_process(self) -> None:
        super()._post_process()
        if self._mandatory:
            self.parent._add_mandatory_child(self)

    def _config_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        if stmt.argument == "false":
            self._ctype = ContentType.nonconfig

    def _default_nodes(self, inst: "InstanceNode") -> List["InstanceNode"]:
        res = []
        if self.default_case is None: return res
        for cn in self.get_child(*self.default_case).children:
            res.extend(cn._default_nodes(inst))
        return res

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + (
            "ro" if self.content_type() == ContentType.nonconfig else "rw")

    def _handle_child(self, node: SchemaNode, stmt: Statement,
                     mid: ModuleId) -> None:
        if isinstance(node, CaseNode):
            super()._handle_child(node, stmt, mid)
        else:
            cn = CaseNode()
            cn.name = stmt.argument
            cn.ns = self._new_ns if self._new_ns else self.ns
            self._add_child(cn)
            cn._handle_child(node, stmt, mid)

    def _default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self.default_case = Context.translate_pname(stmt.argument, mid)

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{} ({}){}".format(
            self._tree_line_prefix(), self.iname(),
            "" if self._mandatory else "?")

class CaseNode(InternalNode):
    """Case node."""

    def _pattern_entry(self) -> SchemaPattern:
        return super()._schema_pattern()

    def _tree_line(self) -> str:
        """Return the receiver's contribution to tree diagram."""
        return "{}:({})".format(
            self._tree_line_prefix(), self.iname())

class LeafNode(DataNode, TerminalNode):
    """Leaf node."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self._mandatory = False # type: bool

    @property
    def mandatory(self) -> bool:
        """Is the receiver a mandatory node?"""
        return self._mandatory

    @property
    def default(self) -> Optional[ScalarValue]:
        """Default value of the receiver, if any."""
        if self.mandatory: return None
        if self._default is not None: return self._default
        return self.type.default

    def _post_process(self) -> None:
        super()._post_process()
        if self._mandatory:
            self.parent._add_mandatory_child(self)

    def _tree_line(self) -> str:
        return super()._tree_line() + ("" if self._mandatory else "?")

    def _default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        self._default = self.type.from_yang(stmt.argument, mid)

class LeafListNode(SequenceNode, TerminalNode):
    """Leaf-list node."""

    @property
    def default(self) -> Optional[ScalarValue]:
        """Default value of the receiver, if any."""
        if self.mandatory: return None
        if self._default is not None: return self._default
        return (None if self.type.default is None
                else ArrayValue([self.type.default]))

    def _check_list_props(self, inst: "InstanceNode") -> None:
        if (self.content_type() == ContentType.config and
            len(set(inst.value)) < len(inst.value)):
            raise SemanticError(inst, "non-unique leaf-list values")

    def _default_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        val = self.type.parse_value(stmt.argument)
        if self._default is None:
            self._default = ArrayValue([val])
        else:
            self._default.append(val)

class AnydataNode(DataNode):
    """Anydata or anyxml node."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self._mandatory = False # type: bool

    def content_type(self) -> ContentType:
        """Override superclass method."""
        return TerminalNode.content_type(self)

    @property
    def mandatory(self) -> bool:
        """Is the receiver a mandatory node?"""
        return self._mandatory

    def from_raw(self, rval: RawValue) -> Value:
        """Override the superclass method."""
        def convert(val):
            if isinstance(val, list):
                res = ArrayValue([convert(x) for x in val])
            elif isinstance(val, dict):
                res = ObjectValue({ x:convert(val[x]) for x in val })
            else:
                res = val
            return res
        return convert(rval)

    def _default_instance(self, pnode: "InstanceNode", ctype: ContentType,
                          lazy: bool = False) -> "InstanceNode":
        return pnode

    def _tree_line(self) -> str:
        return super()._tree_line() + ("" if self._mandatory else "?")

    def _ascii_tree(self, indent: str) -> str:
        return ""

    def _post_process(self) -> None:
        if self._mandatory:
            self.parent._add_mandatory_child(self)

class RpcActionNode(GroupNode):
    """RPC or action node."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self._ctype = ContentType.nonconfig

    def _handle_substatements(self, stmt: Statement, mid: ModuleId) -> None:
        self._add_child(InputNode(self.ns))
        self._add_child(OutputNode(self.ns))
        super()._handle_substatements(stmt, mid)

    def _flatten(self) -> List[SchemaNode]:
        return [self]

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + "-x"

    def _input_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle RPC or action input statement."""
        self.get_child("input")._handle_substatements(stmt, mid)

    def _output_stmt(self, stmt: Statement, mid: ModuleId) -> None:
        """Handle RPC or action output statement."""
        self.get_child("output")._handle_substatements(stmt, mid)

class InputNode(GroupNode):
    """RPC or action input node."""

    def __init__(self, ns):
        """Initialize the class instance."""
        super().__init__()
        self._config = False
        self.name = "input"
        self.ns = ns

    def _flatten(self) -> List[SchemaNode]:
        return [self]

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + "ro"

class OutputNode(GroupNode):
    """RPC or action output node."""

    def __init__(self, ns):
        """Initialize the class instance."""
        super().__init__()
        self._config = False
        self.name = "output"
        self.ns = ns

    def _flatten(self) -> List[SchemaNode]:
        return [self]

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + "ro"

class NotificationNode(GroupNode):
    """Notification node."""

    def __init__(self):
        """Initialize the class instance."""
        super().__init__()
        self._ctype = ContentType.nonconfig

    def _flatten(self) -> List[SchemaNode]:
        return [self]

    def _tree_line_prefix(self) -> str:
        return super()._tree_line_prefix() + "-n"

class SchemaNodeException(YangsonException):
    """Abstract exception class for schema node errors."""

    def __init__(self, sn: SchemaNode):
        self.schema_node = sn

    def __str__(self) -> str:
        return str(self.schema_node.qual_name)

class NonexistentSchemaNode(SchemaNodeException):
    """A schema node doesn't exist."""

    def __init__(self, sn: SchemaNode, name: YangIdentifier,
                 ns: YangIdentifier = None):
        super().__init__(sn)
        self.name = name
        self.ns = ns

    def __str__(self) -> str:
        loc = ("under " + super().__str__() if self.schema_node.parent
                   else "top level")
        return loc + " – name '{}', namespace '{}'".format(self.name, self.ns)

class BadSchemaNodeType(SchemaNodeException):
    """A schema node is of a wrong type."""

    def __init__(self, sn: SchemaNode, expected: str):
        super().__init__(sn)
        self.expected = expected

    def __str__(self) -> str:
        return super().__str__() + " is not a " + self.expected

class BadLeafrefPath(SchemaNodeException):
    """A leafref path is incorrect."""
    pass

class ValidationError(YangsonException):
    """Abstract exception class for instance validation errors."""

    def __init__(self, inst: "InstanceNode", detail: str):
        self.inst = inst
        self.detail = detail

    def __str__(self) -> str:
        return "[{}] {}".format(self.inst.json_pointer(), self.detail)

class SchemaError(ValidationError):
    """An instance violates a schema constraint."""
    pass

class SemanticError(ValidationError):
    """An instance violates a semantic rule."""
    pass

from .xpathast import Expr, LocationPath, Step, Root
from .instance import InstanceNode, ArrayEntry, NonexistentInstance
