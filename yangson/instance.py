"""Classes related to instance data."""

from datetime import datetime
from typing import Any, Callable, List, Tuple
from .constants import YangsonException
from .instvalue import ArrayValue, ObjectValue, Value
from .schema import CaseNode, DataNode, NonexistentSchemaNode
from .typealiases import *

class JSONPointer(tuple):
    """This class represents JSON Pointer [RFC 6901]."""

    def __str__(self) -> str:
        """Return string representation of the receiver."""
        return "/" + "/".join([ str(c) for c in self ])

class InstanceNode:
    """YANG data node instance implemented as a zipper structure."""

    def __init__(self, value: Value, parent: Optional["InstanceNode"],
                 schema_node: DataNode, ts: datetime) -> None:
        """Initialize the class instance.

        :param value: instance value
        """
        self.value = value
        self.parent = parent
        self.schema_node = schema_node
        self.timestamp = ts

    @property
    def qualName(self) -> Optional[QualName]:
        """Return the receiver's qualified name."""
        return None

    @property
    def namespace(self) -> Optional[YangIdentifier]:
        """Return the receiver's namespace."""
        return None

    def path(self) -> str:
        """Return JSONPointer of the receiver."""
        parents = []
        inst = self
        while inst.parent:
            parents.append(inst)
            inst = inst.parent
        return JSONPointer([ i._pointer_fragment() for i in parents[::-1] ])

    def update_from_raw(self, value: RawValue) -> Value:
        """Update the receiver's value from a raw value."""
        return self.update(self.schema_node.from_raw(value))

    def up(self) -> "InstanceNode":
        """Ascend to the parent instance node."""
        try:
            ts = max(self.timestamp, self.parent.timestamp)
            return self.parent._copy(self.zip(), ts)
        except AttributeError:
            raise NonexistentInstance(self, "up of top") from None

    def top(self) -> "InstanceNode":
        inst = self
        while inst.parent:
            inst = inst.up()
        return inst

    def goto(self, ii: "InstancePath") -> "InstanceNode":
        """Return an instance in the receiver's subtree.

        :param ii: instance route (relative to the receiver)
        """
        inst = self # type: "InstanceNode"
        for sel in ii:
            inst = sel.goto_step(inst)
        return inst

    def peek(self, ii: "InstancePath") -> Optional[Value]:
        """Return a value in the receiver's subtree.

        :param ii: instance route (relative to the receiver)
        """
        val = self.value
        for sel in ii:
            val = sel.peek_step(val)
            if val is None: return None
        return val

    def update(self, newval: Value) -> "InstanceNode":
        """Return a copy of the receiver with a new value.

        :param newval: new value
        """
        return self._copy(newval, datetime.now())

    def _member_schema_node(self, name: InstanceName) -> DataNode:
        qname = self.schema_node.iname2qname(name)
        res = self.schema_node.get_data_child(*qname)
        if res is None:
            raise NonexistentSchemaNode(qname)
        return res

    def member(self, name: InstanceName) -> "ObjectMember":
        csn = self._member_schema_node(name)
        sibs = self.value.copy()
        try:
            return ObjectMember(name, sibs, sibs.pop(name), self,
                                csn, self.value.timestamp)
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None

    def put_member(self, name: InstanceName, value: Value) -> "InstanceNode":
        csn = self._member_schema_node(name)
        newval = self.value.copy()
        newval[name] = value
        sn = csn
        while sn is not self.schema_node:
            if not isinstance(sn, CaseNode): continue
            for case in [ c for c in sn.parent.children if c is not sn ]:
                for x in c.data_children():
                    newval.pop(x.iname(), None)
        ts = datetime.now()
        return self._copy(ObjectValue(newval, ts) , ts)

    def delete_member(self, name: InstanceName) -> "InstanceNode":
        if name not in self.value:
            raise NonexistentInstance(self, "member " + name) from None
        csn = self._member_schema_node(name)
        if csn.mandatory: raise MandatoryMember(self, name)
        newval = self.value.copy()
        del newval[name]
        ts = datetime.now()
        return self._copy(ObjectValue(newval, ts), ts)

    def entry(self, index: int) -> "ArrayEntry":
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "entry of non-array")
        try:
            return ArrayEntry(val[:index], val[index+1:], val[index], self,
                              self.schema_node, val.timestamp)
        except IndexError:
            raise NonexistentInstance(self, "entry " + str(index)) from None

    def last_entry(self) -> "ArrayEntry":
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "last entry of non-array")
        try:
            return ArrayEntry(val[:-1], [], val[-1], self,
                              self.schema_node, val.timestamp)
        except IndexError:
            raise NonexistentInstance(self, "last of empty") from None

    def xpath_nodes(self) -> List["InstanceNode"]:
        """Return the list of all receiver's instances."""
        val = self.value
        return ([ self.entry(i) for i in range(len(val)) ] if
                isinstance(val, ArrayValue) else [self])

    def delete_entry(self, index: int) -> "InstanceNode":
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "entry of non-array")
        if index >= len(val):
            raise NonexistentInstance(self, "entry " + str(index)) from None
        if self.schema_node.min_elements == len(val):
            raise MinElements(self)
        ts = datetime.now()
        return self._copy(ArrayValue(val[:index] + val[index+1:], ts), ts)

    def look_up(self, keys: Dict[InstanceName, ScalarValue]) -> "ArrayEntry":
        """Return the entry with matching keys."""
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

    def children(self, qname: QualName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath children."""
        if not isinstance(self.value, ObjectValue): return []
        if qname is None:
            names = sorted(self.value.keys())
            res = []
            for n in sorted(self.value.keys()):
                res += self.member(n).xpath_nodes()
            return res
        iname = (qname[0] if self.namespace == qname[1]
                 else qname[1] + ":" + qname[0])
        return self.member(iname).xpath_nodes() if iname in self.value else []

    def descendants(self, qname: QualName = None,
                    with_self: bool = False) -> List["InstanceNode"]:
        """Return the list of receiver's XPath descendants."""
        res = [self] if with_self and self.qualName == qname else []
        for c in self.children(qname):
            res.append(c)
            res += c.descendants(qname)
        return res

class RootNode(InstanceNode):
    """This class represents the root of the instance tree."""

    def __init__(self, value: Value, schema_node: DataNode,
                 ts: datetime) -> None:
        super().__init__(value, None, schema_node, ts)
        self.name = None

    def _copy(self, newval: Value = None,
              newts: datetime = None) -> "InstanceNode":
        return RootNode(newval if newval else self.value, self.schema_node,
                          newts if newts else self._timestamp)

    def ancestors_or_self(self, qname: QualName = None,
                          with_root: bool = False) -> List["InstanceNode"]:
        """Return the list of receiver's XPath ancestors."""
        return [self] if qname is None and with_root else []

    def ancestors(self, qname: QualName = None,
                  with_root: bool = False) -> List["InstanceNode"]:
        """Return the list of receiver's XPath ancestors."""
        return []

    def preceding_siblings(self,
                           qname: QualName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath preceding-siblings."""
        return []

    def following_siblings(self,
                           qname: QualName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath following-siblings."""
        return []

class ObjectMember(InstanceNode):
    """This class represents an object member."""

    def __init__(self, name: InstanceName, siblings: Dict[InstanceName, Value],
                 value: Value, parent: InstanceNode,
                 schema_node: DataNode, ts: datetime ) -> None:
        super().__init__(value, parent, schema_node, ts)
        self.name = name
        self.siblings = siblings

    @property
    def qualName(self) -> Optional[QualName]:
        """Return the receiver's qualified name."""
        p, s, loc = self.name.partition(":")
        return (loc, p) if s else (p, self.parent.namespace)

    @property
    def namespace(self) -> Optional[YangIdentifier]:
        """Return the receiver's namespace."""
        p, s, loc = self.name.partition(":")
        return p if s else self.parent.namespace

    def zip(self) -> ObjectValue:
        """Zip the receiver into an object and return it."""
        res = ObjectValue(self.siblings.copy(), self.timestamp)
        res[self.name] = self.value
        return res

    def _pointer_fragment(self) -> str:
        return self.name

    def _copy(self, newval: Value = None,
              newts: datetime = None) -> "ObjectMember":
        return ObjectMember(self.name, self.siblings,
                           newval if newval else self.value,
                           self.parent, self.schema_node,
                           newts if newts else self._timestamp)

    def sibling(self, name: InstanceName) -> "InstanceNode":
        ssn = self.parent._member_schema_node(name)
        try:
            sibs = self.siblings.copy()
            newval = sibs.pop(name)
            sibs[self.name] = self.value
            return ObjectMember(name, sibs, newval, self.parent,
                                ssn, self.timestamp)
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None

    def ancestors_or_self(self, qname: QualName = None,
                          with_root: bool = False) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors-or-self."""
        res = [] if qname and self.qualName != qname else [self]
        return res + self.up().ancestors_or_self(qname, with_root)

    def ancestors(self, qname: QualName = None,
                  with_root: bool = False) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors."""
        return self.up().ancestors_or_self(qname, with_root)

    def preceding_siblings(self,
                           qname: QualName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath preceding-siblings."""
        if qname is None:
            prec = sorted([ n for n in self.siblings if n < self.name ],
                          reverse=True)
            res = []
            for n in prec:
                res += self.sibling(n).xpath_nodes()
            return res
        iname = (qname[0] if self.parent.namespace == qname[1]
                 else qname[1] + ":" + qname[0])
        return (self.sibling(iname).xpath_nodes() if
                iname < self.name and iname in self.siblings else [])

    def following_siblings(self,
                           qname: QualName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath following-siblings."""
        if qname is None:
            foll = sorted([ n for n in self.siblings if n > self.name ])
            res = []
            for n in foll:
                res += self.sibling(n).xpath_nodes()
            return res
        iname = (qname[0] if self.parent.namespace == qname[1]
                 else qname[1] + ":" + qname[0])
        return (self.sibling(iname).xpath_nodes() if
                iname > self.name and iname in self.siblings else [])

class ArrayEntry(InstanceNode):
    """This class represents an array entry."""

    def __init__(self, before: List[Value], after: List[Value],
                 value: Value, parent: InstanceNode,
                 schema_node: DataNode, ts: datetime = None) -> None:
        super().__init__(value, parent, schema_node, ts)
        self.before = before
        self.after = after

    @property
    def name(self) -> Optional[InstanceName]:
        """Return the name of the receiver."""
        return self.parent.name

    @property
    def qualName(self) -> Optional[QualName]:
        """Return the receiver's qualified name."""
        return self.parent.qualName

    @property
    def namespace(self) -> Optional[YangIdentifier]:
        """Return the receiver's namespace."""
        return self.parent.namespace

    def update_from_raw(self, value: RawValue) -> Value:
        """Update the receiver's value from a raw value.

        This method overrides the superclass method.
        """
        return self.update(self.schema_node._entry_from_raw(value))

    def zip(self) -> ArrayValue:
        """Zip the receiver into an array and return it."""
        res = ArrayValue(self.before.copy(), self.timestamp)
        res.append(self.value)
        res += self.after
        return res

    def _pointer_fragment(self) -> int:
        return len(self.before)

    def _copy(self, newval: Value = None,
              newts: datetime = None) -> "ArrayEntry":
        return ArrayEntry(self.before, self.after,
                          newval if newval else self.value,
                          self.parent, self.schema_node,
                          newts if newts else self._timestamp)

    def next(self) -> "ArrayEntry":
        try:
            newval = self.after[0]
        except IndexError:
            raise NonexistentInstance(self, "next of last") from None
        return ArrayEntry(self.before + [self.value], self.after[1:], newval,
                          self.parent, self.schema_node, self.timestamp)

    def previous(self) -> "ArrayEntry":
        try:
            newval = self.before[-1]
        except IndexError:
            raise NonexistentInstance(self, "previous of first") from None
        return ArrayEntry(self.before[:-1], [self.value] + self.after, newval,
                          self.parent, self.schema_node, self.timestamp)

    def insert_before(self, value: Value):
        if (self.schema_node.max_elements ==
            len(self.before) + len(self.after) + 1):
            raise MaxElements(self)
        return ArrayEntry(self.before, [self.value] + self.after, value,
                          self.parent, self.schema_node, datetime.now())

    def insert_after(self, value: Value):
        if (self.schema_node.max_elements ==
            len(self.before) + len(self.after) + 1):
            raise MaxElements(self)
        return ArrayEntry(self.before + [self.value], self.after, value,
                          self.parent, self.schema_node, datetime.now())

    def ancestors_or_self(self, qname: QualName = None,
                          with_root: bool = False) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors-or-self."""
        res = [] if qname and self.qualName != qname else [self]
        return res + self.up().ancestors(qname, with_root)

    def ancestors(self, qname: QualName = None,
                  with_root: bool = False) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors."""
        return self.up().ancestors(qname, with_root)

    def preceding_entries(self) -> List["ArrayEntry"]:
        """Return the list of instances preceding in the array."""
        res = []
        ent = self
        for i in range(len(self.before)):
            ent = ent.previous()
            res.append(ent)
        return res

    def following_entries(self) -> List["ArrayEntry"]:
        """Return the list of instances following in the array."""
        res = []
        ent = self
        for i in range(len(self.after)):
            ent = ent.next()
            res.append(ent)
        return res

    def preceding_siblings(self,
                           qname: QualName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath preceding-siblings."""
        if qname is None:
            return self.preceding_entries() + self.up().preceding_siblings()
        return (self.preceding_entries() if self.qualName == qname
                else self.up().preceding_siblings(qname))

    def following_siblings(self,
                           qname: QualName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath following-siblings."""
        if qname is None:
            return self.following_entries() + self.up().following_siblings()
        return (self.following_entries() if self.qualName == qname
                else self.up().following_siblings(name))

class InstancePath(list):
    """Instance route."""

    def __str__(self):
        """Return a string representation of the receiver."""
        return "".join([ str(i) for i in self ])

class InstanceSelector:
    """Components of instance identifers."""
    pass

class MemberName(InstanceSelector):
    """Selectors of object members."""

    def __init__(self, name: InstanceName) -> None:
        """Initialize the class instance.

        :param name: member name
        """
        self.name = name

    def __str__(self) -> str:
        """Return a string representation of the receiver."""
        return "/" + self.name

    def __eq__(self, other: "MemberName") -> bool:
        return self.name == other.name

    def peek_step(self, obj: ObjectValue) -> Value:
        """Return the member of `obj` addressed by the receiver.

        :param obj: current object
        """
        return obj.get(self.name)

    def goto_step(self, inst: InstanceNode) -> InstanceNode:
        """Return member instance of `inst` addressed by the receiver.

        :param inst: current instance
        """
        return inst.member(self.name)

class EntryIndex(InstanceSelector):
    """Numeric selectors for a list or leaf-list entry."""

    def __init__(self, index: int) -> None:
        """Initialize the class instance.

        :param index: index of an entry
        """
        self.index = index

    def __str__(self) -> str:
        """Return a string representation of the receiver."""
        return "[{0:d}]".format(self.index)

    def __eq__(self, other: "EntryIndex") -> bool:
        return self.index == other.index

    def peek_step(self, arr: ArrayValue) -> Value:
        """Return the entry of `arr` addressed by the receiver.

        :param arr: current array
        """
        try:
            return arr[self.index]
        except IndexError:
            return None

    def goto_step(self, inst: InstanceNode) -> InstanceNode:
        """Return member instance of `inst` addressed by the receiver.

        :param inst: current instance
        """
        return inst.entry(self.index)

class EntryValue(InstanceSelector):
    """Value-based selectors of an array entry."""

    def __init__(self, value: ScalarValue) -> None:
        """Initialize the class instance.

        :param value: value of a leaf-list entry
        """
        self.value = value

    def __str__(self) -> str:
        """Return a string representation of the receiver."""
        return "[.=" + str(self.value) +"]"

    def __eq__(self, other: "EntryValue") -> bool:
        return self.value == other.value

    def peek_step(self, arr: ArrayValue) -> Value:
        """Return the entry of `arr` addressed by the receiver.

        :param arr: current array
        """
        try:
            return arr[arr.index(self.value)]
        except ValueError:
            return None

    def goto_step(self, inst: InstanceNode) -> InstanceNode:
        """Return member instance of `inst` addressed by the receiver.

        :param inst: current instance
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

        :param keys: dictionary with keys of an entry
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

        :param arr: current array
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

        :param inst: current instance
        """
        return inst.look_up(self.keys)

# Exceptions

class InstanceError(YangsonException):
    """Exceptions related to operations on the instance structure."""

    def __init__(self, inst: InstanceNode):
        self.instance = inst

    def __str__(self):
        return "[" + str(self.instance.path()) + "]"

class NonexistentInstance(InstanceError):
    """Exception to raise when moving out of bounds."""

    def __init__(self, inst: InstanceNode, text: str) -> None:
        super().__init__(inst)
        self.text = text

    def __str__(self):
        return "{} {}".format(super().__str__(), self.text)

class InstanceTypeError(InstanceError):
    """Exception to raise when calling a method for a wrong instance type."""

    def __init__(self, inst: InstanceNode, text: str) -> None:
        super().__init__(inst)
        self.text = text

    def __str__(self):
        return "{} {}".format(super().__str__(), self.text)

class DuplicateMember(InstanceError):
    """Exception to raise on attempt to create a member that already exists."""

    def __init__(self, inst: InstanceNode, name: InstanceName) -> None:
        super().__init__(inst)
        self.name = name

    def __str__(self):
        return "{} duplicate member {}".format(super().__str__(), self.name)

class MandatoryMember(InstanceError):
    """Exception to raise on attempt to remove a mandatory member."""

    def __init__(self, inst: InstanceNode, name: InstanceName) -> None:
        super().__init__(inst)
        self.name = name

    def __str__(self):
        return "{} mandatory member {}".format(super().__str__(), self.name)

class MinElements(InstanceError):
    """Exception to raise if an array becomes shorter than min-elements."""

    def __str__(self):
        return "{} less than {} entries".format(
            super().__str__(), self.instance.schema_node.min_elements)

class MaxElements(InstanceError):
    """Exception to raise if an array becomes longer than max-elements."""

    def __str__(self):
        return "{} more than {} entries".format(
            super().__str__(), self.instance.schema_node.max_elements)
