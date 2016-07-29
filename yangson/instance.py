"""Classes related to instance data."""

from datetime import datetime
from typing import Any, Callable, List, Tuple
from urllib.parse import unquote
from .constants import YangsonException
from .context import Context
from .instvalue import ArrayValue, ObjectValue, Value
from .parser import EndOfInput, Parser
from .typealiases import *

class JSONPointer(tuple):
    """This class represents JSON Pointer [RFC 6901]."""

    def __str__(self) -> str:
        """Return string representation of the receiver."""
        return "/" + "/".join([ str(c) for c in self ])

class InstanceNode:
    """YANG data node instance implemented as a zipper structure."""

    def __init__(self, value: Value, parent: Optional["InstanceNode"],
                 schema_node: "DataNode", ts: datetime) -> None:
        """Initialize the class instance.

        :param value: instance value
        """
        self.value = value
        self.parent = parent
        self.schema_node = schema_node
        self.timestamp = ts

    def __str__(self):
        """Return string representation of the receiver's value."""
        sn = self.schema_node
        if not self.is_structured():
            return sn.type.canonical_string(self.value)
        return str(self.value)

    @property
    def qualName(self) -> Optional[QualName]:
        """Return the receiver's qualified name."""
        return None

    @property
    def namespace(self) -> Optional[YangIdentifier]:
        """Return the receiver's namespace."""
        return self.schema_node.ns

    def validate(self) -> None:
        """Validate the receiver."""
        sn = self.schema_node
        sn.validate(self)
        if isinstance(sn, TerminalNode):
            return
        elif isinstance(self.value, ArrayValue):
            e = self.entry(0)
            while True:
                e.validate()
                try:
                    e = e.next()
                except NonexistentInstance:
                    break
        else:
            for m in self.value:
                self.member(m).validate()

    def path(self) -> str:
        """Return JSONPointer of the receiver."""
        parents = []
        inst = self
        while inst.parent:
            parents.append(inst)
            inst = inst.parent
        return JSONPointer([ i._pointer_fragment() for i in parents[::-1] ])

    def update_from_raw(self, value: RawValue) -> "InstanceNode":
        """Update the receiver's value from a raw value."""
        newval = self.schema_node.from_raw(value)
        return self.update(newval)

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

    def _member_schema_node(self, name: InstanceName) -> "DataNode":
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
            if isinstance(sn, CaseNode):
                for ci in sn.competing_instances():
                    newval.pop(ci, None)
            sn = sn.parent
        ts = datetime.now()
        return self._copy(ObjectValue(newval, ts) , ts)

    def delete_member(self, name: InstanceName,
                      validate: bool = True) -> "InstanceNode":
        if name not in self.value:
            raise NonexistentInstance(self, "member " + name) from None
        csn = self._member_schema_node(name)
        if validate and csn.mandatory: raise MandatoryMember(self, name)
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
        """Return the node-set of all receiver's instances."""
        val = self.value
        if isinstance(val, ArrayValue):
            return [ self.entry(i) for i in range(len(val)) ]
        return [self]

    def delete_entry(self, index: int,
                     validate: bool = True) -> "InstanceNode":
        val = self.value
        if not isinstance(val, ArrayValue):
            raise InstanceTypeError(self, "entry of non-array")
        if index >= len(val):
            raise NonexistentInstance(self, "entry " + str(index)) from None
        if validate and self.schema_node.min_elements >= len(val):
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

    def children(self,
                 qname: Union[QualName, bool] = None) -> List["InstanceNode"]:
        """Return the node-set of receiver's XPath children."""
        sn = self.schema_node
        if isinstance(sn, TerminalNode): return []
        if qname:
            cn = sn.get_data_child(*qname)
            if cn is None: return []
            iname = cn.iname()
            if iname in self.value:
                return self.member(iname).xpath_nodes()
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
        for cn in sn.children.values():
            if isinstance(cn, ChoiceNode):
                cin = cn.child_inst_names().intersection(self.value)
                if cin:
                    for i in cin:
                        res.extend(self.member(i).xpath_nodes())
                else:
                    res.extend(cn._default_nodes(inst))
            else:
                iname = cn.iname()
                if iname in self.value:
                    res.extend(self.member(iname).xpath_nodes())
                else:
                    res.extend(cn._default_nodes(self))
        return res

    def descendants(self, qname: Union[QualName, bool] = None,
                    with_self: bool = False) -> List["InstanceNode"]:
        """Return the node-set of receiver's XPath descendants."""
        res = ([] if not with_self or (qname and self.qualName != qname)
               else [self])
        for c in self.children():
            if not qname or c.qualName == qname:
                res.append(c)
            res += c.descendants(qname)
        return res

    def preceding_siblings(
            self, qname: Union[QualName, bool] = None) -> List["InstanceNode"]:
        """Return the node-set of receiver's XPath preceding-siblings."""
        return []

    def following_siblings(
            self, qname: Union[QualName, bool] = None) -> List["InstanceNode"]:
        """Return the node-set of receiver's XPath following-siblings."""
        return []

    def deref(self) -> List["InstanceNode"]:
        """Return the list of nodes that the receiver refers to.

        The result is an empty list unless the receiver is a leaf
        with either "leafref" or "instance-identifier" type.
        """
        return ([] if self.is_structured() else
                self.schema_node.type._deref(self))

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

class RootNode(InstanceNode):
    """This class represents the root of the instance tree."""

    def __init__(self, value: Value, schema_node: "DataNode",
                 ts: datetime) -> None:
        super().__init__(value, None, schema_node, ts)
        self.name = None

    def _copy(self, newval: Value = None,
              newts: datetime = None) -> InstanceNode:
        return RootNode(newval if newval else self.value, self.schema_node,
                          newts if newts else self._timestamp)

    def is_structured(self):
        """Return ``True`` if the receiver has a structured value."""
        return True

    def ancestors_or_self(
            self, qname: Union[QualName, bool] = None) -> List["RootNode"]:
        """Return the list of receiver's XPath ancestors."""
        return [self] if qname is None else []

    def ancestors(
            self, qname: Union[QualName, bool] = None) -> List["RootNode"]:
        """Return the list of receiver's XPath ancestors."""
        return []

class ObjectMember(InstanceNode):
    """This class represents an object member."""

    def __init__(self, name: InstanceName, siblings: Dict[InstanceName, Value],
                 value: Value, parent: InstanceNode,
                 schema_node: "DataNode", ts: datetime ) -> None:
        super().__init__(value, parent, schema_node, ts)
        self.name = name
        self.siblings = siblings

    @property
    def qualName(self) -> Optional[QualName]:
        """Return the receiver's qualified name."""
        p, s, loc = self.name.partition(":")
        return (loc, p) if s else (p, self.namespace)

    def zip(self) -> ObjectValue:
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
                           self.parent, self.schema_node,
                           newts if newts else self._timestamp)

    def sibling(self, name: InstanceName) -> InstanceNode:
        ssn = self.parent._member_schema_node(name)
        try:
            sibs = self.siblings.copy()
            newval = sibs.pop(name)
            sibs[self.name] = self.value
            return ObjectMember(name, sibs, newval, self.parent,
                                ssn, self.timestamp)
        except KeyError:
            raise NonexistentInstance(self, "member " + name) from None

    def ancestors_or_self(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors-or-self."""
        res = [] if qname and self.qualName != qname else [self]
        return res + self.up().ancestors_or_self(qname)

    def ancestors(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors."""
        return self.up().ancestors_or_self(qname)

class ArrayEntry(InstanceNode):
    """This class represents an array entry."""

    def __init__(self, before: List[Value], after: List[Value],
                 value: Value, parent: InstanceNode,
                 schema_node: "DataNode", ts: datetime = None) -> None:
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
    def index(self) -> int:
        """Return the receiver's index."""
        return len(self.before)

    def update_from_raw(self, value: RawValue) -> "ArrayEntry":
        """Update the receiver's value from a raw value.

        This method overrides the superclass method.
        """
        return self.update(super(SequenceNode, self.schema_node).from_raw(value))

    def zip(self) -> ArrayValue:
        """Zip the receiver into an array and return it."""
        res = ArrayValue(self.before.copy(), self.timestamp)
        res.append(self.value)
        res += self.after
        return res

    def is_structured(self) -> bool:
        """Return ``True`` if the receiver has a structured value."""
        return not isinstance(self.schema_node, LeafListNode)

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

    def insert_before(self, value: Value,
                      validate: bool = True) -> "ArrayEntry":
        if validate and (self.schema_node.max_elements <=
            len(self.before) + len(self.after) + 1):
            raise MaxElements(self)
        return ArrayEntry(self.before, [self.value] + self.after, value,
                          self.parent, self.schema_node, datetime.now())

    def insert_after(self, value: Value, validate: bool = True) -> "ArrayEntry":
        if validate and (self.schema_node.max_elements <=
            len(self.before) + len(self.after) + 1):
            raise MaxElements(self)
        return ArrayEntry(self.before + [self.value], self.after, value,
                          self.parent, self.schema_node, datetime.now())

    def ancestors_or_self(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors-or-self."""
        res = [] if qname and self.qualName != qname else [self]
        return res + self.up().ancestors(qname)

    def ancestors(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """Return the list of receiver's XPath ancestors."""
        return self.up().ancestors(qname)

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

    def preceding_siblings(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """Return the list of receiver's XPath preceding-siblings."""
        return ([] if qname and self.qualName != qname
                else self.preceding_entries())

    def following_siblings(
            self, qname: Union[QualName, bool] = None) -> List[InstanceNode]:
        """Return the list of receiver's XPath following-siblings."""
        return ([] if qname and self.qualName != qname
                else self.following_entries())

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

class InstancePathParser(Parser):
    """Abstract class for parsers of strings identifying instances."""

    def member_name(self, sn: "InternalNode") -> Tuple[MemberName, "DataNode"]:
        """Parser object member name."""
        name, ns = self.instance_name()
        cn = sn.get_data_child(name, ns if ns else sn.ns)
        if cn is None:
            raise NonexistentSchemaNode(name, ns)
        return (MemberName(cn.iname()), cn)

class ResourceIdParser(InstancePathParser):
    """Parser for RESTCONF resource identifiers."""

    def parse(self) -> InstancePath:
        """Parse resource identifier."""
        if self.peek() == "/": self.offset += 1
        res = InstancePath()
        sn = Context.schema
        while True:
            mnam, cn = self.member_name(sn)
            res.append(mnam)
            try:
                next = self.one_of("/=")
            except EndOfInput:
                return res
            if next == "=":
                res.append(self.key_values(cn))
                if self.at_end(): return res
            sn = cn

    def key_values(self, sn: "SequenceNode") -> Union[EntryKeys, EntryValue]:
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
            knod = sn.children.get(sn.keys[j])
            val = knod.type.parse_value(unquote(ks[j]))
            sel[knod.iname()] = val
        return EntryKeys(sel)

class InstanceIdParser(InstancePathParser):
    """Parser for YANG instance identifiers."""

    def parse(self) -> InstancePath:
        """Parse instance identifier."""
        res = InstancePath()
        sn = Context.schema
        while True:
            self.char("/")
            mnam, cn = self.member_name(sn)
            res.append(mnam)
            try:
                next = self.peek()
            except EndOfInput:
                return res
            if next == "[":
                self.offset += 1
                self.skip_ws()
                if self.peek() in "0123456789":
                    ind = self.integer() - 1
                    if ind < 0:
                        raise UnexpectedInput(self, "positive index")
                    self.skip_ws()
                    self.char("]")
                    res.append(EntryIndex(ind))
                elif isinstance(cn, LeafListNode):
                    self.char(".")
                    res.append(EntryValue(self.get_value(cn)))
                else:
                    res.append(self.key_predicates(cn))
                if self.at_end(): return res
            sn = cn

    def get_value(self, tn: "TerminalNode") -> ScalarValue:
        self.skip_ws()
        self.char("=")
        self.skip_ws()
        quote = self.one_of("'\"")
        val = self.up_to(quote)
        self.skip_ws()
        self.char("]")
        return tn.type.parse_value(val)

    def key_predicates(self, sn: "ListNode") -> EntryKeys:
        "Parse one or more key predicates."""
        sel = {}
        while True:
            name, ns = self.instance_name()
            knod = sn.get_child(name, ns)
            val = self.get_value(knod)
            sel[knod.iname()] = val
            try:
                next = self.peek()
            except EndOfInput:
                break
            if next != "[": break
            self.offset += 1
            self.skip_ws()
        return EntryKeys(sel)

    def key_values(self, sn: "SequenceNode") -> EntryKeys:
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
            knod = sn.children.get(sn.keys[j])
            val = knod.type.parse_value(unquote(ks[j]))
            sel[knod.iname()] = val
        return EntryKeys(sel)

from .schema import (CaseNode, ChoiceNode, DataNode, InternalNode,
                     LeafNode, LeafListNode, ListNode,
                     NonexistentSchemaNode, SequenceNode, TerminalNode)
