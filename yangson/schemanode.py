# Copyright © 2016–2023 CZ.NIC, z. s. p. o.
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
# You should have received a copy of the GNU Lesser General Public License
# along with Yangson.  If not, see <http://www.gnu.org/licenses/>.

"""YANG schema nodes.

This module implements the following classes:

* SchemaNode: Abstract class for schema nodes.
* InternalNode: Abstract class for schema nodes that have children.
* GroupNode: Anonymous group of schema nodes.
* SchemaTreeNode: Root node of a schema tree.
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
* AnyContentNode: Abstract superclass for anydata and anyxml nodes..
* AnydataNode: YANG anydata node.
* AnyxmlNode: YANG anyxml node.
"""
from collections.abc import MutableSet
from datetime import datetime
from itertools import product
from typing import Any, Optional
import xml.etree.ElementTree as ET
from .constraint import Must
from .datatype import (DataType, LinkType,
                       RawScalar, IdentityrefType)
from .enumerations import (Axis, ContentType, DefaultDeny,
                           NodeStatus, ValidationScope)
from .exceptions import (
    AnnotationTypeError, InvalidArgument,
    MissingAnnotationTarget, MissingModuleNamespace, RawMemberError,
    RawTypeError, SchemaError, SemanticError, UndefinedAnnotation,
    YangsonException, YangTypeError)
from .instvalue import (
    ArrayValue, EntryValue, MetadataObject, ObjectValue, Value)
from .schemadata import IdentityAdjacency, SchemaContext, SchemaData
from .schpattern import (ChoicePattern, ConditionalPattern, Empty, Member,
                         NotAllowed, Pair, SchemaPattern)
from .statement import Statement
from .typealiases import (DataPath, InstanceName, JSONPointer, QualName,
                          RawEntry, RawList, RawObject, RawValue,
                          RawMetadataObject, ScalarValue, SchemaRoute,
                          YangIdentifier)
from .xpathast import Expr, LocationPath, Step, Root
from .xpathparser import XPathParser
from .instance import (ArrayEntry, EmptyList, InstanceNode,
                       InstanceRoute, MemberName, ObjectMember)


class Annotation:
    """Class for metadata annotations [RFC 7952]."""

    def __init__(self: "Annotation", type: DataType, description: str = None):
        """Initialize the class instance."""
        self.type = type
        self.description = description


class SchemaNode:
    """Abstract class for all schema nodes."""

    def __init__(self: "SchemaNode"):
        """Initialize the class instance."""
        self.name: Optional[YangIdentifier] = None
        """Name of the receiver."""
        self.ns: Optional[YangIdentifier] = None
        """Namespace of the receiver."""
        self.parent: Optional["InternalNode"] = None
        """Parent schema node."""
        self.description: Optional[str] = None
        """Description of the receiver."""
        self.must: list[Must] = []
        """List of "must" expressions attached to the receiver."""
        self.when: Optional["Expr"] = None
        """Optional "when" expression that makes the receiver conditional."""
        self.val_count = 0
        self._ctype = None
        """Content type of the receiver."""
        self._status = None
        """Status of node definition."""

    @property
    def qual_name(self: "SchemaNode") -> QualName:
        """Qualified name of the receiver."""
        return (self.name, self.ns)

    @property
    def config(self: "SchemaNode") -> bool:
        """Does the receiver (also) represent configuration?"""
        return self.content_type().value & ContentType.config.value != 0

    @property
    def mandatory(self: "SchemaNode") -> bool:
        """Is the receiver a mandatory node in the complete data tree?"""
        return False

    @property
    def mandatory_config(self: "SchemaNode") -> bool:
        """Is the receiver mandatory node in a configuration?"""
        return self.mandatory and self.config

    @property
    def status(self: "SchemaNode") -> NodeStatus:
        """Return receiver's definition status."""
        return self._status if self._status else self.parent.status

    def delete(self: "SchemaNode") -> None:
        """Remove the receiver from the schema."""
        self.parent.children.remove(self)

    def schema_root(self: "SchemaNode") -> "SchemaTreeNode":
        """Return the root node of the receiver's schema."""
        sn = self
        while sn.parent:
            sn = sn.parent
        return sn

    def content_type(self: "SchemaNode") -> ContentType:
        """Return receiver's content type."""
        return self._ctype if self._ctype else self.parent.content_type()

    def data_parent(self: "SchemaNode") -> Optional["InternalNode"]:
        """Return the closest ancestor data node."""
        parent = self.parent
        while parent:
            if isinstance(parent, DataNode):
                return parent
            parent = parent.parent

    def iname(self: "SchemaNode") -> InstanceName:
        """Return the instance name corresponding to the receiver."""
        dp = self.data_parent()
        return (self.name if dp and self.ns == dp.ns
                else self.ns + ":" + self.name)

    def data_path(self: "SchemaNode") -> DataPath:
        """Return the receiver's data path."""
        dp = self.data_parent()
        return (dp.data_path() if dp else "") + "/" + self.iname()

    def state_roots(self: "SchemaNode") -> list[DataPath]:
        """Return a list of data paths to descendant state data roots."""
        return [r.data_path() for r in self._state_roots()]

    def from_raw(self: "SchemaNode", rval: RawValue, jptr: JSONPointer = "") -> Value:
        """Return instance value transformed from a raw value using receiver.

        Args:
            rval: Raw value.
            jptr: JSON pointer of the current instance node.

        Raises:
            RawMemberError: If a member inside `rval` is not defined in the
                schema.
            RawTypeError: If a scalar value inside `rval` is of incorrect type.
        """
        raise NotImplementedError

    def from_xml(self: "SchemaNode", rval: ET.Element, jptr: JSONPointer = "", isroot: bool = False) -> Value:
        """Return instance value transformed from a raw value using receiver.

        Args:
            rval: XML node.
            jptr: JSON pointer of the current instance node.

        Raises:
            RawMemberError: If a member inside `rval` is not defined in the
                schema.
            RawTypeError: If a scalar value inside `rval` is of incorrect type.
        """
        raise NotImplementedError

    def clear_val_counters(self: "SchemaNode") -> None:
        """Clear receiver's validation counter."""
        self.val_count = 0

    def _apply_deviate(self: "SchemaNode", stmt: Statement,
                       sctx: SchemaContext) -> None:
        """Apply **deviate** statement to the receiver."""
        arg = stmt.argument
        if arg == "not-supported":
            self.delete()
        else:
            for subst in stmt.substatements:
                try:
                    method = getattr(self, "_deviate_" +
                                     subst.keyword.replace("-", "_", 1))
                except AttributeError as error:
                    if subst.prefix:  # ignore unsupported extension
                        continue
                    raise error from None
                method(subst, sctx, action=arg)

    def _get_description(self: "SchemaNode", stmt: Statement):
        dst = stmt.find1("description")
        if dst is not None:
            self.description = dst.argument

    def _yang_class(self: "SchemaNode") -> str:
        return self.__class__.__name__[:-4].lower()

    def _node_digest(self: "SchemaNode") -> dict[str, Any]:
        """Return dictionary of receiver's properties suitable for clients."""
        res = {"kind": self._yang_class()}
        if self.mandatory:
            res["mandatory"] = True
        if self.description:
            res["description"] = self.description
        return res

    def _tree_name(self: "SchemaNode") -> str:
        """Return the receiver's name to be displayed in ASCII tree."""
        return (self.name if self.parent and self.ns == self.parent.ns
                 else f"{self.ns}:{self.name}")

    def _validate(self: "SchemaNode", inst: InstanceNode, scope: ValidationScope,
                  ctype: ContentType) -> None:
        """Validate instance against the receiver.

        Args:
            inst: Instance node to be validated.
            scope: Scope of the validation (syntax, semantics or all)
            ctype: Content type of the instance.

        Returns:
            ``None`` if validation succeeds.

        Raises:
            SchemaError: if `inst` doesn't conform to the schema.
            SemanticError: If `inst` violates a semantic rule.
            YangTypeError: If `inst` is a scalar of incorrect type.
        """
        self.val_count += 1

    def _iname2qname(self: "SchemaNode", iname: InstanceName) -> QualName:
        """Translate instance name to qualified name in the receiver's context.
        """
        p, s, loc = iname.partition(":")
        return (loc, p) if s else (p, self.ns)

    def _flatten(self: "SchemaNode") -> list["SchemaNode"]:
        return [self]

    def _handle_substatements(self: "SchemaNode", stmt: Statement,
                              sctx: SchemaContext) -> None:
        """Dispatch actions for substatements of `stmt`."""
        for s in stmt.substatements:
            if s.prefix:
                key = (
                    sctx.schema_data.modules[sctx.text_mid].prefix_map[s.prefix][0]
                    + ":" + s.keyword)
            else:
                key = s.keyword
            mname = SchemaNode._stmt_callback.get(key, "_noop")
            method = getattr(self, mname)
            method(s, sctx)

    def _follow_leafref(
            self: "SchemaNode", xpath: Expr, init: "TerminalNode") -> Optional["DataNode"]:
        """Return the data node referred to by a leafref path.

        Args:
            xpath: XPath expression compiled from a leafref path.
            init: initial context node
        """
        if isinstance(xpath, LocationPath):
            lft = self._follow_leafref(xpath.left, init)
            if lft is None:
                return None
            return lft._follow_leafref(xpath.right, init)
        elif isinstance(xpath, Step):
            if xpath.axis == Axis.parent:
                if isinstance(self, SchemaTreeNode):
                    return None
                return self.data_parent() or self.schema_root()
            elif xpath.axis == Axis.child:
                if isinstance(self, InternalNode) and xpath.qname:
                    qname = (xpath.qname if xpath.qname[1]
                             else (xpath.qname[0], init.ns))
                    return self.get_data_child(*qname)
        elif isinstance(xpath, Root):
            return self.schema_root()
        return None

    def _noop(self: "SchemaNode", stmt: Statement, sctx: SchemaContext) -> None:
        pass

    def _config_stmt(self: "SchemaNode", stmt: Statement,
                     sctx: SchemaContext) -> None:
        if stmt.argument == "false":
            self._ctype = ContentType.nonconfig

    def _status_stmt(self: "SchemaNode", stmt: Statement,
                     sctx: SchemaContext) -> None:
        if stmt.argument == "deprecated":
            nst = NodeStatus.deprecated
        elif stmt.argument == "obsolete":
            nst = NodeStatus.obsolete
        else:
            nst = NodeStatus.current
        if nst != self.parent.status:
            self._status = nst

    def _deviate_config(self: "SchemaNode", stmt: Statement,
                         sctx: SchemaContext, action: str) -> None:
        if action == "delete":
            self._ctype = None
        elif action in ("add", "replace"):
            self._config_stmt(stmt, sctx)

    def _description_stmt(self: "SchemaNode", stmt: Statement,
                          sctx: SchemaContext) -> None:
        self.description = stmt.argument

    def _must_stmt(self: "SchemaNode", stmt: Statement,
                   sctx: SchemaContext) -> None:
        xpp = XPathParser(stmt.argument, sctx)
        mex = xpp.parse()
        if not xpp.at_end():
            raise InvalidArgument(stmt.argument)
        self.must.append(Must(mex, *stmt.get_error_info()))

    def _deviate_must(self: "SchemaNode", stmt: Statement,
                      sctx: SchemaContext, action: str) -> None:
        if action in ("add", "replace"):
            if action == "replace":
                self.must = []
            self._must_stmt(stmt, sctx)
        elif action == "delete":
            mstr = str(XPathParser(stmt.argument, sctx).parse())
            for i in range(len(self.must)):
                if str(self.must[i].expression) == mstr:
                    del self.must[i]
                    return

    def _when_stmt(self: "SchemaNode", stmt: Statement,
                   sctx: SchemaContext) -> None:
        xpp = XPathParser(stmt.argument, sctx)
        wex = xpp.parse()
        if not xpp.at_end():
            raise InvalidArgument(stmt.argument)
        self.when = wex

    def _mandatory_stmt(self: "SchemaNode", stmt,
                        sctx: SchemaContext) -> None:
        if stmt.argument == "true":
            self._mandatory = True
        elif stmt.argument == "false":
            self._mandatory = False

    def _deviate_mandatory(self: "SchemaNode", stmt: Statement,
                         sctx: SchemaContext, action: str) -> None:
        if action == "delete":
            self._mandatory = False
        elif action in ("add", "replace"):
            self._mandatory_stmt(stmt, sctx)

    def _post_process(self: "SchemaNode") -> None:
        pass

    def _is_identityref(self: "SchemaNode") -> bool:
        return False

    def _tree_line(self: "SchemaNode", no_type: bool = False) -> str:
        """Return the receiver's contribution to tree diagram."""
        return f"{self._tree_line_prefix()} {self._tree_name()}"

    def _tree_line_prefix(self: "SchemaNode") -> str:
        return self.status.value + "--"

    def _nacm_default_deny_stmt(self: "SchemaNode", stmt: Statement,
                                sctx: SchemaContext) -> None:
        """Set NACM default access."""
        if not hasattr(self, 'default_deny'):
            return
        if stmt.keyword == "default-deny-all":
            self.default_deny = DefaultDeny.all
        elif stmt.keyword == "default-deny-write":
            self.default_deny = DefaultDeny.write

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
        "ietf-yang-metadata:annotation": "_annotation_stmt",
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
        "status": "_status_stmt",
        "unique": "_unique_stmt",
        "units": "_units_stmt",
        "uses": "_uses_stmt",
        "when": "_when_stmt",
    }
    """Map of statement keywords to callback methods."""


class InternalNode(SchemaNode):
    """Abstract class for schema nodes that have children."""

    _mandatory_children: tuple[MutableSet[SchemaNode], MutableSet[SchemaNode]]
    """Two sets of mandatory children: item 0 = nonconfig, 1 = config."""

    def __init__(self: "InternalNode"):
        """Initialize the class instance."""
        super().__init__()
        self.children: list[SchemaNode] = []
        self.schema_pattern: Optional[SchemaPattern] = None
        self._mandatory_children = (set(), set())

    @property
    def mandatory(self: "InternalNode") -> bool:
        """Override the superclass property."""
        return bool(self._mandatory_children[0] or
                    self._mandatory_children[1])

    def get_child(self: "InternalNode", name: YangIdentifier,
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
            grandchild = c.get_child(name, ns)
            if grandchild is not None:
                return grandchild

    def get_schema_descendant(
            self: "InternalNode", route: SchemaRoute) -> Optional[SchemaNode]:
        """Return descendant schema node or ``None`` if not found.

        Args:
            route: Schema route to the descendant node
                   (relative to the receiver).
        """
        node = self
        for p in route:
            try:
                node = node.get_child(*p)
            except AttributeError:
                return None
            if node is None:
                return None
        return node

    def get_data_child(self: "InternalNode", name: YangIdentifier,
                       ns: YangIdentifier = None) -> Optional["DataNode"]:
        """Return data node directly under the receiver."""
        ns = ns if ns else self.ns
        todo = []
        for child in self.children:
            if child.name == name and child.ns == ns:
                if isinstance(child, DataNode):
                    return child
                todo.insert(0, child)
            elif not isinstance(child, DataNode):
                todo.append(child)
        for c in todo:
            res = c.get_data_child(name, ns)
            if res:
                return res

    def filter_children(self: "InternalNode", ctype: ContentType = None) -> list[SchemaNode]:
        """Return receiver's children based on content type.

        Args:
            ctype: Content type.
        """
        if ctype is None:
            ctype = self.content_type()
        return [c for c in self.children if
                not isinstance(c, (RpcActionNode, NotificationNode)) and
                c.content_type().value & ctype.value != 0]

    def data_children(self: "InternalNode") -> list["DataNode"]:
        """Return the set of all data nodes directly under the receiver."""
        res = []
        for child in self.children:
            if isinstance(child, DataNode):
                res.append(child)
            elif not isinstance(child, SchemaTreeNode):
                res.extend(child.data_children())
        return res

    def from_raw(self: "InternalNode", rval: RawObject, jptr: JSONPointer = "") -> ObjectValue:
        """Override the superclass method."""
        if not isinstance(rval, dict):
            raise RawTypeError(jptr, "object")
        res = ObjectValue()
        for qn in rval:
            if qn.startswith("@"):
                if qn != "@":
                    tgt = qn[1:]
                    if tgt not in rval:
                        raise MissingAnnotationTarget(jptr, tgt)
                    jptr += '/' + tgt
                res[qn] = self._process_metadata(rval[qn], jptr)
            else:
                cn = self._iname2qname(qn)
                ch = self.get_data_child(*cn)
                if jptr == "" and ch is None:
                    ch = self.get_child(*cn)
                    if not isinstance(ch, SchemaTreeNode):
                        ch = None
                npath = jptr + "/" + qn
                if ch is None:
                    raise RawMemberError(npath)
                if jptr == "" or self.ns != ch.ns:
                    iname = '{1}:{0}'.format(*ch.qual_name)
                else:
                    iname = ch.name
                res[iname] = ch.from_raw(rval[qn], npath)
        return res

    def from_xml(self: "InternalNode", rval: ET.Element, jptr: JSONPointer = "") -> ObjectValue:
        res = ObjectValue()
        if isinstance(self, RpcActionNode) and jptr == "":
            self._process_xmlobj_child(res, None, rval, jptr)
        else:
            for xmlchild in rval:
                self._process_xmlobj_child(res, rval, xmlchild, jptr)
        return res

    def _process_xmlobj_child(
            self: "InternalNode", res: ObjectValue, rval: ET.Element,
            xmlchild: ET.Element, jptr: JSONPointer):
        if xmlchild.tag[0] == '{':
            xmlns, name = xmlchild.tag[1:].split('}')
            nsmap = self.schema_root().schema_data.modules_by_ns
            if xmlns not in nsmap:
                raise MissingModuleNamespace(xmlns)
            ns = nsmap[xmlns].yang_id[0]
            fqn = ns + ':' + name
        else:
            name = xmlchild.tag
            ns = self.ns
            fqn = ns + ':' + name
        qn = fqn if ns != self.ns else name

        ch = self.get_data_child(name, ns)
        if jptr == "" and ch is None:
            ch = self.get_child(name, ns)
            if not isinstance(ch, SchemaTreeNode):
                ch = None
        npath = jptr + "/" + qn
        if ch is None:
            raise RawMemberError(npath)

        if rval is not None and self.ns == ch.ns:
            iname = ch.name
        else:
            iname = '{1}:{0}'.format(*ch.qual_name)
        if isinstance(ch, SequenceNode):
            if iname not in res:
                res[iname] = ch.from_xml(rval, npath, fqn)
        else:
            res[iname] = ch.from_xml(xmlchild, npath)

    def _process_metadata(self: "InternalNode", rmo: RawMetadataObject,
                          jptr: JSONPointer) -> MetadataObject:
        res = {}
        ans = self.schema_root().annotations
        for mem in rmo:
            try:
                an = ans[self._iname2qname(mem)]
            except KeyError:
                raise UndefinedAnnotation(jptr, mem)
            res[mem] = an.type.from_raw(rmo[mem])
            if res[mem] not in an.type:
                raise AnnotationTypeError(jptr, mem, an.type.error_message)
        return res

    def _node_digest(self: "InternalNode") -> dict[str, Any]:
        res = super()._node_digest()
        rc = res["children"] = {}
        for c in self.data_children():
            cdig = rc[c.iname()] = c._node_digest()
            if self.config and not c.config:
                cdig["config"] = False
        for c in [c for c in self.children if isinstance(c, SchemaTreeNode)]:
            rc[c.iname()] = c._node_digest()
        return res

    def _validate(self: "InternalNode", inst: InstanceNode, scope: ValidationScope,
                  ctype: ContentType) -> None:
        """Extend the superclass method."""
        if scope.value & ValidationScope.syntax.value:   # schema
            self._check_schema_pattern(inst, ctype)
        for m in inst:
            inst._member(m).validate(scope, ctype)
        super()._validate(inst, scope, ctype)

    def _add_child(self: "InternalNode", node: SchemaNode) -> None:
        node.parent = self
        self.children.append(node)

    def _child_inst_names(self: "InternalNode") -> set[InstanceName]:
        """Return the set of instance names under the receiver."""
        return frozenset([c.iname() for c in self.data_children()])

    def _check_schema_pattern(self: "InternalNode", inst: InstanceNode,
                              ctype: ContentType) -> None:
        p = self.schema_pattern
        p._eval_when(inst)
        for m in inst:
            newp = p.deriv(m, ctype)
            if isinstance(newp, NotAllowed):
                raise SchemaError(
                    inst,
                    ("" if ctype == ContentType.all else ctype.name + " ") +
                    "member-not-allowed", m)
            p = newp
        if not p.nullable(ctype):
            mms = p._mandatory_members(ctype)
            msg = "one of " if len(mms) > 1 else ""
            raise SchemaError(
                inst, "missing-data",
                "expected " + msg + ", ".join([repr(m) for m in mms]))

    def _make_schema_patterns(self: "InternalNode") -> None:
        """Build schema pattern for the receiver and its data descendants."""
        self.schema_pattern = self._schema_pattern()
        for dc in self.data_children():
            if isinstance(dc, InternalNode):
                dc._make_schema_patterns()

    def _schema_pattern(self: "InternalNode") -> SchemaPattern:
        todo = [c for c in self.children if not (
            isinstance(c, (RpcActionNode, NotificationNode)) or
            c._status == NodeStatus.obsolete)]
        if not todo:
            return Empty()
        prev = todo[0]._pattern_entry()
        for c in todo[1:]:
            prev = Pair(c._pattern_entry(), prev)
        return ConditionalPattern(prev, self.when) if self.when else prev

    def _post_process(self: "InternalNode") -> None:
        super()._post_process()
        for c in self.children:
            c._post_process()

    def _add_mandatory_child(self: "InternalNode", node: SchemaNode) -> None:
        """Add `node` to the set of mandatory children."""
        if node.mandatory_config:
            self._mandatory_children[1].add(node)
        else:
            self._mandatory_children[0].add(node)

    def _add_defaults(self: "InternalNode", inst: InstanceNode, ctype: ContentType,
                      lazy: bool = False) -> InstanceNode:
        for c in self.filter_children(ctype):
            if isinstance(c, DataNode):
                inst = c._default_instance(inst, ctype, lazy)
            elif not isinstance(c, (RpcActionNode, NotificationNode)):
                inst = c._add_defaults(inst, ctype)
        return inst

    def _state_roots(self: "InternalNode") -> list[SchemaNode]:
        if self.content_type() == ContentType.nonconfig:
            return [self]
        res = []
        for c in self.data_children():
            res.extend(c._state_roots())
        return res

    def _handle_child(self: "InternalNode", node: SchemaNode, stmt: Statement,
                      sctx: SchemaContext) -> None:
        """Add child node to the receiver and handle substatements."""
        if not sctx.schema_data.if_features(stmt, sctx.text_mid):
            return
        node.name = stmt.argument
        node.ns = sctx.default_ns
        node._get_description(stmt)
        self._add_child(node)
        node._handle_substatements(stmt, sctx)

    def _augment_stmt(self: "InternalNode", stmt: Statement,
                      sctx: SchemaContext) -> None:
        """Handle **augment** statement."""
        if not sctx.schema_data.if_features(stmt, sctx.text_mid):
            return
        target = self.get_schema_descendant(
            sctx.schema_data.sni2route(stmt.argument, sctx))
        if target is None:      # silently ignore missing target
            return
        if stmt.find1("when"):
            gr = GroupNode()
            target._add_child(gr)
            target = gr
        target._handle_substatements(stmt, sctx)

    def _deviation_stmt(self: "InternalNode", stmt: Statement,
                        sctx: SchemaContext) -> None:
        """Handle **deviation** statement."""
        target = self.get_schema_descendant(
            sctx.schema_data.sni2route(stmt.argument, sctx))
        if target is None:      # silently ignore missing target
            return
        for dstmt in stmt.find_all("deviate"):
            target._apply_deviate(dstmt, sctx)

    def _refine_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle **refine** statement."""
        target = self.get_schema_descendant(
            sctx.schema_data.sni2route(stmt.argument, sctx))
        if not target:
            return
        if not sctx.schema_data.if_features(stmt, sctx.text_mid):
            target.parent.children.remove(target)
        else:
            target._handle_substatements(stmt, sctx)

    def _uses_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle uses statement."""
        if not sctx.schema_data.if_features(stmt, sctx.text_mid):
            return
        grp, gid = sctx.schema_data.get_definition(stmt, sctx)
        wst = stmt.find1("when")
        if wst:
            sn = GroupNode()
            xpp = XPathParser(wst.argument, sctx)
            wex = xpp.parse()
            if not xpp.at_end():
                raise InvalidArgument(wst.argument)
            sn.when = wex
            self._add_child(sn)
        else:
            sn = self
        sn._handle_substatements(grp, gid)
        for augst in stmt.find_all("augment"):
            sn._augment_stmt(augst, sctx)
        for refst in stmt.find_all("refine"):
            sn._refine_stmt(refst, sctx)

    def _container_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle container statement."""
        self._handle_child(ContainerNode(), stmt, sctx)

    def _identity_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle identity statement."""
        if not sctx.schema_data.if_features(stmt, sctx.text_mid):
            return
        id = (stmt.argument, sctx.schema_data.namespace(sctx.text_mid))
        adj = sctx.schema_data.identity_adjs.setdefault(id, IdentityAdjacency())
        for bst in stmt.find_all("base"):
            bid = sctx.schema_data.translate_pname(bst.argument, sctx.text_mid)
            adj.bases.add(bid)
            badj = sctx.schema_data.identity_adjs.setdefault(
                bid, IdentityAdjacency())
            badj.derivs.add(id)
        sctx.schema_data.identity_adjs[id] = adj

    def _list_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle list statement."""
        self._handle_child(ListNode(), stmt, sctx)

    def _choice_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle choice statement."""
        self._handle_child(ChoiceNode(), stmt, sctx)

    def _case_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle case statement."""
        self._handle_child(CaseNode(), stmt, sctx)

    def _leaf_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle leaf statement."""
        node = LeafNode()
        node.type = DataType._resolve_type(
            stmt.find1("type", required=True), sctx)
        self._handle_child(node, stmt, sctx)

    def _leaf_list_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle leaf-list statement."""
        node = LeafListNode()
        node.type = DataType._resolve_type(
            stmt.find1("type", required=True), sctx)
        self._handle_child(node, stmt, sctx)

    def _rpc_action_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle rpc or action statement."""
        self._handle_child(RpcActionNode(), stmt, sctx)

    def _notification_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle notification statement."""
        self._handle_child(NotificationNode(), stmt, sctx)

    def _anydata_stmt(self: "InternalNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle anydata statement."""
        self._handle_child(AnydataNode(), stmt, sctx)

    def _ascii_tree(self: "InternalNode", indent: str, no_types: bool, val_count: bool) -> str:
        """Return the receiver's subtree as ASCII art."""
        def suffix(sn):
            return f" {{{sn.val_count}}}\n" if val_count else "\n"
        if not self.children:
            return ""
        cs = []
        for c in self.children:
            cs.extend(c._flatten())
        cs.sort(key=lambda x: x.qual_name)
        res = ""
        for c in cs[:-1]:
            res += (indent + c._tree_line(no_types) + suffix(c) +
                    c._ascii_tree(indent + "|  ", no_types, val_count))
        return (res + indent + cs[-1]._tree_line(no_types) + suffix(cs[-1]) +
                cs[-1]._ascii_tree(indent + "   ", no_types, val_count))

    def clear_val_counters(self: "InternalNode") -> None:
        """Clear validation counters in the receiver and its subtree."""
        super().clear_val_counters()
        for c in self.children:
            c.clear_val_counters()


class GroupNode(InternalNode):
    """Anonymous group of schema nodes."""

    def _handle_child(self: "GroupNode", node: SchemaNode, stmt: Statement,
                      sctx: SchemaContext) -> None:
        if not isinstance(
                self.parent, ChoiceNode) or isinstance(node, CaseNode):
            super()._handle_child(node, stmt, sctx)
        else:
            cn = CaseNode()
            cn.name = stmt.argument
            cn.ns = sctx.default_ns
            self._add_child(cn)
            cn._handle_child(node, stmt, sctx)

    def _pattern_entry(self: "GroupNode") -> SchemaPattern:
        return super()._schema_pattern()

    def _flatten(self: "GroupNode") -> list[SchemaNode]:
        res = []
        for c in self.children:
            res.extend(c._flatten())
        return res


class SchemaTreeNode(GroupNode):
    """Root node of a schema tree."""

    def __init__(self: "SchemaTreeNode", schemadata: SchemaData = None):
        """Initialize the class instance."""
        super().__init__()
        self.annotations: dict[QualName, Annotation] = {}
        self.schema_data = schemadata
        self._status = NodeStatus.current

    def iname(self: "SchemaTreeNode") -> InstanceName:
        """Override the superclass method."""
        return ""

    def data_parent(self: "SchemaTreeNode") -> None:
        """Override the superclass method."""
        return None

    def _annotation_stmt(self: "SchemaTreeNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle annotation statement."""
        if not sctx.schema_data.if_features(stmt, sctx.text_mid):
            return
        dst = stmt.find1("description")
        self.annotations[(stmt.argument, sctx.default_ns)] = Annotation(
            DataType._resolve_type(stmt.find1("type", required=True), sctx),
            dst.argument if dst else None)


class DataNode(SchemaNode):
    """Abstract superclass for all data nodes."""

    def __init__(self: "DataNode"):
        """Initialize the class instance."""
        super().__init__()
        self.default_deny: DefaultDeny = DefaultDeny.none

    def orphan_instance(self: "DataNode", rval: RawValue) -> "ObjectMember":
        """Return an isolated instance of the receiver.

        Args:
            rval: Raw value to be used for the returned instance.
        """
        val = self.from_raw(rval, jptr = "/")
        return ObjectMember(self.iname(), {}, val, None, self, datetime.now())

    def split_instance_route(self: "DataNode", route: InstanceRoute) -> Optional[tuple[InstanceRoute, InstanceRoute]]:
        """Split `route` into the part up to receiver and the rest.

        Args:
            route: Absolute instance route (the receiver should correspond
                to an instance node on this route).

        Returns:
            A tuple consisting of
                - the part of `route` from the root up to and including the
                  instance whose schema node is the receiver, and
                - the rest of `route`.
                ``None`` is returned if the receiver is not on the route.
        """
        sroute = []
        sn = self
        while sn:
            sroute.append(sn.iname())
            sn = sn.data_parent()
        i = 0
        while True:
            if not sroute:
                break
            inst = sroute.pop()
            if inst != route[i].iname():
                return None
            while True:         # skip up to next MemberName
                i += 1
                if i >= len(route) or isinstance(route[i], MemberName):
                    break
            if not sroute:
                return (InstanceRoute(route[:i]), InstanceRoute(route[i:]))
            if i >= len(route):
                return None

    def _validate(self: "DataNode", inst: InstanceNode, scope: ValidationScope,
                  ctype: ContentType) -> None:
        """Extend the superclass method."""
        if scope.value & ValidationScope.semantics.value:
            self._check_must(inst)        # must expressions
        super()._validate(inst, scope, ctype)

    def _default_instance(self: "DataNode", pnode: InstanceNode, ctype: ContentType,
                          lazy: bool = False) -> InstanceNode:
        iname = self.iname()
        if iname in pnode.value:
            return pnode
        nm = pnode.put_member(iname, (None,))
        if not self.when or self.when.evaluate(nm):
            wd = self._default_value(nm, ctype, lazy)
            if wd.value is not None:
                return wd.up()
        return pnode

    def _check_must(self: "DataNode", inst: InstanceNode) -> None:
        for m in self.must:
            if not m.expression.evaluate(inst):
                raise SemanticError(inst, m.error_tag, m.error_message)

    def _pattern_entry(self: "DataNode") -> SchemaPattern:
        m = Member(self.iname(), self.content_type(), self.when)
        return m if (self.mandatory and self._status !=
                     NodeStatus.deprecated) else SchemaPattern.optional(m)

    def _tree_line_prefix(self: "DataNode") -> str:
        return super()._tree_line_prefix() + (
            "ro" if self.content_type() == ContentType.nonconfig else "rw")


class TerminalNode(SchemaNode):
    """Abstract superclass for terminal nodes in the schema tree."""

    def __init__(self: "TerminalNode"):
        """Initialize the class instance."""
        super().__init__()
        self.type: DataType = None
        self._default: Optional[Value] = None
        self._units: Optional[str] = None

    def content_type(self: "TerminalNode") -> ContentType:
        """Override superclass method."""
        if self._ctype:
            return self._ctype
        return (ContentType.config if self.parent.config else
                ContentType.nonconfig)

    @property
    def units(self: "TerminalNode") -> Optional[str]:
        """Units of the receiver's value, if specified."""
        return (self._units if self._units is not None
                else self.type.units)

    def from_raw(self: "TerminalNode", rval: RawScalar,
                 jptr: JSONPointer = "") -> ScalarValue:
        """Override the superclass method."""
        res = self.type.from_raw(rval)
        if res is None:
            raise RawTypeError(jptr, self.type.yang_type() + " value")
        return res

    def from_xml(self: "TerminalNode", rval: ET.Element, jptr: JSONPointer = "") -> Value:
        res = self.type.from_xml(rval)
        if res is None:
            raise RawTypeError(jptr, self.type.yang_type() + " value")
        return res

    def _deviate_type(self: "TerminalNode", stmt: Statement,
                         sctx: SchemaContext, action: str) -> None:
        if action == "replace":
            self.type = DataType._resolve_type(stmt, sctx)

    def _node_digest(self: "TerminalNode") -> dict[str, Any]:
        res = super()._node_digest()
        res["type"] = self.type._type_digest(self.config)
        df = self.default
        if df is not None:
            res["default"] = self.type.to_raw(df)
        if self.units:
            res["units"] = self.units
        return res

    def _units_stmt(self: "TerminalNode", stmt: Statement,
                      sctx: SchemaContext) -> None:
        self._units = stmt.argument

    def _deviate_units(self: "TerminalNode", stmt: Statement,
                       sctx: SchemaContext, action: str) -> None:
        if action == "delete":
            self._units = None
        elif action in ("add", "replace"):
            self._units_stmt(stmt, sctx)

    def _validate(self: "TerminalNode", inst: InstanceNode,
                  scope: ValidationScope, ctype: ContentType) -> None:
        """Extend the superclass method."""
        if (scope.value & ValidationScope.syntax.value and
                inst.value not in self.type):
            raise YangTypeError(inst, self.type.error_tag,
                                self.type.error_message)
        if (isinstance(self.type, LinkType) and        # referential integrity
                scope.value & ValidationScope.semantics.value and
                self.type.require_instance):
            try:
                tgt = inst._deref()
            except YangsonException:
                tgt = []
            if not tgt:
                raise SemanticError(inst, "instance-required")
        super()._validate(inst, scope, ctype)

    def _default_value(self: "TerminalNode", inst: InstanceNode, ctype: ContentType,
                       lazy: bool) -> InstanceNode:
        inst.value = self.default
        return inst

    def _post_process(self: "TerminalNode") -> None:
        super()._post_process()
        self.type._post_process(self)

    def _is_identityref(self: "TerminalNode") -> bool:
        return isinstance(self.type, IdentityrefType)

    def _ascii_tree(self: "TerminalNode", indent: str, no_types: bool, val_count: bool) -> str:
        return ""

    def _state_roots(self: "TerminalNode") -> list[SchemaNode]:
        return [] if self.content_type() == ContentType.config else [self]


class ContainerNode(DataNode, InternalNode):
    """Container node."""

    def __init__(self: "ContainerNode"):
        """Initialize the class instance."""
        super().__init__()
        self.presence: bool = False

    @property
    def mandatory(self: "ContainerNode") -> bool:
        """Extend the superclass property."""
        return not self.presence and super().mandatory

    @property
    def mandatory_config(self: "InternalNode") -> bool:
        """Override the superclass property."""
        return bool(self._mandatory_children[1])

    def _node_digest(self: "ContainerNode") -> dict[str, Any]:
        res = super()._node_digest()
        res["presence"] = self.presence
        return res

    def _add_mandatory_child(self: "ContainerNode", node: SchemaNode):
        propagate = not (self.presence or self.mandatory)
        super()._add_mandatory_child(node)
        if propagate:
            self.parent._add_mandatory_child(self)

    def _default_instance(self: "ContainerNode", pnode: InstanceNode, ctype: ContentType,
                          lazy: bool = False) -> InstanceNode:
        if self.presence:
            return pnode
        return super()._default_instance(pnode, ctype, lazy)

    def _default_value(self: "ContainerNode", inst: InstanceNode, ctype: ContentType,
                       lazy: bool) -> Optional[InstanceNode]:
        inst.value = ObjectValue()
        return inst if lazy else self._add_defaults(inst, ctype)

    def _pattern_entry(self: "ContainerNode") -> SchemaPattern:
        m = Member(self.iname(), self.content_type(), self.when)
        if self._status == NodeStatus.deprecated:
            return SchemaPattern.optional(m)
        if self.mandatory:
            return (m if self.mandatory_config else
                    SchemaPattern.optional_config(m))
        else:
            return SchemaPattern.optional(m)

    def _presence_stmt(self: "ContainerNode", stmt: Statement, sctx: SchemaContext) -> None:
        self.presence = True

    def _tree_line(self: "ContainerNode", no_type: bool = False) -> str:
        """Return the receiver's contribution to tree diagram."""
        return super()._tree_line() + ("!" if self.presence else "")


class SequenceNode(DataNode):
    """Abstract class for data nodes that represent a sequence."""

    def __init__(self: "SequenceNode"):
        """Initialize the class instance."""
        super().__init__()
        self.min_elements: int = 0
        self.max_elements: Optional[int] = None
        self.user_ordered: bool = False

    @property
    def mandatory(self: "SequenceNode") -> bool:
        """Override the superclass property."""
        return self.min_elements > 0

    def _validate(self: "SequenceNode", inst: InstanceNode,
                  scope: ValidationScope,
                  ctype: ContentType) -> None:
        """Extend the superclass method."""
        if isinstance(inst, ArrayEntry):
            super()._validate(inst, scope, ctype)
        else:
            if scope.value & ValidationScope.semantics.value:
                self._check_list_props(inst)
                self._check_cardinality(inst)
            for e in inst:
                super()._validate(e, scope, ctype)

    def _check_cardinality(self: "SequenceNode", inst: InstanceNode) -> None:
        if len(inst.value) < self.min_elements:
            raise SemanticError(inst, "too-few-elements")
        if (self.max_elements is not None and
                len(inst.value) > self.max_elements):
            raise SemanticError(inst, "too-many-elements")

    def _post_process(self: "SequenceNode") -> None:
        super()._post_process()
        if self.min_elements > 0:
            self.parent._add_mandatory_child(self)

    def _min_elements_stmt(self: "SequenceNode", stmt: Statement,
                           sctx: SchemaContext) -> None:
        self.min_elements = int(stmt.argument)

    def _deviate_min_elements(self: "SequenceNode", stmt: Statement,
                              sctx: SchemaContext, action: str) -> None:
        if action == "delete":
            self.min_elements = 0
        elif action in ("add", "replace"):
            self._min_elements_stmt(stmt, sctx)

    def _max_elements_stmt(self: "SequenceNode", stmt: Statement,
                           sctx: SchemaContext) -> None:
        arg = stmt.argument
        if arg == "unbounded":
            self.max_elements = None
        else:
            self.max_elements = int(arg)

    def _deviate_max_elements(self: "SequenceNode", stmt: Statement,
                              sctx: SchemaContext, action: str) -> None:
        if action == "delete":
            self.max_elements = None
        elif action in ("add", "replace"):
            self._max_elements_stmt(stmt, sctx)

    def _ordered_by_stmt(self: "SequenceNode", stmt: Statement,
                         sctx: SchemaContext) -> None:
        self.user_ordered = stmt.argument == "user"

    def _tree_line(self: "SequenceNode", no_type: bool = False) -> str:
        """Extend the superclass method."""
        return super()._tree_line() + ("#" if self.user_ordered else "*")

    def from_raw(self: "SequenceNode", rval: RawList,
                 jptr: JSONPointer = "") -> ArrayValue:
        """Override the superclass method."""
        if not isinstance(rval, list):
            raise RawTypeError(jptr, "array")
        res = ArrayValue()
        idx = 0
        for i in range(len(rval)):
            if isinstance(self, ListNode):
                try:
                    keys = [str(rval[i].get(k[0], '<missing>'))
                            for k in self.keys]
                except AttributeError:
                    raise RawTypeError(f"{jptr}/{i}", "object")
                element = "=" + ",".join(keys)
            else:
                element = "/" + str(idx)
            res.append(self.entry_from_raw(rval[i], jptr + element))
            idx = idx + 1
        return res

    def from_xml(self: "SequenceNode", rval: ET.Element, jptr: JSONPointer = "",
                 tagname: str = None, isroot: bool = False) -> ArrayValue:
        res = ArrayValue()
        idx = 0
        if isroot:
            return self._process_xmlarray_child(res, rval, None, jptr)
        else:
            for xmlchild in rval:
                if isinstance(self, ListNode):
                    keys = [str(xmlchild.findtext(k[0], default='<missing>')) for k in self.keys]
                    element = "=" + ",".join(keys)
                else:
                    element = "/" + str(idx)
                self._process_xmlarray_child(
                    res, xmlchild, tagname, jptr + element)
                idx = idx + 1
        return res

    def _process_xmlarray_child(
            self: "SequenceNode", res: ArrayValue, xmlchild: ET.Element,
            tagname: str, jptr: JSONPointer):
        if xmlchild.tag[0] == '{':
            xmlns, name = xmlchild.tag[1:].split('}')
            module = self.schema_root().schema_data.modules_by_ns.get(xmlns)
            if not module:
                raise MissingModuleNamespace(xmlns)
            ns = module.yang_id[0]
            qn = ns + ':' + name
        else:
            name = qn = xmlchild.tag
            ns = self.ns
        if tagname is None or qn == tagname:
            child = self.entry_from_xml(xmlchild, jptr + "/" + str(len(res)))
            res.append(child)
        else:
            child = None
        return child

    def entry_from_raw(self: "SequenceNode", rval: RawEntry,
                       jptr: JSONPointer = "") -> EntryValue:
        """Transform a raw (leaf-)list entry into the cooked form.

        Args:
            rval: raw entry (scalar or object)
            jptr: JSON pointer of the entry

        Raises:
            NonexistentSchemaNode: If a member inside `rval` is not defined
                in the schema.
            RawTypeError: If a scalar value inside `rval` is of incorrect type.
        """
        return super().from_raw(rval, jptr)

    def entry_from_xml(self: "SequenceNode", rval: ET.Element, jptr: JSONPointer = "") -> EntryValue:
        """Transform a XML (leaf-)list entry into the cooked form.

        Args:
            rval: xml node
            jptr: JSON pointer of the entry

        Raises:
            NonexistentSchemaNode: If a member inside `rval` is not defined
                in the schema.
            RawTypeError: If a scalar value inside `rval` is of incorrect type.
        """
        return super().from_xml(rval, jptr)


class ListNode(SequenceNode, InternalNode):
    """List node."""

    def __init__(self: "ListNode"):
        """Initialize the class instance."""
        super().__init__()
        self.keys: list[QualName] = []
        self._key_members = []
        self.unique: list[list[LocationPath]] = []

    def _node_digest(self: "ListNode") -> dict[str, Any]:
        res = super()._node_digest()
        res["keys"] = self._key_members
        return res

    def _check_list_props(self: "ListNode", inst: InstanceNode) -> None:
        """Check uniqueness of keys and "unique" properties, if applicable."""
        if self.keys:
            self._check_keys(inst)
        for u in self.unique:
            self._check_unique(u, inst)

    def _check_keys(self: "ListNode", inst: InstanceNode) -> None:
        ukeys = set()
        for i in range(len(inst.value)):
            en = inst.value[i]
            try:
                kval = tuple([en[k] for k in self._key_members])
            except KeyError as e:
                raise SchemaError(inst._entry(i),
                                  "list-key-missing", e.args[0]) from None
            if kval in ukeys:
                raise SemanticError(inst, "non-unique-key",
                                    repr(kval[0] if len(kval) < 2 else kval))
            ukeys.add(kval)

    def _check_unique(self: "ListNode", unique: list[LocationPath],
                      inst: InstanceNode) -> None:
        allvals = set()
        for i in range(len(inst.value)):
            en = inst[i]
            den = en.add_defaults()
            uvals = []
            for uex in unique:
                uval = [n.value for n in uex.evaluate(den)]
                uvals.append(uval)
            tups = set(product(*uvals))
            if tups & allvals:
                raise SemanticError(inst, f"data-not-unique: entry {i}")
            else:
                allvals |= tups

    def _default_instance(self: "ListNode", pnode: InstanceNode, ctype: ContentType,
                          lazy: bool = False) -> InstanceNode:
        return pnode

    def _post_process(self: "ListNode") -> None:
        super()._post_process()
        for k in self.keys:
            kn = self.get_data_child(*k)
            self._key_members.append(kn.iname())
            if not kn._mandatory:
                kn._mandatory = True
                self._add_mandatory_child(kn)

    def _key_stmt(self: "ListNode", stmt: Statement,
                  sctx: SchemaContext) -> None:
        self.keys = [sctx.schema_data.translate_node_id(k, sctx)
                     for k in stmt.argument.split()]

    def _parse_unique(self: "ListNode", stmt: Statement,
                     sctx: SchemaContext) -> list[LocationPath]:
        uspec = []
        for sid in stmt.argument.split():
            xpp = XPathParser(sid, sctx)
            uex = xpp.parse()
            if not xpp.at_end():
                raise InvalidArgument(stmt.argument)
            uspec.append(uex)
        return uspec

    def _unique_stmt(self: "ListNode", stmt: Statement,
                     sctx: SchemaContext) -> None:
        self.unique.append(self._parse_unique(stmt, sctx))

    def _deviate_unique(self: "ListNode", stmt: Statement,
                        sctx: SchemaContext, action: str) -> None:
        if action in ("add", "replace"):
            if action == "replace":
                self.unique = []
            self._unique_stmt(stmt, sctx)
        elif action == "delete":
            uniq = self._parse_unique(stmt, sctx)
            for i in range(len(self.unique)):
                if self.unique[i] == uniq:
                    del self.unique[i]
                    return

    def _tree_line(self: "ListNode", no_type: bool = False) -> str:
        """Return the receiver's contribution to tree diagram."""
        keys = (" [" + " ".join([k[0] for k in self.keys]) + "]"
                if self.keys else "")
        return super()._tree_line() + keys

    def orphan_entry(self: "ListNode", rval: RawObject) -> "ArrayEntry":
        """Return an isolated entry of the receiver.

        Args:
            rval: Raw object to be used for the returned entry.
        """
        val = self.entry_from_raw(rval, jptr = "/")
        return ArrayEntry(0, EmptyList(), EmptyList(), val, None, self,
                          val.timestamp)


class ChoiceNode(InternalNode):
    """Choice node."""

    def __init__(self: "ChoiceNode"):
        """Initialize the class instance."""
        super().__init__()
        self.default_case: QualName = None
        self._mandatory: bool = False

    @property
    def mandatory(self: "ChoiceNode") -> bool:
        """Override the superclass property."""
        return self._mandatory

    def _add_defaults(self: "ChoiceNode", inst: InstanceNode,
                      ctype: ContentType) -> InstanceNode:
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

    def _active_case(self: "ChoiceNode",
                     value: ObjectValue) -> Optional["CaseNode"]:
        """Return receiver's case that's active in an instance node value."""
        for c in self.children:
            for cc in c.data_children():
                if cc.iname() in value:
                    return c

    def _pattern_entry(self: "ChoiceNode") -> SchemaPattern:
        if not self.children:
            return Empty()
        prev = self.children[0]._schema_pattern()
        for c in self.children[1:]:
            prev = ChoicePattern(c._schema_pattern(), prev, self.name)
        prev.ctype = self.content_type()
        if not self.mandatory:
            prev = SchemaPattern.optional(prev)
        return ConditionalPattern(prev, self.when) if self.when else prev

    def _post_process(self: "ChoiceNode") -> None:
        super()._post_process()
        if self.mandatory:
            self.parent._add_mandatory_child(self)

    def _tree_line_prefix(self: "ChoiceNode") -> str:
        return super()._tree_line_prefix() + (
            "ro" if self.content_type() == ContentType.nonconfig else "rw")

    def _handle_child(self: "ChoiceNode", node: SchemaNode, stmt: Statement,
                      sctx: SchemaContext) -> None:
        if isinstance(node, CaseNode):
            super()._handle_child(node, stmt, sctx)
        else:
            cn = CaseNode()
            cn.name = stmt.argument
            cn.ns = sctx.default_ns
            self._add_child(cn)
            cn._handle_child(node, stmt, sctx)

    def _default_stmt(self: "ChoiceNode", stmt: Statement,
                      sctx: SchemaContext) -> None:
        self.default_case = sctx.schema_data.translate_node_id(
            stmt.argument, sctx)

    def _deviate_default(self: "ChoiceNode", stmt: Statement,
                         sctx: SchemaContext, action: str) -> None:
        if action == "delete":
            self.default_case = None
        elif action in ("add", "replace"):
            self._default_stmt(stmt, sctx)

    def _tree_line(self: "ChoiceNode", no_type: bool = False) -> str:
        """Return the receiver's contribution to tree diagram."""
        return f"{self._tree_line_prefix()} ({self._tree_name()})" \
            f"{'' if self._mandatory else '?'}"


class CaseNode(InternalNode):
    """Case node."""

    def _pattern_entry(self: "CaseNode") -> SchemaPattern:
        return super()._schema_pattern()

    def _tree_line(self: "CaseNode", no_type: bool = False) -> str:
        """Return the receiver's contribution to tree diagram."""
        return f"{self._tree_line_prefix()}:({self._tree_name()})"


class LeafNode(DataNode, TerminalNode):
    """Leaf node."""

    def __init__(self: "LeafNode"):
        """Initialize the class instance."""
        super().__init__()
        self._mandatory: bool = False

    @property
    def mandatory(self: "LeafNode") -> bool:
        """Override the superclass property."""
        return self._mandatory

    @property
    def default(self: "LeafNode") -> Optional[ScalarValue]:
        """Default value of the receiver, if any."""
        if self.mandatory:
            return None
        if self._default is not None:
            return self._default
        return self.type.default

    def _post_process(self: "LeafNode") -> None:
        super()._post_process()
        if self._mandatory:
            self.parent._add_mandatory_child(self)
        elif self._default is not None:
            self._default = self.type.from_yang(self._default)

    def _tree_line(self: "LeafNode", no_type: bool = False) -> str:
        res = super()._tree_line() + ("" if self._mandatory else "?")
        return res if no_type else f"{res} <{self.type}>"

    def _default_stmt(self: "LeafNode", stmt: Statement,
                      sctx: SchemaContext) -> None:
        self._default = stmt.argument

    def _deviate_default(self: "LeafNode", stmt: Statement,
                         sctx: SchemaContext, action: str) -> None:
        if action == "delete":
            self._default = None
        elif action in ("add", "replace"):
            self._default_stmt(stmt, sctx)


class LeafListNode(SequenceNode, TerminalNode):
    """Leaf-list node."""

    @property
    def default(self: "LeafListNode") -> Optional[ScalarValue]:
        """Default value of the receiver, if any."""
        if self.mandatory:
            return None
        if self._default is not None:
            return self._default
        return (None if self.type.default is None
                else ArrayValue([self.type.default]))

    def _yang_class(self: "LeafListNode") -> str:
        return "leaf-list"

    def _check_list_props(self: "LeafListNode", inst: InstanceNode) -> None:
        if (self.content_type() == ContentType.config and
                len(set(inst.value)) < len(inst.value)):
            raise SemanticError(inst, "repeated-leaf-list-value")

    def _default_stmt(self: "LeafListNode",
                      stmt: Statement, sctx: SchemaContext) -> None:
        if self._default is None:
            self._default = [stmt.argument]
        else:
            self._default.append(stmt.argument)

    def _deviate_default(self: "LeafListNode", stmt: Statement,
                         sctx: SchemaContext, action: str) -> None:
        if action in ("add", "replace"):
            if action == "replace":
                self._default = []
            self._default_stmt(stmt, sctx)
        elif action == "delete":
            val = self.type.parse_value(stmt.argument)
            for i in range(len(self._default)):
                if self._default[i] == val:
                    del self._default[i]
                    return

    def _post_process(self: "LeafListNode") -> None:
        super()._post_process()
        if self._default is not None:
            self._default = ArrayValue(
                [self.type.from_yang(v) for v in self._default])

    def _tree_line(self: "LeafListNode", no_type: bool = False) -> str:
        res = super()._tree_line()
        return res if no_type else f"{res} <{self.type}>"


class AnyContentNode(DataNode):
    """Abstract class for anydata or anyxml nodes."""

    def __init__(self: "AnyContentNode"):
        """Initialize the class instance."""
        super().__init__()
        self._mandatory: bool = False

    def content_type(self: "AnyContentNode") -> ContentType:
        """Override superclass method."""
        return TerminalNode.content_type(self)

    @property
    def mandatory(self: "AnyContentNode") -> bool:
        """Override the superclass property."""
        return self._mandatory

    def from_raw(self: "AnyContentNode", rval: RawValue, jptr: JSONPointer = "") -> Value:
        """Override the superclass method."""
        def convert(val):
            if isinstance(val, list):
                res = ArrayValue([convert(x) for x in val])
            elif isinstance(val, dict):
                res = ObjectValue({x: convert(val[x]) for x in val})
            else:
                res = val
            return res
        return convert(rval)

    def to_raw(self: "AnyContentNode", value: Value) -> RawValue:
        """Convert the value again to plain Python stuff."""
        def convert(val):
            if isinstance(val, ArrayValue):
                res = [convert(x) for x in val]
            elif isinstance(val, ObjectValue):
                res = {x: convert(val[x]) for x in val}
            else:
                res = val
            return res
        return convert(value)

    def from_xml(self: "AnyContentNode", rval: ET.Element, jptr: JSONPointer = "") -> Value:
        super().from_xml(rval, jptr)

    def _default_instance(self: "AnyContentNode", pnode: InstanceNode, ctype: ContentType,
                          lazy: bool = False) -> InstanceNode:
        return pnode

    def _tree_line(self: "AnyContentNode", no_type: bool = False) -> str:
        return super()._tree_line() + ("" if self._mandatory else "?")

    def _ascii_tree(self: "AnyContentNode", indent: str, no_types: bool, val_count: bool) -> str:
        return ""

    def _post_process(self: "AnyContentNode") -> None:
        if self._mandatory:
            self.parent._add_mandatory_child(self)


class AnydataNode(AnyContentNode):
    """Anydata node."""
    pass


class AnyxmlNode(AnyContentNode):
    """Anyxml node."""
    pass


class RpcActionNode(SchemaTreeNode):
    """RPC or action node."""

    def __init__(self: "RpcActionNode"):
        """Initialize the class instance."""
        super().__init__()
        self.default_deny: DefaultDeny = DefaultDeny.none
        self._ctype = ContentType.nonconfig

    def iname(self: "SchemaTreeNode") -> InstanceName:
        """Override the superclass method."""
        return super(GroupNode, self).iname()

    def data_parent(self: "SchemaTreeNode") -> None:
        """Override the superclass method."""
        return self.parent

    def _handle_substatements(self: "RpcActionNode", stmt: Statement,
                              sctx: SchemaContext) -> None:
        self._add_child(InputNode(sctx.default_ns))
        self._add_child(OutputNode(sctx.default_ns))
        super()._handle_substatements(stmt, sctx)

    def _flatten(self: "RpcActionNode") -> list[SchemaNode]:
        return [self]

    def _tree_line_prefix(self: "RpcActionNode") -> str:
        return super()._tree_line_prefix() + "-x"

    def _input_stmt(self: "RpcActionNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle RPC or action input statement."""
        self.get_child("input")._handle_substatements(stmt, sctx)

    def _output_stmt(self: "RpcActionNode", stmt: Statement, sctx: SchemaContext) -> None:
        """Handle RPC or action output statement."""
        self.get_child("output")._handle_substatements(stmt, sctx)


class InputNode(InternalNode, DataNode):
    """RPC or action input node."""

    def __init__(self: "InputNode", ns):
        """Initialize the class instance."""
        super().__init__()
        self._config = False
        self.name = "input"
        self.ns = ns

    def iname(self: "InputNode") -> InstanceName:
        """Override the superclass method."""
        return self.ns + ":" + self.name

    def _flatten(self: "InputNode") -> list[SchemaNode]:
        return [self]


class OutputNode(InternalNode, DataNode):
    """RPC or action output node."""

    def __init__(self: "OutputNode", ns):
        """Initialize the class instance."""
        super().__init__()
        self._config = False
        self.name = "output"
        self.ns = ns

    def iname(self: "OutputNode") -> InstanceName:
        """Override the superclass method."""
        return self.ns + ":" + self.name

    def _flatten(self: "OutputNode") -> list[SchemaNode]:
        return [self]


class NotificationNode(SchemaTreeNode):
    """Notification node."""

    def __init__(self: "NotificationNode"):
        """Initialize the class instance."""
        super().__init__()
        self.default_deny: DefaultDeny = DefaultDeny.none
        self._ctype = ContentType.nonconfig

    def _flatten(self: "NotificationNode") -> list[SchemaNode]:
        return [self]

    def _tree_line_prefix(self: "NotificationNode") -> str:
        return super()._tree_line_prefix() + "-n"
