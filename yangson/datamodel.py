import json
from typing import Dict, List, Optional
from urllib.parse import unquote
from .constants import pname_re, YangsonException
from .context import Context, BadYangLibraryData
from .instance import (Crumb, EntryKeys, Instance, InstanceIdentifier,
                       MemberName)
from .schema import (BadSchemaNodeType, DataNode, InternalNode,
                     NonexistentSchemaNode, RawObject, SchemaNode)
from .statement import Statement
from .typealiases import *

class DataModel:
    """YANG data model."""

    def __init__(self, yltxt: str, mod_path: List[str]) -> None:
        """Initialize the class instance.

        :param yltxt: JSON text containing YANG library data
        :param mod_path: list of filesystem paths from which
                         YANG modules listed in YANG library
                         can be retrieved.
        """
        Context.schema = InternalNode() # type: InternalNode
        try:
            yl = json.loads(yltxt)
        except json.JSONDecodeError:
            raise BadYangLibraryData() from None
        Context.from_yang_library(yl, mod_path)

    def from_raw(self, robj: RawObject) -> Instance:
        """Return an instance created from a raw data tree.

        :param robj: a dictionary representing raw data tree
        """
        cooked = Context.schema.from_raw(robj)
        return Instance(cooked, Crumb(None, cooked.last_modified))

    def get_schema_node(self, path: SchemaPath) -> Optional[SchemaNode]:
        """Return the schema node corresponding to `path`.

        :param path: schema path
        :raises BadPath: if the schema path is invalid
        """
        return Context.schema.get_schema_descendant(Context.path2route(path))

    def get_data_node(self, path: SchemaPath) -> Optional[DataNode]:
        """Return the data node corresponding to `path`.

        :param path: data path
        :raises BadPath: if the data path is invalid
        """
        addr = Context.path2route(path)
        node = Context.schema
        for p in addr:
            node = node.get_data_child(*p)
            if node is None: return None
        return node

    def parse_instance_id(self, iid: str) -> InstanceIdentifier:
        """Parse instance identifier.

        :param iid: instance identifier string
        :raises BadInstanceIdentifier: if the instance identifier is invalid
        :raises NonexistentSchemaNode: if the instance identifier refers to
                                       a data node that doesn't exist
        """
        end = len(iid)
        offset = 0
        res = InstanceIdentifier()
        sn = Context.schema
        while True:
            if iid[offset] != "/":
                raise BadInstanceIdentifier(iid)
            mo = pname_re.match(iid, offset+1)
            if mo is None:
                raise BadInstanceIdentifier(iid)
            ns = mo.group("prf")
            name = mo.group("loc")
            cn = sn.get_data_child(name, ns)
            if cn is None:
                raise NonexistentSchemaNode(name, ns if ns else sn.ns)
            sn = cn
            res.append(MemberName(sn.instance_name()))
            offset = mo.end()
            if offset < end and iid[offset] != "/":
                sel, offset = sn._parse_entry_selector(iid, offset)
                res.append(sel)
            if offset >= end: return res

    def parse_resource_id(self, rid: str) -> InstanceIdentifier:
        """Parse RESTCONF data resource identifier.

        :param rid: data resource identifier
        :raises BadResourceIdentifier: if the resource identifier is invalid
        :raises NonexistentSchemaNode: if the resource identifier refers to
                                       a data node that doesn't exist
        :raises BadSchemaNodeType: if keys are specified for a schema node that
                                   is not a list
        """
        inp = rid[1:] if rid[0] == "/" else rid
        res = InstanceIdentifier()
        sn = Context.schema
        for p in inp.split("/"):
            apiid, eq, keys = p.partition("=")
            mo = pname_re.match(unquote(apiid))
            if mo is None:
                raise BadResourceIdentifier(rid)
            ns = mo.group("prf")
            name = mo.group("loc")
            cn = sn.get_data_child(name, ns)
            if cn is None:
                raise NonexistentSchemaNode(name, ns if ns else sn.ns)
            sn = cn
            res.append(MemberName(sn.instance_name()))
            if eq:                        # list instance
                ks = keys.split(",")
                try:
                    if len(ks) != len(sn.keys):
                        raise BadResourceIdentifier(rid)
                except AttributeError:
                    raise BadSchemaNodeType(sn, "list") from None
                sel = {}
                for i in range(len(ks)):
                    klf = sn.get_child(*sn.keys[i])
                    val = klf.type.parse_value(unquote(ks[i]))
                    sel[klf.instance_name()] = val
                res.append(EntryKeys(sel))
        return res

    def ascii_tree(self) -> str:
        """Return ascii-art representation of the main data tree."""
        return Context.schema._ascii_tree("")

class BadInstanceIdentifier(YangsonException):
    """Exception to be raised for malformed instance identifier."""

    def __init__(self, iid: str) -> None:
        self.iid = iid

    def __str__(self) -> str:
        return self.iid

class BadResourceIdentifier(YangsonException):
    """Exception to be raised for malformed resource identifier."""

    def __init__(self, rid: str) -> None:
        self.rid = rid

    def __str__(self) -> str:
        return self.rid
