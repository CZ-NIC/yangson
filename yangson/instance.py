"""Instance data represented as a persistent structure.

This module implements the following classes:

* InstanceNode: Abstract class for instance nodes.
* RootNode: Root of the data tree.
* ObjectMember: Instance node that is an object member.
* ArrayEntry: Instance node that is an array entry.
* ResourceIdParser: Parser for RESTCONF resource identifiers.
* InstanceIdParser: Parser for instance identifiers.

The module defines the following exceptions:

* InstanceException: Base class for exceptions related to operations
  on instance nodes.
* NonexistentInstance: Attempt to access an instance node that doesn't
  exist.
* InstanceTypeError: A method is called for a wrong type of instance
  node.
* DuplicateMember: Attempt to create a member that already exists.
* MandatoryMember: Attempt to remove a mandatory member.
* MinElements: An array becomes shorter than the minimum number of
  elements specified in the data model..
* MaxElements: An array becomes longer than the maximum number of
  elements specified in the data model.
"""

from datetime import datetime
from typing import Any, Callable, List, Tuple
from urllib.parse import unquote
from .exceptions import YangsonException
from .context import Context
from .enumerations import ContentType
from .instvalue import ArrayValue, ObjectValue, Value
from .parser import EndOfInput, Parser, UnexpectedInput
from .typealiases import *

class InstanceNode:
    """YANG data node instance implemented as a zipper structure."""

    def __init__(self, value: Value, parinst: Optional["InstanceNode"],
                 schema_node: "DataNode", timestamp: datetime) -> None:
        """Initialize the class instance."""
        self.value = value             # type: Value
        """Value of the receiver."""
        self.parinst = parinst         # type: Optional["InstanceNode"]
        """Parent instance node, or ``None`` for the root node."""
        self.schema_node = schema_node # type: DataNode
        """Data node corresponding to the instance node."""
        self.timestamp = timestamp     # type: datetime
        """Time of the receiver's last modification."""

    def __str__(self):
        """Return string representation of the receiver's value."""
        sn = self.schema_node
        if not self.is_structured():
            return sn.type.canonical_string(self.value)
        return str(self.value)

    @property
    def qualName(self) -> Optional[QualName]:
        """The receiver's qualified name."""
        return None

    @property
    def namespace(self) -> Optional[YangIdentifier]:
        """The receiver's namespace."""
        return self.schema_node.ns

    def validate(self, content: ContentType = ContentType.config) -> None:
        """Validate the receiver.

        Args:
            content: Receiver's content type (config/all).

        Raises:
            SchemaError`: If the value doesn't conform to the schema.
            SemanticError: If the value violates a semantic constraint.
        """
        self.schema_node.validate(self, content)

    def json_pointer(self) -> str:
        """Return JSON Pointer [RFC6901]_ of the receiver."""
        parents = []
        inst = self
        while inst.parinst:
            parents.append(inst)
            inst = inst.parinst
        return "/" + "/".join([i._pointer_fragment() for i in parents[::-1]])

    def update(self, value: Value) -> "InstanceNode":
        """Update the receiver's value.

        Args:
            value: New value.

        Returns:
            Copy of the receiver with the updated value.
        """
        return self._copy(value, datetime.now())

    def update_from_raw(self, rvalue: RawValue) -> "InstanceNode":
        """Update the receiver's value from a raw value.

        Args:
            rvalue: New raw value.

        Returns:
            Copy of the receiver with the updated value.
        """
        newval = self.schema_node.from_raw(rvalue)
        return self.update(newval)

    def up(self) -> "InstanceNode":
        """Move the focus to the parent instance node.

        Returns:
            An instance node that is the parent of the receiver.

        Raises:
            NonexistentInstance: If there is no parent.
        """
        ts = max(self.timestamp, self.parinst.timestamp)
        return self.parinst._copy(self._zip(), ts)

    def top(self) -> "InstanceNode":
        """Move the focus to the root instance node.

        Returns:
            The root instance node.
        """
        inst = self
        while inst.parinst:
            inst = inst.up()
        return inst

    def goto(self, iroute: "InstanceRoute") -> "InstanceNode":
        """Move the focus to an instance inside the receiver's value.

        Args:
            iroute: Instance route (relative to the receiver).

        Returns:
            The instance node corresponding to the target instance.

        Raises:
            InstanceTypeError: If `iroute` is incompatible with the schema.
            NonexistentInstance: If the instance node doesn't exist.
        """
        inst = self
        for sel in iroute:
            inst = sel.goto_step(inst)
        return inst

    def peek(self, iroute: "InstanceRoute") -> Optional[Value]:
        """Return a value within the receiver's subtree.

        Args:
            iroute: Instance route (relative to the receiver).
        """
        val = self.value
        for sel in iroute:
            val = sel.peek_step(val)
            if val is None: return None
        return val

    def member(self, name: InstanceName) -> "ObjectMember":
        """Return an instance node corresponding to a receiver's member.

        Args:
            name: Instance name of the member

        Raises:
            NonexistentSchemaNode: If the member isn't permitted by the schema.
            NonexistentInstance: If receiver's value doesn't contain member of
                that name.
        """
        csn = self._member_schema_node(name)
        sibs = self.value.copy()
        try:
            return ObjectMember(name, sibs, sibs.pop(name), self,
                                csn, self.value.timestamp)
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None

    def put_member(self, name: InstanceName, value: Value) -> "InstanceNode":
        """Return a copy of the receiver with a new value of a member.

        If the member is permitted by the schema but doesn't exist, it
        is created.

        Args:
            name: Instance name of the member.
            value: New value of the member.

        Raises:
            NonexistentSchemaNode: If the member isn't permitted by the schema.
        """
        csn = self._member_schema_node(name)
        newval = self.value.copy()
        newval[name] = value
        sn = csn
        while sn is not self.schema_node:
            if isinstance(sn, CaseNode):
                for ci in sn.competing_instances():
                    newval.pop(ci, None)
            sn = sn.parent
        ts = datetime.now()
        return self._copy(ObjectValue(newval, ts) , ts)

    def delete_member(self, name: InstanceName) -> "InstanceNode":
        """Return a copy of the receiver with a member deleted from its value.

        Args:
            name: Instance name of the member.

        Raises:
            NonexistentSchemaNode: If the member isn't permitted by the schema.
            NonexistentInstance: If receiver's value doesn't contain member of
                that name.
        """
        if name not in self.value:
            raise NonexistentInstance(self, "member " + name) from None
        csn = self._member_schema_node(name)
        if validate and csn.mandatory: raise MandatoryMember(self, name)
        newval = self.value.copy()
        del newval[name]
        ts = datetime.now()
        return self._copy(ObjectValue(newval, ts), ts)

    def entry(self, index: int) -> "ArrayEntry":
        """Return an instance node corresponding to a receiver's entry.

        Args:
            index: Index of the entry.

        Raises:
            InstanceTypeError: If the receiver's value is not an array.
            NonexistentInstance: If entry `index` is not present.
        """
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "entry of non-array")
        try:
            return ArrayEntry(val[:index], val[index+1:], val[index], self,
                              self.schema_node, val.timestamp)
        except IndexError:
            raise NonexistentInstance(self, "entry " + str(index)) from None

    def last_entry(self) -> "ArrayEntry":
        """Return an instance node corresponding to the last entry of the receiver.

        Raises:
            InstanceTypeError: If the receiver's value isn't an array.
            NonexistentInstance: If the receiver's value is an empty array.
        """
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "last entry of non-array")
        try:
            return ArrayEntry(val[:-1], [], val[-1], self,
                              self.schema_node, val.timestamp)
        except IndexError:
            raise NonexistentInstance(self, "last of empty") from None

    def delete_entry(self, index: int) -> "InstanceNode":
        """Return a copy of the receiver with an entry deleted from its value.

        Args:
            index: Index of the deleted entry.

        Raises:
            InstanceTypeError: If the receiver value is not an array.
            NonexistentInstance: If entry `index` is not present.
        """
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "entry of non-array")
        if index >= len(val):
            raise NonexistentInstance(self, "entry " + str(index)) from None
        ts = datetime.now()
        return self._copy(ArrayValue(val[:index] + val[index+1:], ts), ts)

    def look_up(self, keys: Dict[InstanceName, ScalarValue]) -> "ArrayEntry":
        """Return the entry with matching keys.

        Args:
            keys: Dictionary of list keys and their values.

        Raises:
            InstanceTypeError: If the receiver is not a YANG list.
            NonexistentInstance: If no entry with matching keys exists.
        """
        if not isinstance(self.value, ArrayValue):
            raise InstanceTypeError(self, "lookup on non-list")
        try:
            for i in range(len(self.value)):
                en = self.value[i]
                flag = True
                for k in keys:
                    if en[k] != keys[k]:
                        flag = False
                        break
                if flag: return self.entry(i)
            raise NonexistentInstance(self, "entry lookup failed")
        except KeyError:
            raise NonexistentInstance(self, "entry lookup failed") from None
        except TypeError:
            raise InstanceTypeError(self, "lookup on non-list") from None

    def add_defaults(self) -> "InstanceNode":
        """Return a copy of the receiver with defaults added to its value."""
        sn = self.schema_node
        if isinstance(self.value, ArrayValue) and isinstance(sn, ListNode):
            try:
                inst = self.entry(0)
            except NonexistentInstance:
                return self
            try:
                while True:
                    ninst = inst.add_defaults()
                    inst = ninst.next()
            except NonexistentInstance:
                return ninst.up()
        if isinstance(sn, InternalNode):
            res = self
            if self.value:
                for mn in self.value:
                    m = res.member(mn) if res is self else res.sibling(mn)
                    res = m.add_defaults()
                res = res.up()
            sn._apply_defaults(res.value)
            return res
        return self

    def _member_schema_node(self, name: InstanceName) -> "DataNode":
        qname = self.schema_node.iname2qname(name)
        res = self.schema_node.get_data_child(*qname)
        if res is None:
            raise NonexistentSchemaNode(*qname)
        return res

    def _node_set(self) -> List["InstanceNode"]:
        """XPath - return the list of all receiver's nodes."""
        val = self.value
        if isinstance(val, ArrayValue):
            return [ self.entry(i) for i in range(len(val)) ]
        return [self]

    def _children(self,
                 qname: Union[QualName, bool] = None) -> List["InstanceNode"]:
        """XPath - return the list of receiver's children."""
        sn = self.schema_node
        if not isinstance(sn, InternalNode): return []
        if qname:
            cn = sn.get_data_child(*qname)
            if cn is None: return []
            iname = cn.iname()
            if iname in self.value:
                return self.member(iname)._node_set()
            res = cn._default_nodes(self)
            if not res: return res
            while True:
                cn = cn.parent
                if cn is sn: return res
                if ((cn.when is None or cn.when.evaluate(self)) and
                    (not isinstance(cn, CaseNode) or
                     cn.qual_name == cn.parent.default_case)):
                    continue
                return []
        res = []
        for cn in sn.children:
            if isinstance(cn, ChoiceNode):
                cin = cn.child_inst_names().intersection(self.value)
                if cin:
                    for i in cin:
                        res.extend(self.member(i)._node_set())
                else:
                    res.extend(cn._default_nodes(inst))
            else:
                iname = cn.iname()
                if iname in self.value:
                    res.extend(self.member(iname)._node_set())
                else:
                    res.extend(cn._default_nodes(self))
        return res

    def _descendants(self, qname: Union[QualName, bool] = None,
                    with_self: bool = False) -> List["InstanceNode"]:
        """XPath - return the list of receiver's descendants."""
        res = ([] if not with_self or (qname and self.qualName != qname)
               else [self])
        for c in self._children():
            if not qname or c.qualName == qname:
                res.append(c)
            res += c._descendants(qname)
        return res

    def _preceding_siblings(
            self, qname: Union[QualName, bool] = None) -> List["InstanceNode"]:
        """XPath - return the list of receiver's preceding-siblings."""
        return []

    def _following_siblings(
            self, qname: Union[QualName, bool] = None) -> List["InstanceNode"]:
        """XPath - return the list of receiver's following-siblings."""
        return []

    def _parent(self) -> List["InstanceNode"]:
        """XPath - return the receiver's parent as a singleton list."""
        return [self.up()]

    def _deref(self) -> List["InstanceNode"]:
        """XPath - return the list of nodes that the receiver refers to."""
        return ([] if self.is_structured() else
                self.schema_node.type._deref(self))

class RootNode(InstanceNode):
    """This class represents the root of the instance tree."""

    def __init__(self, value: Value, schema_node: "DataNode",
                 ts: datetime) -> None:
        super().__init__(value, None, schema_node, ts)
        self.name = None # type: None
        """The instance name of the root node is always ``None``."""

    def up(self) -> None:
        """Override the superclass method.

        Raises:
            NonexistentInstance: root node has no parent
        """
        raise NonexistentInstance(self, "up of top")

    def _copy(self, newval: Value = None,
              newts: datetime = None) -> InstanceNode:
        return RootNode(newval if newval else self.value, self.schema_node,
                          newts if newts else self._timestamp)

    def is_structured(self):
        """Return ``True`` if the receiver has a structured value."""
        return True

    def _ancestors_or_self(
            self, qname: Union[QualName, bool] = None) -> List["RootNode"]:
        """XPath - return the list of receiver's ancestors including itself."""
        return [self] if qname is None else []

    def _ancestors(
            self, qname: Union[QualName, bool] = None) -> List["RootNode"]:
        """XPath - return the list of receiver's ancestors."""
        return []

class ObjectMember(InstanceNode):
    """This class represents an object member."""

    def __init__(self, name: InstanceName, siblings: Dict[InstanceName, Value],
                 value: Value, parinst: InstanceNode,
                 schema_node: "DataNode", ts: datetime ) -> None:
        super().__init__(value, parinst, schema_node, ts)
        self.name = name # type: InstanceName
        """The instance name of the receiver."""
        self.siblings = siblings # type: Dict[InstanceName, Value]
        """Sibling members within the parent object."""

    @property
    def qualName(self) -> Optional[QualName]:
        """Return the receiver's qualified name."""
        p, s, loc = self.name.partition(":")
        return (loc, p) if s else (p, self.namespace)

    def _zip(self) -> ObjectValue:
        """Zip the receiver into an object and return it."""
        res = ObjectValue(self.siblings.copy(), self.timestamp)
        res[self.name] = self.value
        return res

    def is_structured(self) -> bool:
        """Return ``True`` if the receiver has a structured value."""
        return not isinstance(self.schema_node, LeafNode)

    def _pointer_fragment(self) -> str:
        return self.name

    def _copy(self, newval: Value = None,
              newts: datetime = None) -> "ObjectMember":
        return ObjectMember(self.name, self.siblings,
                           newval if newval else self.value,
                           self.parinst, self.schema_node,
                           newts if newts else self._timestamp)

    def sibling(self, name: InstanceName) -> "ObjectMember":
        """Return an instance node corresponding to a sibling member.

        Args:
            name: Instance name of the sibling member.

        Raises:
            NonexistentSchemaNode: If member `name` is not permitted by the schema.
            NonexistentInstance: If sibling member `name` doesn't exist.
        """
        ssn = self.parinst._member_schema_node(name)
        try:
            sibs = self.siblings.copy()
            newval = sibs.pop(name)
            sibs[self.name] = self.value
            return ObjectMember(name, sibs, newval, self.parinst,
                                ssn, self.timestamp)
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None

    def _ancestors_or_self(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """XPath - return the list of receiver's ancestors including itself."""
        res = [] if qname and self.qualName != qname else [self]
        return res + self.up()._ancestors_or_self(qname)

    def _ancestors(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """XPath - return the list of receiver's ancestors."""
        return self.up()._ancestors_or_self(qname)

class ArrayEntry(InstanceNode):
    """This class represents an array entry."""

    def __init__(self, before: List[Value], after: List[Value],
                 value: Value, parinst: InstanceNode,
                 schema_node: "DataNode", ts: datetime = None) -> None:
        super().__init__(value, parinst, schema_node, ts)
        self.before = before # type: List[Value]
        """Preceding entries of the parent array."""
        self.after = after # type: List[Value]
        """Following entries of the parent array."""

    @property
    def name(self) -> InstanceName:
        """Return the name of the receiver."""
        return self.parinst.name

    @property
    def qualName(self) -> Optional[QualName]:
        """Return the receiver's qualified name."""
        return self.parinst.qualName

    @property
    def index(self) -> int:
        """Return the receiver's index."""
        return len(self.before)

    def update_from_raw(self, value: RawValue) -> "ArrayEntry":
        """Update the receiver's value from a raw value.

        This method overrides the superclass method.
        """
        return self.update(super(SequenceNode, self.schema_node).from_raw(value))

    def _zip(self) -> ArrayValue:
        """Zip the receiver into an array and return it."""
        res = ArrayValue(self.before.copy(), self.timestamp)
        res.append(self.value)
        res += self.after
        return res

    def is_structured(self) -> bool:
        """Return ``True`` if the receiver has a structured value."""
        return not isinstance(self.schema_node, LeafListNode)

    def _pointer_fragment(self) -> int:
        return str(len(self.before))

    def _copy(self, newval: Value = None,
              newts: datetime = None) -> "ArrayEntry":
        return ArrayEntry(self.before, self.after,
                          newval if newval else self.value,
                          self.parinst, self.schema_node,
                          newts if newts else self._timestamp)

    def next(self) -> "ArrayEntry":
        """Return an instance node corresponding to the next entry.

        Raises:
            NonexistentInstance: If the receiver is the last entry of the parent array.
        """
        try:
            newval = self.after[0]
        except IndexError:
            raise NonexistentInstance(self, "next of last") from None
        return ArrayEntry(self.before + [self.value], self.after[1:], newval,
                          self.parinst, self.schema_node, self.timestamp)

    def previous(self) -> "ArrayEntry":
        """Return an instance node corresponding to the previous entry.

        Raises:
            NonexistentInstance: If the receiver is the first entry of the parent array.
        """
        try:
            newval = self.before[-1]
        except IndexError:
            raise NonexistentInstance(self, "previous of first") from None
        return ArrayEntry(self.before[:-1], [self.value] + self.after, newval,
                          self.parinst, self.schema_node, self.timestamp)

    def insert_before(self, value: Value) -> "ArrayEntry":
        """Insert a new entry before the receiver.

        Args:
            value: The value of the new entry.

        Returns:
            An instance node of the new inserted entry.
        """
        return ArrayEntry(self.before, [self.value] + self.after, value,
                          self.parinst, self.schema_node, datetime.now())

    def insert_after(self, value: Value) -> "ArrayEntry":
        """Insert a new entry after the receiver.

        Args:
            value: The value of the new entry.

        Returns:
            An instance node of the newly inserted entry.
        """
        return ArrayEntry(self.before + [self.value], self.after, value,
                          self.parinst, self.schema_node, datetime.now())

    def _ancestors_or_self(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """XPath - return the list of receiver's ancestors including itself."""
        res = [] if qname and self.qualName != qname else [self]
        return res + self.up()._ancestors(qname)

    def _ancestors(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """XPath - return the list of receiver's ancestors."""
        return self.up()._ancestors(qname)

    def preceding_entries(self) -> List["ArrayEntry"]:
        """Return the list of entries preceding the receiver."""
        res = []
        ent = self
        for i in range(len(self.before)):
            ent = ent.previous()
            res.append(ent)
        return res

    def following_entries(self) -> List["ArrayEntry"]:
        """Return the list of entries following the receiver."""
        res = []
        ent = self
        for i in range(len(self.after)):
            ent = ent.next()
            res.append(ent)
        return res

    def _preceding_siblings(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """XPath - return the list of receiver's preceding siblings."""
        return ([] if qname and self.qualName != qname
                else self.preceding_entries())

    def _following_siblings(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """XPath - return the list of receiver's following siblings."""
        return ([] if qname and self.qualName != qname
                else self.following_entries())

    def _parent(self) -> List["InstanceNode"]:
        """XPath - return the receiver's parent as a singleton list."""
        return [self.up().up()]

class InstanceSelector:
    """Components of instance identifers."""
    pass

class MemberName(InstanceSelector):
    """Selectors of object members."""

    def __init__(self, name: InstanceName) -> None:
        """Initialize the class instance.

        Args:
            name: Member name.
        """
        self.name = name

    def __str__(self) -> str:
        """Return a string representation of the receiver."""
        return "/" + self.name

    def __eq__(self, other: "MemberName") -> bool:
        return self.name == other.name

    def peek_step(self, obj: ObjectValue) -> Value:
        """Return the member of `obj` addressed by the receiver.

        Args:
            obj: Current object.
        """
        return obj.get(self.name)

    def goto_step(self, inst: InstanceNode) -> InstanceNode:
        """Return member instance of `inst` addressed by the receiver.

        Args:
            inst: Current instance.
        """
        return inst.member(self.name)

class EntryIndex(InstanceSelector):
    """Numeric selectors for a list or leaf-list entry."""

    def __init__(self, index: int) -> None:
        """Initialize the class instance.

        Args:
            index: Index of an entry.
        """
        self.index = index

    def __str__(self) -> str:
        """Return a string representation of the receiver."""
        return "[{0:d}]".format(self.index)

    def __eq__(self, other: "EntryIndex") -> bool:
        return self.index == other.index

    def peek_step(self, arr: ArrayValue) -> Value:
        """Return the entry of `arr` addressed by the receiver.

        Args:
            arr: Current array.
        """
        try:
            return arr[self.index]
        except IndexError:
            return None

    def goto_step(self, inst: InstanceNode) -> InstanceNode:
        """Return member instance of `inst` addressed by the receiver.

        Args:
            inst: Current instance.
        """
        return inst.entry(self.index)

class EntryValue(InstanceSelector):
    """Value-based selectors of an array entry."""

    def __init__(self, value: ScalarValue) -> None:
        """Initialize the class instance.

        Args:
            value: Value of a leaf-list entry.
        """
        self.value = value

    def __str__(self) -> str:
        """Return a string representation of the receiver."""
        return "[.=" + str(self.value) +"]"

    def __eq__(self, other: "EntryValue") -> bool:
        return self.value == other.value

    def peek_step(self, arr: ArrayValue) -> Value:
        """Return the entry of `arr` addressed by the receiver.

        Args:
            arr: Current array.
        """
        try:
            return arr[arr.index(self.value)]
        except ValueError:
            return None

    def goto_step(self, inst: InstanceNode) -> InstanceNode:
        """Return member instance of `inst` addressed by the receiver.

        Args:
            inst: Current instance.
        """
        try:
            return inst.entry(inst.value.index(self.value))
        except ValueError:
            raise NonexistentInstance(
                inst, "entry '{}'".format(str(self.value))) from None

class EntryKeys(InstanceSelector):
    """Key-based selectors for a list entry."""

    def __init__(self, keys: Dict[InstanceName, ScalarValue]) -> None:
        """Initialize the class instance.

        Args:
            keys: Dictionary with keys of an entry.
        """
        self.keys = keys

    def __str__(self) -> str:
        """Return a string representation of the receiver."""
        return "".join(["[{}={}]".format(k, repr(self.keys[k]))
                        for k in self.keys])

    def __eq__(self, other: "EntryKeys") -> bool:
        return self.keys == other.keys

    def peek_step(self, arr: ArrayValue) -> Value:
        """Return the entry of `arr` addressed by the receiver.

        Args:
            arr: Current array.
        """
        for en in arr:
            flag = True
            for k in self.keys:
                if en[k] != self.keys[k]:
                    flag = False
                    break
            if flag: return en

    def goto_step(self, inst: InstanceNode) -> InstanceNode:
        """Return member instance of `inst` addressed by the receiver.

        Args:
            inst: Current instance.
        """
        return inst.look_up(self.keys)

class InstancePathParser(Parser):
    """Abstract class for parsers of strings identifying instances."""

    def _member_name(self, sn: "InternalNode") -> Tuple[MemberName, "DataNode"]:
        """Parser object member name."""
        name, ns = self.prefixed_name()
        cn = sn.get_data_child(name, ns if ns else sn.ns)
        if cn is None:
            raise NonexistentSchemaNode(name, ns)
        return (MemberName(cn.iname()), cn)

class ResourceIdParser(InstancePathParser):
    """Parser for RESTCONF resource identifiers."""

    def parse(self) -> "InstanceRoute":
        """Parse resource identifier."""
        if self.peek() == "/": self.offset += 1
        res = []
        sn = Context.schema
        while True:
            mnam, cn = self._member_name(sn)
            res.append(mnam)
            try:
                next = self.one_of("/=")
            except EndOfInput:
                return res
            if next == "=":
                res.append(self._key_values(cn))
                if self.at_end(): return res
            sn = cn

    def _key_values(self, sn: "SequenceNode") -> Union[EntryKeys, EntryValue]:
        """Parse leaf-list value or list keys."""
        try:
            keys = self.up_to("/")
        except EndOfInput:
            keys = self.remaining()
        if not keys:
            raise UnexpectedInput(self, "entry value or keys")
        if isinstance(sn, LeafListNode):
            return EntryValue(sn.type.parse_value(unquote(keys)))
        ks = keys.split(",")
        try:
            if len(ks) != len(sn.keys):
                raise UnexpectedInput(
                    self, "exactly {} keys".format(len(sn.keys)))
        except AttributeError:
            raise BadSchemaNodeType(sn, "list")
        sel = {}
        for j in range(len(ks)):
            knod = sn.get_data_child(*sn.keys[j])
            val = knod.type.parse_value(unquote(ks[j]))
            sel[knod.iname()] = val
        return EntryKeys(sel)

class InstanceIdParser(InstancePathParser):
    """Parser for YANG instance identifiers."""

    def parse(self) -> "InstanceRoute":
        """Parse instance identifier."""
        res = []
        sn = Context.schema
        while True:
            self.char("/")
            mnam, cn = self._member_name(sn)
            res.append(mnam)
            try:
                next = self.peek()
            except EndOfInput:
                return res
            if next == "[":
                self.offset += 1
                self.skip_ws()
                if self.peek() in "0123456789":
                    ind = self.unsigned_integer() - 1
                    if ind < 0:
                        raise UnexpectedInput(self, "positive index")
                    self.skip_ws()
                    self.char("]")
                    res.append(EntryIndex(ind))
                elif isinstance(cn, LeafListNode):
                    self.char(".")
                    res.append(EntryValue(self._get_value(cn)))
                else:
                    res.append(self._key_predicates(cn))
                if self.at_end(): return res
            sn = cn

    def _get_value(self, tn: "TerminalNode") -> ScalarValue:
        self.skip_ws()
        self.char("=")
        self.skip_ws()
        quote = self.one_of("'\"")
        val = self.up_to(quote)
        self.skip_ws()
        self.char("]")
        return tn.type.parse_value(val)

    def _key_predicates(self, sn: "ListNode") -> EntryKeys:
        "Parse one or more key predicates."""
        sel = {}
        while True:
            name, ns = self.prefixed_name()
            knod = sn.get_data_child(name, ns)
            val = self._get_value(knod)
            sel[knod.iname()] = val
            try:
                next = self.peek()
            except EndOfInput:
                break
            if next != "[": break
            self.offset += 1
            self.skip_ws()
        return EntryKeys(sel)

    def _key_values(self, sn: "SequenceNode") -> EntryKeys:
        """Parse leaf-list value or list keys."""
        try:
            keys = self.up_to("/")
        except EndOfInput:
            keys = self.remaining()
        if not keys:
            raise UnexpectedInput(self, "entry value or keys")
        if isinstance(sn, LeafListNode):
            return EntryValue(sn.type.parse_value(unquote(keys)))
        ks = keys.split(",")
        try:
            if len(ks) != len(sn.keys):
                raise UnexpectedInput(self,
                                      "exactly {} keys".format(len(sn.keys)))
        except AttributeError:
            raise BadSchemaNodeType(sn, "list")
        sel = {}
        for j in range(len(ks)):
            knod = sn.get_data_child(*sn.keys[j])
            val = knod.type.parse_value(unquote(ks[j]))
            sel[knod.iname()] = val
        return EntryKeys(sel)

class InstanceException(YangsonException):
    """Base class for exceptions related to operations on instance nodes."""

    def __init__(self, inst: InstanceNode):
        self.instance = inst

    def __str__(self):
        return "[" + self.instance.json_pointer() + "]"

class NonexistentInstance(InstanceException):
    """Attempt to access an instance node that doesn't exist."""

    def __init__(self, inst: InstanceNode, detail: str) -> None:
        super().__init__(inst)
        self.detail = detail

    def __str__(self):
        return "{} {}".format(super().__str__(), self.detail)

class InstanceTypeError(InstanceException):
    """A method is called for a wrong type of instance node."""

    def __init__(self, inst: InstanceNode, detail: str) -> None:
        super().__init__(inst)
        self.detail = detail

    def __str__(self):
        return "{} {}".format(super().__str__(), self.detail)

class DuplicateMember(InstanceException):
    """Attempt to create a member that already exists."""

    def __init__(self, inst: InstanceNode, name: InstanceName) -> None:
        super().__init__(inst)
        self.name = name

    def __str__(self):
        return "{} duplicate member {}".format(super().__str__(), self.name)

class MandatoryMember(InstanceException):
    """Attempt to remove a mandatory member."""

    def __init__(self, inst: InstanceNode, name: InstanceName) -> None:
        super().__init__(inst)
        self.name = name

    def __str__(self):
        return "{} member {}".format(super().__str__(), self.name)

class MinElements(InstanceException):
    """An array becomes shorter than min-elements."""

    def __str__(self):
        return "{} less than {} entries".format(
            super().__str__(), self.instance.schema_node.min_elements)

class MaxElements(InstanceException):
    """An array becomes shorter than max-elements."""

    def __str__(self):
        return "{} more than {} entries".format(
            super().__str__(), self.instance.schema_node.max_elements)

InstanceRoute = List[InstanceSelector]

from .schema import (AnydataNode, CaseNode, ChoiceNode, DataNode, InternalNode,
                     LeafNode, LeafListNode, ListNode,
                     NonexistentSchemaNode, SequenceNode, TerminalNode)
