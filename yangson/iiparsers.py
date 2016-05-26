"""Parsers of strings identifying instances."""

from typing import Tuple
from urllib.parse import unquote
from .constants import YangsonException
from .context import Context
from .instvalue import ArrayValue, ObjectValue, Value
from .instance import EntryKeys, EntryValue, InstancePath, MemberName
from .parser import Parser, ParserException, EndOfInput, UnexpectedInput
from .schema import (BadSchemaNodeType, DataNode, InternalNode, LeafListNode,
                     NonexistentSchemaNode, SequenceNode)
from .typealiases import *

class InstancePathParser(Parser):
    """Abstract class for parsers of strings identifying instances."""

    def member_name(self, sn: InternalNode) -> Tuple[MemberName, DataNode]:
        """Parser object member name."""
        i1 = self.yang_identifier()
        if self.at_end() or self.peek() != ":":
            ns = sn.ns
            name = i1
        else:
            self.offset += 1
            ns = i1
            name = self.yang_identifier()
        cn = sn.get_data_child(name, ns)
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
                if self.at_end():
                    return res
            sn = cn

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
