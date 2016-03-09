"""Classes related to JSON-encoded instance data."""

from datetime import datetime
from typing import Any, Callable, List, Tuple
from .exception import YangsonException
from .typealiases import *

# Local type aliases

Value = Union[ScalarValue, "ArrayValue", "ObjectValue"]
"""Instance value."""

class StructuredValue:
    """Abstract class for array and object values."""

    def __init__(self, ts: datetime = None) -> None:
        """Initialize class instance.

        :param ts: creation time stamp
        """
        self.last_modified = ts

    def time_stamp(self, ts: datetime = None) -> None:
        """Update the receiver's last-modified time stamp.

        :param ts: new time stamp (if ``None``, set it to current time)
        """
        self.last_modified = ts if ts else datetime.now()

    def __eq__(self, val: "StructuredValue") -> bool:
        """Is the receiver equal to `val`?

        :param val: value to compare
        """
        return self.__class__ == val.__class__ and hash(self) == hash(val)

class ArrayValue(StructuredValue, list):
    """Array values corresponding to YANG lists and leaf-lists."""

    def __hash__(self) -> int:
        """Return an integer hash value for the receiver."""
        return tuple([ x.__hash__() for x in self]).__hash__()

class ObjectValue(StructuredValue, dict):
    """Array values corresponding to YANG container."""

    def __hash__(self) -> int:
        """Return an integer hash value for the receiver."""
        sks = sorted(self.keys())
        return tuple([ (k, self[k].__hash__()) for k in sks ]).__hash__()

class Crumb:
    """Class of crumb objects representing zipper context."""

    def __init__(self, parent: "Crumb", ts: datetime) -> None:
        """Initialize the class instance.

        :param parent: parent crumb
        :param ts: receiver's time stamp
        """
        self.parent = parent
        self._timestamp = ts

    @property
    def timestamp(self) -> datetime:
        """Return receiver's timestamp (or parent's if ``None``)."""
        return self._timestamp if self._timestamp else self.parent.timestamp

    def pointer(self):
        """Return JSON pointer of the receiver."""

        return ("{}/{}".format(self.parent.pointer(), self.pointer_fragment())
                if self.parent else "")

class MemberCrumb(Crumb):
    """Zipper contexts for an object member."""

    def __init__(self, name: QName, obj: Dict[QName, Value], parent: Crumb,
                 ts: datetime = None) -> None:
        """Initialize the class instance.

        :param name: name of an object member that's the current focus
        :param obj: an object containing the remaining members
        :param parent: parent crumb
        :param ts: receiver's time stamp
        """
        super().__init__(parent, ts)
        self.name = name
        self.object = obj

    def pointer_fragment(self) -> QName:
        """Return the JSON pointer fragment of the focused value."""
        return self.name

    def zip(self, value: Value) -> ObjectValue:
        """Put focused value back to a copy of the object and return it.

        :param value: value of the focused member
        """
        res = ObjectValue(self.timestamp)
        res[self.name] = value
        res.update(self.object)
        return res

    def _copy(self, ts: datetime) -> "MemberCrumb":
        """Return a shallow copy of the receiver.

        :param ts: timestamp of the copy
        """
        return MemberCrumb(self.name, self.object, self.parent, ts)

class EntryCrumb(Crumb):
    """Zipper contexts for an array entry."""

    def __init__(self, before: List[Value], after: List[Value],
                 parent: Crumb, ts: datetime = None) -> None:
        """Initialize the class instance.

        :param before: array entries before the focused entry
        :param after: array entries after the focused entry
        :param parent: parent crumb
        :param ts: receiver's time stamp
        """
        super().__init__(parent, ts)
        self.before = before
        self.after = after

    def pointer_fragment(self) -> int:
        """Return the JSON pointer fragment of the focused value."""
        return len(self.before)

    def zip(self, value: Value) -> ArrayValue:
        """Concatenate the receiver's parts with the focused entry.

        :param value: value of the focused entry
        """
        res = ArrayValue(self.timestamp)
        res.extend(self.before)
        res.append(value)
        res.extend(self.after)
        return res

    def _copy(self, ts: datetime) -> "EntryCrumb":
        """Return a shallow copy of the receiver.

        :param ts: timestamp of the copy
        """
        return EntryCrumb(self.before, self.after, self.parent, ts)

class Instance:
    """YANG data node instance implemented as a zipper structure."""

    def __init__(self, value: Value, crumb: Crumb) -> None:
        """Initialize the class instance.

        :param value: instance value
        :param crumb: receiver's crumb
        """
        self.value = value
        self.crumb = crumb

    def goto(self, ii: "InstanceIdentifier") -> "Instance":
        """Return an instance in the receiver's subtree.

        :param ii: instance identifier (relative to the receiver)
        """
        inst = self # type: "Instance"
        for sel in ii:
            inst = sel.goto_step(inst)
        return inst

    def peek(self, ii: "InstanceIdentifier") -> Value:
        """Return a value in the receiver's subtree.

        :param ii: instance identifier (relative to the receiver)
        """
        val = self.value
        for sel in ii:
            val = sel.peek_step(val)
        return val

    def update(self, newval: Value) -> "Instance":
        """Return a copy of the receiver with a new value.

        :param newval: new value
        """
        return Instance(newval, self.crumb._copy(datetime.now()))

    def up(self) -> "Instance":
        """Ascend to the parent instance."""
        try:
            if self.crumb._timestamp:
                self.crumb.parent._timestamp = self.crumb._timestamp
            return Instance(self.crumb.zip(self.value), self.crumb.parent)
        except (AttributeError, IndexError):
            raise NonexistentInstance(self, "up of top") from None

    def is_top(self) -> bool:
        """Is the receiver the top-level instance?"""
        return self.crumb.parent is None

    def top(self) -> "Instance":
        inst = self
        while inst.crumb.parent:
            inst = inst.up()
        return inst

    def member(self, name: QName) -> "Instance":
        try:
            obj = self.value.copy()
            return Instance(obj.pop(name), MemberCrumb(name, obj, self.crumb))
        except (TypeError, AttributeError):
            raise InstanceTypeError(self, "member of non-object") from None
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None

    def new_member(self, name: QName, value: Value) -> "Instance":
        if not isinstance(self.value, ObjectValue):
            raise InstanceTypeError(self, "member of non-object")
        if name in self.value:
            raise DuplicateMember(self, name)
        return Instance(value, MemberCrumb(name, self.value, self.crumb,
                                           datetime.now()))

    def remove_member(self, name: QName) -> "Instance":
        try:
            val = self.value.copy()
            del val[name]
            return Instance(val, self.crumb)
        except (TypeError, AttributeError):
            raise InstanceTypeError(self, "member of non-object") from None
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None

    def sibling(self, name: QName) -> "Instance":
        try:
            obj = self.crumb.object.copy()
            newval = obj.pop(name)
            obj[self.crumb.name] = self.value
            return Instance(newval, MemberCrumb(name, obj, self.crumb.parent))
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None
        except IndexError:
            raise InstanceTypeError(self, "sibling of non-member") from None

    def entry(self, index: int) -> "Instance":
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "entry of non-array")
        try:
            return Instance(val[index],
                            EntryCrumb(val[:index], val[index+1:], self.crumb))
        except IndexError:
            raise NonexistentInstance(self, "entry " + str(index)) from None

    def remove_entry(self, index: int) -> "Instance":
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "entry of non-array")
        try:
            return Instance(val[:index] + val[index+1:], self.crumb)
        except IndexError:
            raise NonexistentInstance(self, "entry " + str(index)) from None

    def first_entry(self):
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "first entry of non-array")
        try:
            return Instance(val[0], EntryCrumb([], val[1:], self.crumb))
        except IndexError:
            raise NonexistentInstance(self, "first of empty") from None

    def last_entry(self):
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "last entry of non-array")
        try:
            return Instance(val[-1], EntryCrumb(val[:-1], [], self.crumb))
        except IndexError:
            raise NonexistentInstance(self, "last of empty") from None

    def look_up(self, keys: Dict[QName, ScalarValue]) -> "Instance":
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

    def next(self) -> "Instance":
        try:
            cr = self.crumb
            return Instance(
                cr.after[0],
                EntryCrumb(cr.before + [self.value], cr.after[1:], cr.parent))
        except IndexError:
            raise NonexistentInstance(self, "next of last") from None
        except AttributeError:
            raise InstanceTypeError(self, "next of non-entry") from None

    def previous(self) -> "Instance":
        try:
            cr = self.crumb
            return Instance(
                cr.before[-1],
                EntryCrumb(cr.before[:-1], [self.value] + cr.after, cr.parent))
        except IndexError:
            raise NonexistentInstance(self, "previous of first") from None
        except AttributeError:
            raise InstanceTypeError(self, "previous of non-entry") from None

    def insert_before(self, value: Value):
        try:
            cr = self.crumb
            return Instance(value,
                            EntryCrumb(cr.before, [self.value] + cr.after, cr,
                                       datetime.now()))
        except (AttributeError, IndexError):
            raise InstanceTypeError(self, "insert before non-entry") from None

    def insert_after(self, value: Value):
        try:
            cr = self.crumb
            return Instance(value,
                            EntryCrumb(cr.before + [self.value], cr.after, cr,
                                       datetime.now()))
        except (AttributeError, IndexError):
            raise InstanceTypeError(self, "insert after non-entry") from None

class InstanceIdentifier(list):
    """Instance identifiers."""

    def __str__(self):
        """Return a string representation of the receiver."""
        return "".join([ str(i) for i in self ])

class InstanceSelector:
    """Components of instance identifers."""
    pass

class MemberName(InstanceSelector):
    """Selectors of object members."""

    def __init__(self, name: QName) -> None:
        """Initialize the class instance.

        :param name: member name
        """
        self.name = name

    def __str__(self) -> str:
        """Return a string representation of the receiver."""
        return "/" + self.name

    def peek_step(self, obj: ObjectValue) -> Value:
        """Return the member of `obj` addressed by the receiver.

        :param obj: current object
        """
        return obj.get(self.name)

    def goto_step(self, inst: Instance) -> Instance:
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

    def peek_step(self, arr: ArrayValue) -> Value:
        """Return the entry of `arr` addressed by the receiver.

        :param arr: current array
        """
        try:
            return arr[self.index]
        except IndexError:
            return None

    def goto_step(self, inst: Instance) -> Instance:
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

    def peek_step(self, arr: ArrayValue) -> Value:
        """Return the entry of `arr` addressed by the receiver.

        :param arr: current array
        """
        try:
            return arr[arr.index(self.value)]
        except ValueError:
            return None

    def goto_step(self, inst: Instance) -> Instance:
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

    def __init__(self, keys: Dict[QName, ScalarValue]) -> None:
        """Initialize the class instance.

        :param keys: dictionary with keys of an entry
        """
        self.keys = keys

    def __str__(self) -> str:
        """Return a string representation of the receiver."""
        return "".join(["[{}={}]".format(k, repr(self.keys[k]))
                        for k in self.keys])

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

    def goto_step(self, inst: Instance) -> Instance:
        """Return member instance of `inst` addressed by the receiver.

        :param inst: current instance
        """
        return inst.look_up(self.keys)

# Exceptions

class InstanceError(YangsonException):
    """Exceptions related to operations on the instance structure."""

    def __init__(self, inst: Instance):
        self.instance = inst

    def __str__(self):
        return "[" + self.instance.crumb.pointer() + "] "

class NonexistentInstance(InstanceError):
    """Exception to raise when moving out of bounds."""

    def __init__(self, inst: Instance, text: str) -> None:
        super().__init__(inst)
        self.text = text

    def __str__(self):
        return "{} {}".format(super().__str__(), self.text)

class InstanceTypeError(InstanceError):
    """Exception to raise when calling a method for a wrong instance type."""

    def __init__(self, inst: Instance, text: str) -> None:
        super().__init__(inst)
        self.text = text

    def __str__(self):
        return "{} {}".format(super().__str__(), self.text)

class DuplicateMember(InstanceError):
    """Exception to raise on attempt to create a member that already exists."""

    def __init__(self, inst: Instance, name: QName) -> None:
        super().__init__(inst)
        self.name = name

    def __str__(self):
        return "{} member {}".format(super().__str__(), self.name)
