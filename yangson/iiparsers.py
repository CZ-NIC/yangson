"""Parsers of strings identifying instances."""

from typing import Tuple, Union
from urllib.parse import unquote
from .constants import YangsonException
from .context import Context
from .instvalue import ArrayValue, ObjectValue, Value
from .instance import EntryKeys, EntryValue, InstancePath, MemberName
from .parser import Parser, ParserException, EndOfInput, UnexpectedInput
from .schema import (BadSchemaNodeType, DataNode, InternalNode, LeafListNode,
                     ListNode, NonexistentSchemaNode, SequenceNode,
                     TerminalNode)
from .typealiases import *

class InstancePathParser(Parser):
    """Abstract class for parsers of strings identifying instances."""

    def member_name(self, sn: InternalNode) -> Tuple[MemberName, DataNode]:
        """Parser object member name."""
        name, ns = self.instance_name()
        cn = sn.get_data_child(name, ns if ns else sn.ns)
        if cn is None:
            raise NonexistentSchemaNode(name, ns)
        return (MemberName(cn.instance_name()), cn)

class ResourceIdParser(InstancePathParser):
    """Parser for RESTCONF resource identifiers."""

    def parse(self, rid: ResourceIdentifier) -> InstancePath:
        """Parse resource identifier."""
        super().parse(rid)
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

    def key_values(self, sn: SequenceNode) -> Union[EntryKeys, EntryValue]:
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
            knod = sn.get_child(*sn.keys[j])
            val = knod.type.parse_value(unquote(ks[j]))
            sel[knod.instance_name()] = val
        return EntryKeys(sel)

class InstanceIdParser(InstancePathParser):
    """Parser for YANG instance identifiers."""

    def parse(self, iid: ResourceIdentifier) -> InstancePath:
        """Parse instance identifier."""
        super().parse(iid)
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
                if isinstance(sn, LeafListNode):
                    self.char(".")
                    res.append(EntryValue(self.get_value(cn)))
                    return res
                res.append(self.key_predicates(cn))
                if self.at_end(): return res
            sn = cn

    def get_value(self, tn: TerminalNode) -> ScalarValue:
        self.skip_ws()
        self.char("=")
        self.skip_ws()
        quote = self.one_of("'\"")
        val = self.up_to(quote)
        self.skip_ws()
        self.char("]")
        return tn.type.parse_value(val)

    def key_predicates(self, sn: ListNode) -> EntryKeys:
        "Parse one or more key predicates."""
        sel = {}
        while True:
            key = self.instance_name()
            knod = sn.get_child(*key)
            val = self.get_value(knod)
            sel[knod.instance_name()] = val
            try:
                next = self.peek()
            except EndOfInput:
                break
            if next != "[": break
            self.offset += 1
            self.skip_ws()
        return EntryKeys(sel)

    def key_values(self, sn: SequenceNode) -> EntryKeys:
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
            knod = sn.get_child(*sn.keys[j])
            val = knod.type.parse_value(unquote(ks[j]))
            sel[knod.instance_name()] = val
        return EntryKeys(sel)
