import hashlib
import json
from typing import Dict, List, Optional
from .constants import Singleton, YangsonException
from .context import Context, BadYangLibraryData
from .instance import (EntryKeys, RootNode, InstancePath,
                       MemberName, InstanceIdParser, ResourceIdParser)
from .schema import (BadSchemaNodeType, DataNode, GroupNode,
                     NonexistentSchemaNode, RawObject, SchemaNode)
from .typealiases import *

class DataModel(metaclass=Singleton):
    """Singleton class representing the entry point to the YANG data model."""

    def __init__(self, yltxt: str, mod_path: List[str]) -> None:
        """Initialize the class instance.

        :param yltxt: JSON text containing YANG library data
        :param mod_path: list of filesystem paths from which
                         YANG modules listed in YANG library
                         can be retrieved.
        """
        Context.schema = GroupNode()
        try:
            yl = json.loads(yltxt)
        except json.JSONDecodeError:
            raise BadYangLibraryData() from None
        Context.from_yang_library(yl, mod_path)

    @classmethod
    def from_file(cls, name: str, mod_path: List[str] = ["."]) -> "DataModel":
        """Return an instance initialised from a file with YANG library data.

        :param name: name of the file with YANG library data
        :param mod_path: list of directories where to search for YANG modules
        """
        with open(name, encoding="utf-8") as infile:
            yltxt = infile.read()
        return cls(yltxt, mod_path)

    @staticmethod
    def module_set_id() -> str:
        """Return hexadecimal id of the current set of modules."""
        fnames = sorted(["@".join(m) for m in Context.modules.keys()])
        return hashlib.sha1("".join(fnames).encode("ascii")).hexdigest()

    @staticmethod
    def from_raw(robj: RawObject) -> RootNode:
        """Return an instance created from a raw data tree.

        :param robj: a dictionary representing raw data tree
        """
        cooked = Context.schema.from_raw(robj)
        return RootNode(cooked, Context.schema, cooked.timestamp)

    @staticmethod
    def get_schema_node(path: SchemaPath) -> Optional[SchemaNode]:
        """Return the schema node corresponding to `path`.

        :param path: schema path
        :raises BadPath: if the schema path is invalid
        """
        return Context.schema.get_schema_descendant(Context.path2route(path))

    @staticmethod
    def get_data_node(path: SchemaPath) -> Optional[DataNode]:
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

    @staticmethod
    def ascii_tree() -> str:
        """Return ascii-art representation of the main data tree."""
        return Context.schema._ascii_tree("")
