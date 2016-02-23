"""Classes related to JSON-encoded instance data."""

from typing import Any, List, Tuple
from .exception import YangsonException
from .typealiases import *

Trace = List["Crumb"]
Value = Any
Object = Dict[QName, Value]
Array = List[Value]

class Crumb(object):
    """Abstract class of crumb object representing a zipper context."""
    pass

class MemberCrumb(Crumb):
    """Zipper context for an object member."""

    def __init__(self, name: QName, obj: Object) -> None:
        """Initialize the class instance.

        :param name: name of an object member that's the current focus
        :param obj: an object containing the remaining members
        """
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
    """Zipper context for an array entry."""

    def __init__(self, before: Array, after: Array) -> None:
        """Initialize the class instance.

        :param before: array entries before the focused entry
        :param after: array entries after the focused entry
        """
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

class Instance(object):
    """YANG data node instance implemented as a zipper structure."""

    def __init__(self, value: Value, trace: Trace = []) -> None:
        """Initialize the class instance.

        :param value: instance value
        :param trace: sequence of crumbs
        """
        self.value = value
        self.trace = trace

    def crumb(self) -> Crumb:
        """Return the most recent crumb in receiver's trace."""
        return self.trace[-1]

    def prev_trace(self) -> Trace:
        """Return the receiver's trace without the last item."""
        return self.trace[:-1]

    def pointer(self) -> str:
        """Return JSON pointer of the receiver."""
        return "/" + "/".join([ c.pointer_fragment() for c in self.trace ])

    def update(self, newval: Value) -> "Instance":
        """Return a copy of the receiver with a new value.

        :param newval: new value
        """
        return self.__class__(newval, self.trace)

    @property
    def up(self) -> "Instance":
        """Ascend to the parent instance."""
        try:
            return self.__class__(self.crumb().zip(self.value),
                                  self.prev_trace())
        except IndexError:
            raise NonexistentInstance(self, "up of top") from None

    @property
    def top(self) -> "Instance":
        inst = self
        while inst.trace:
            inst = inst.up
        return inst

    def member(self, name: QName) -> "Instance":
        obj = self.value.copy()
        try:
            return self.__class__(obj.pop(name),
                                  self.trace + [MemberCrumb(name, obj)])
        except TypeError:
            raise InstanceTypeError(self, "member of non-object") from None
        except KeyError:
            raise NonexistentInstance(self, "member " + name)

    def entry(self, index: int) -> "Instance":
        try:
            return self.__class__(
                self.value[index], self.trace +
                [EntryCrumb(self.value[:index], self.value[index+1:])])
        except (KeyError, TypeError):
            raise InstanceTypeError(self, "entry of non-array") from None
        except IndexError:
            raise NonexistentInstance(self, "entry " + str(index)) from None

    @property
    def next(self) -> "Instance":
        try:
            return Instance(self.crumb.after[0], self.prev_trace() +
                            [EntryCrumb(self.crumb.before + [self.value],
                                        self.crumb.after[1:])])
        except IndexError: 
            raise NonexistentInstance(self, "next of last") from None

class InstanceError(YangsonException):
    """Exceptions related to operations on the instance structure."""

    def __init__(self, inst: Instance):
        self.instance = inst

    def __str__(self):
        return "[" + self.instance.pointer() + "] "

class NonexistentInstance(InstanceError):
    """Exception to raise when moving out of bounds."""

    def __init__(self, inst: Instance, text: str) -> None:
        super().__init__(inst)
        self.text = text

    def __str__(self):
        return "{} {}".format(super().__str__(), text)

class InstanceTypeError(InstanceError):
    """Exception to raise when calling a method for a wrong instance type."""

    def __init__(self, inst: Instance, text: str) -> None:
        super().__init__(inst)
        self.text = text

    def __str__(self):
        return "{} {}".format(super().__str__(), text)
