"""Classes related to JSON-encoded instance data."""

from datetime import datetime
from typing import Any, Callable, List, Tuple
from .exception import YangsonException
from .typealiases import *

Value = Any
Object = Dict[QName, Value]
Array = List[Value]

class Crumb:
    """Class of crumb objects representing zipper context."""

    def __init__(self, parent: Optional["Crumb"] = None) -> None:
        """Initialize the class instance.

        :param parent: parent crumb
        """
        self.parent = parent

    def pointer(self):
        """Return JSON pointer of the receiver."""

        return ("{}/{}".format(self.parent.pointer(), self.pointer_fragment())
                if self.parent else "")

class MemberCrumb(Crumb):
    """Zipper contexts for an object member."""

    def __init__(self, name: QName, obj: Object, parent: Crumb) -> None:
        """Initialize the class instance.

        :param name: name of an object member that's the current focus
        :param obj: an object containing the remaining members
        :param parent: parent crumb
        """
        super().__init__(parent)
        self.name = name
        self.object = obj

    def pointer_fragment(self) -> QName:
        """Return the JSON pointer fragment of the focused value."""
        return self.name

    def zip(self, value: Value) -> Object:
        """Put focused value back to a copy of the object and return it.

        :param value: value of the focused member
        """
        res = self.object.copy()
        res[self.name] = value
        return res

class EntryCrumb(Crumb):
    """Zipper contexts for an array entry."""

    def __init__(self, before: Array, after: Array, parent: Crumb) -> None:
        """Initialize the class instance.

        :param before: array entries before the focused entry
        :param after: array entries after the focused entry
        :param parent: parent crumb
        """
        super().__init__(parent)
        self.before = before
        self.after = after

    def pointer_fragment(self) -> int:
        """Return the JSON pointer fragment of the focused value."""
        return len(self.before)

    def zip(self, value: Value) -> Array:
        """Concatenate the receiver's parts with the focused entry.

        :param value: value of the focused entry
        """
        return self.before + [value] + self.after

class Instance:
    """YANG data node instance implemented as a zipper structure."""

    def __init__(self, value: Value, crumb: Optional[Crumb] = None) -> None:
        """Initialize the class instance.

        :param value: instance value
        :param crumb: receiver's crumb
        """
        self.value = value
        self.crumb = crumb if crumb else Crumb()

    @property
    def namespace(self):
        """Return the receiver's namespace identifier."""
        for cr in reversed(self.trace):
            if isinstance(cr, MemberCrumb):
                p, s, loc = cr.name.partition(":")
                if s: return p

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
        return Instance(newval, self.crumb)

    @property
    def up(self) -> "Instance":
        """Ascend to the parent instance."""
        try:
            return Instance(self.crumb.zip(self.value), self.crumb.parent)
        except IndexError:
            raise NonexistentInstance(self, "up of top") from None

    @property
    def top(self) -> "Instance":
        inst = self
        while inst.crumb.parent:
            inst = inst.up
        return inst

    def member(self, name: QName) -> "Instance":
        obj = self.value.copy()
        try:
            return Instance(obj.pop(name), MemberCrumb(name, obj, self.crumb))
        except TypeError:
            raise InstanceTypeError(self, "member of non-object") from None
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None

    def new_member(self, name: QName, value: Value) -> "Instance":
        if name in self.value:
            raise DuplicateMember(self, name)
        return Instance(value, MemberCrumb(name, self.value, self.crumb))

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
        if not isinstance(val, list):
            raise InstanceTypeError(self, "entry of non-array") from None
        try:
            return Instance(val[index],
                            EntryCrumb(val[:index], val[index+1:], self.crumb))
        except IndexError:
            raise NonexistentInstance(self, "entry " + str(index)) from None

    @property
    def first_entry(self):
        val = self.value
        if not isinstance(val, list):
            raise InstanceTypeError(self, "first entry of non-array")
        try:
            return Instance(val[0], EntryCrumb([], val[1:], self.crumb))
        except IndexError:
            raise NonexistentInstance(self, "first of empty") from None

    @property
    def last_entry(self):
        val = self.value
        if not isinstance(val, list):
            raise InstanceTypeError(self, "last entry of non-array")
        try:
            return Instance(val[-1], EntryCrumb(val[:-1], [], self.crumb))
        except IndexError:
            raise NonexistentInstance(self, "last of empty") from None

    def look_up(self, keys: Dict[QName, Value]) -> "Instance":
        """Return the entry with matching keys."""
        if not isinstance(self.value, list):
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

    @property
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

    @property
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
                            EntryCrumb(cr.before, [self.value] + cr.after, cr))
        except (AttributeError, IndexError):
            raise InstanceTypeError(self, "insert before non-entry") from None

    def insert_after(self, value: Value):
        try:
            cr = self.crumb
            return Instance(value,
                            EntryCrumb(cr.before + [self.value], cr.after, cr))
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

    def peek_step(self, obj: Object) -> Value:
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

    def peek_step(self, arr: Array) -> Value:
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

    def __init__(self, value: Value) -> None:
        """Initialize the class instance.

        :param value: value of a leaf-list entry
        """
        self.value = value

    def __str__(self) -> str:
        """Return a string representation of the receiver."""
        return "[.=" + str(self.value) +"]"

    def peek_step(self, arr: Array) -> Value:
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

    def __init__(self, keys: Dict[QName, Value]) -> None:
        """Initialize the class instance.

        :param keys: dictionary with keys of an entry
        """
        self.keys = keys

    def __str__(self) -> str:
        """Return a string representation of the receiver."""
        return "".join(["[{}={}]".format(k, repr(self.keys[k]))
                        for k in self.keys])

    def peek_step(self, arr: Array) -> Value:
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

class StructuredValue:
    """Abstract class for array and object values."""

    def __init__(self, ts: Optional[datetime] = None) -> None:
        """Initialize class instance.

        :param ts: creation time stamp
        """
        self.last_modified = ts

    def time_stamp(self, ts: Optional[datetime] = None) -> None:
        """Update the receiver's last-modified time stamp.

        :param ts: new time stamp (if ``None``, set it to current time)
        """
        self.last_modified = ts if ts else datetime.now()

class ArrayValue(StructuredValue, list):
    """Array values corresponding to YANG lists and leaf-lists."""
    pass

class ObjectValue(StructuredValue, dict):
    """Array values corresponding to YANG container."""
    pass

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
