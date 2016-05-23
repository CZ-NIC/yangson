"""Classes related to JSON-encoded instance data."""

import copy
from datetime import datetime
from typing import Any, Callable, List, Tuple
from .constants import YangsonException
from .typealiases import *

# Local type aliases

Value = Union[ScalarValue, "ArrayValue", "ObjectValue"]
"""Instance node value."""

class StructuredValue:
    """Abstract class for array and object values."""

    def __init__(self, ts: datetime) -> None:
        """Initialize class instance.

        :param ts: creation timestamp
        """
        self.timestamp = ts if ts else datetime.now()

    def stamp(self) -> None:
        """Update the receiver's timestamp to current time."""
        self.timestamp = datetime.now()

    def __eq__(self, val: "StructuredValue") -> bool:
        """Return ``True`` if the receiver equal to `val`.

        :param val: value to compare
        """
        return self.__class__ == val.__class__ and hash(self) == hash(val)

class ArrayValue(StructuredValue, list):
    """Array values corresponding to YANG lists and leaf-lists."""

    def __init__(self, val: List[Value], ts: datetime=None):
        StructuredValue.__init__(self, ts)
        list.__init__(self, val)

    def __hash__(self) -> int:
        """Return integer hash value for the receiver."""
        return tuple([ x.__hash__() for x in self]).__hash__()

class ObjectValue(StructuredValue, dict):
    """Array values corresponding to YANG container."""

    def __init__(self, val: Dict[InstanceName, Value], ts: datetime = None):
        StructuredValue.__init__(self, ts)
        dict.__init__(self, val)

    def __hash__(self) -> int:
        """Return integer hash value for the receiver."""
        sks = sorted(self.keys())
        return tuple([ (k, self[k].__hash__()) for k in sks ]).__hash__()

class JSONPointer(tuple):
    """This class represents JSON Pointer [RFC 6901]."""

    def __str__(self) -> str:
        """Return string representation of the receiver."""
        return "/" + "/".join([ str(c) for c in self ])

class InstanceNode:
    """YANG data node instance implemented as a zipper structure."""

    def __init__(self, value: Value, parent: Optional["InstanceNode"],
                 ts: datetime) -> None:
        """Initialize the class instance.

        :param value: instance value
        """
        self.value = value
        self.parent = parent
        self.timestamp = ts

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

    def goto(self, ii: "InstanceIdentifier") -> "InstanceNode":
        """Return an instance in the receiver's subtree.

        :param ii: instance route (relative to the receiver)
        """
        inst = self # type: "InstanceNode"
        for sel in ii:
            inst = sel.goto_step(inst)
        return inst

    def peek(self, ii: "InstanceIdentifier") -> Value:
        """Return a value in the receiver's subtree.

        :param ii: instance route (relative to the receiver)
        """
        val = self.value
        for sel in ii:
            val = sel.peek_step(val)
        return val

    def update(self, newval: Value) -> "InstanceNode":
        """Return a copy of the receiver with a new value.

        :param newval: new value
        """
        return self._copy(newval, datetime.now())

    def member(self, name: InstanceName) -> "ObjectMember":
        if not isinstance(self.value, ObjectValue):
            raise InstanceTypeError(self, "member of non-object")
        obj = self.value.copy()
        try:
            return ObjectMember(name, obj, obj.pop(name), self,
                                self.value.timestamp)
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None

    def new_member(self, name: InstanceName, value: Value) -> "ObjectMember":
        if not isinstance(self.value, ObjectValue):
            raise InstanceTypeError(self, "member of non-object")
        if name in self.value:
            raise DuplicateMember(self, name)
        return ObjectMember(name, self.value, value, self, datetime.now())

    def remove_member(self, name: InstanceName) -> "InstanceNode":
        if not isinstance(self.value, ObjectValue):
            raise InstanceTypeError(self, "member of non-object")
        val = self.value.copy()
        try:
            del val[name]
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None
        ts = datetime.now()
        return self._copy(ObjectValue(val, ts), ts)

    def entry(self, index: int) -> "ArrayEntry":
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "entry of non-array")
        try:
            return ArrayEntry(val[:index], val[index+1:], val[index], self,
                              val.timestamp)
        except IndexError:
            raise NonexistentInstance(self, "entry " + str(index)) from None

    def last_entry(self) -> "ArrayEntry":
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "last entry of non-array")
        try:
            return ArrayEntry(val[:-1], [], val[-1], self, val.timestamp)
        except IndexError:
            raise NonexistentInstance(self, "last of empty") from None

    def xpath_nodes(self) -> List["ArrayEntry"]:
        """Return the list of all receiver's instances."""
        val = self.value
        return ([ self.entry(i) for i in range(len(val)) ] if
                isinstance(val, ArrayValue) else [self])

    def remove_entry(self, index: int) -> "InstanceNode":
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "entry of non-array")
        ts = datetime.now()
        try:
            return self._copy(ArrayValue(val[:index] + val[index+1:], ts), ts)
        except IndexError:
            raise NonexistentInstance(self, "entry " + str(index)) from None

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

    def children(self, name: InstanceName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath children."""
        if not isinstance(self.value, ObjectValue): return []
        if name is None:
            names = sorted(self.value.keys())
            res = []
            for n in sorted(self.value.keys()):
                res += self.member(n).xpath_nodes()
            return res
        return self.member(name).xpath_nodes() if name in self.value else []

    def descendants(self, name: InstanceName = None,
                    with_self: bool = False) -> List["InstanceNode"]:
        """Return the list of receiver's XPath descendants."""
        res = ([self] if with_self and (name is None or self.name == name)
               else [])
        for c in self.children(name):
            res.append(c)
            res += c.descendants(name)
        return res

class RootNode(InstanceNode):
    """This class represents the root of the instance tree."""

    def __init__(self, value: Value, ts: datetime) -> None:
        super().__init__(value, None, ts)
        self.name = None

    def _copy(self, newval: Value = None,
              newts: datetime = None) -> "InstanceNode":
        return RootNode(newval if newval else self.value,
                          newts if newts else self._timestamp)

    def ancestors_or_self(self, name: InstanceName = None,
                          with_root: bool = False) -> List["InstanceNode"]:
        """Return the list of receiver's XPath ancestors."""
        return [self] if name is None and with_root else []

    def ancestors(self, name: InstanceName = None,
                  with_root: bool = False) -> List["InstanceNode"]:
        """Return the list of receiver's XPath ancestors."""
        return []

    def preceding_siblings(self,
                           name: InstanceName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath preceding-siblings."""
        return []

    def following_siblings(self,
                           name: InstanceName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath following-siblings."""
        return []

class ObjectMember(InstanceNode):
    """This class represents an object member."""

    def __init__(self, name: InstanceName, siblings: Dict[InstanceName, Value],
                 value: Value, parent: InstanceNode,
                 ts: datetime ) -> None:
        super().__init__(value, parent, ts)
        self.name = name
        self.siblings = siblings

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
                           newval if newval else self.value, self.parent,
                           newts if newts else self._timestamp)

    def sibling(self, name: InstanceName) -> "InstanceNode":
        try:
            sib = self.siblings.copy()
            newval = sib.pop(name)
            sib[self.name] = self.value
            return ObjectMember(name, sib, newval, self.parent, self.timestamp)
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None

    def ancestors_or_self(self, name: InstanceName = None,
                          with_root: bool = False) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors-or-self."""
        res = self.up().ancestors_or_self(name, with_root)
        if name is None or self.name == name:
            res.append(self)
        return res

    def ancestors(self, name: InstanceName = None,
                  with_root: bool = False) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors."""
        return self.up().ancestors_or_self(name, with_root)

    def preceding_siblings(self,
                           name: InstanceName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath preceding-siblings."""
        if name is None:
            prec = sorted([ n for n in self.siblings if n < self.name ],
                          reverse=True)
            res = []
            for n in prec:
                res += self.sibling(n).xpath_nodes()
            return res
        return (self.sibling(name).xpath_nodes() if
                name < self.name and name in self.siblings else [])

    def following_siblings(self,
                           name: InstanceName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath following-siblings."""
        if name is None:
            foll = sorted([ n for n in self.siblings if n > self.name ])
            res = []
            for n in foll:
                res += self.sibling(n).xpath_nodes()
            return res
        return (self.sibling(name).xpath_nodes() if
                name > self.name and name in self.siblings else [])

class ArrayEntry(InstanceNode):
    """This class represents an array entry."""

    def __init__(self, before: List[Value], after: List[Value], value: Value,
                 parent: InstanceNode, ts: datetime = None) -> None:
        super().__init__(value, parent, ts)
        self.before = before
        self.after = after

    @property
    def name(self) -> Optional[InstanceName]:
        """Return the name of the receiver."""
        return self.parent.name

    @property
    def namespace(self) -> Optional[YangIdentifier]:
        """Return the receiver's namespace."""
        return self.parent.namespace

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
                          newval if newval else self.value, self.parent,
                          newts if newts else self._timestamp)

    def next(self) -> "ArrayEntry":
        try:
            newval = self.after[0]
        except IndexError:
            raise NonexistentInstance(self, "next of last") from None
        return ArrayEntry(self.before + [self.value], self.after[1:],
                          newval, self.parent, self.timestamp)

    def previous(self) -> "ArrayEntry":
        try:
            newval = self.before[-1]
        except IndexError:
            raise NonexistentInstance(self, "previous of first") from None
        return ArrayEntry(self.before[:-1], [self.value] + self.after,
                          newval, self.parent, self.timestamp)

    def insert_before(self, value: Value):
        return ArrayEntry(self.before, [self.value] + self.after, value,
                          self.parent, datetime.now())

    def insert_after(self, value: Value):
        return ArrayEntry(self.before + [self.value], self.after, value,
                          self.parent, datetime.now())

    def ancestors_or_self(self, name: InstanceName = None,
                          with_root: bool = False) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors-or-self."""
        res = self.up().ancestors(name, with_root)
        if name is None or name == self.name:
            res.append(self)
        return res

    def ancestors(self, name: InstanceName = None,
                  with_root: bool = False) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors."""
        return self.up().ancestors(name, with_root)

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
                           name: InstanceName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath preceding-siblings."""
        if name is None:
            return self.preceding_entries() + self.up().preceding_siblings()
        return (self.preceding_entries() if name == self.name
                else self.up().preceding_siblings(name))

    def following_siblings(self,
                           name: InstanceName = None) -> List["InstanceNode"]:
        """Return the list of receiver's XPath following-siblings."""
        if name is None:
            return self.following_entries() + self.up().following_siblings()
        return (self.following_entries() if name == self.name
                else self.up().following_siblings(name))

class InstanceIdentifier(list):
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
        return "[" + str(self.instance.path()) + "] "

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
        return "{} member {}".format(super().__str__(), self.name)
