"""Basic access to the YANG data model."""

import hashlib
import json
from typing import Dict, List, Optional
from .exceptions import YangsonException
from .context import Context, BadYangLibraryData
from .instance import (EntryKeys, RootNode, MemberName,
                       InstanceIdParser, ResourceIdParser)
from .schema import DataNode, GroupNode, RawObject, SchemaNode
from .typealiases import *
from .typealiases import _Singleton

class DataModel(metaclass=_Singleton):
    """Basic entry point to the YANG data model.

    It is a singleton class, which means that only one instance can be
    created.
    """

    def __init__(self, yltxt: str, mod_path: List[str]) -> None:
        """Initialize the class instance.
        
        Args:
            yltxt: JSON text with YANG library data.
            mod_path: List of directories where to look for YANG modules.

        Raises:
            BadYangLibraryData: If YANG library data is invalid.
            FeaturePrerequisiteError: If a pre-requisite feature isn't
                supported.
            MultipleImplementedRevisions: If multiple revisions of an
                implemented module are listed in YANG library.
            ModuleNotFound: If a YANG module wasn't found in any of the
                directories specified in `mod_path`.
        """
        Context.schema = GroupNode()
        try:
            yl = json.loads(yltxt)
        except json.JSONDecodeError as e:
            raise BadYangLibraryData(str(e)) from None
        Context._from_yang_library(yl, mod_path)

    @classmethod
    def from_file(cls, name: str, mod_path: List[str] = ["."]) -> "DataModel":
        """Initialize the data model from a file with YANG library data.

        Args:
            name: Name of a file with YANG library data.
            mod_path: List of directories where to look for YANG modules.

        Returns:
            The data model instance.

        Raises:
            The same exceptions as the class constructor above.
        """
        with open(name, encoding="utf-8") as infile:
            yltxt = infile.read()
        return cls(yltxt, mod_path)

    @staticmethod
    def module_set_id() -> str:
        """Compute unique id of YANG modules comprising the data model.

        Returns:
            String consisting of hexadecimal digits.
        """
        fnames = sorted(["@".join(m) for m in Context.modules])
        return hashlib.sha1("".join(fnames).encode("ascii")).hexdigest()

    @staticmethod
    def from_raw(robj: RawObject) -> RootNode:
        """Create an instance node from a raw data tree.

        Args:
            robj: Dictionary representing a raw data tree.

        Returns:
            Root instance node.
        """
        cooked = Context.schema.from_raw(robj)
        return RootNode(cooked, Context.schema, cooked.timestamp)

    @staticmethod
    def get_schema_node(path: SchemaPath) -> Optional[SchemaNode]:
        """Return the schema node addressed by a schema path.

        Args:
            path: Schema path.

        Returns:
            Schema node if found in the schema, or ``None``.

        Raises:
            BadPath: If the schema path is invalid.
        """
        return Context.schema.get_schema_descendant(Context.path2route(path))

    @staticmethod
    def get_data_node(path: DataPath) -> Optional[DataNode]:
        """Return the data node addressed by a data path.

        Args:
            path: Data path.

        Returns:
            Data node if found in the schema, or ``None``.

        Raises:
            BadPath: If the schema path is invalid
        """
        addr = Context.path2route(path)
        node = Context.schema
        for p in addr:
            node = node.get_data_child(*p)
            if node is None: return None
        return node

    @staticmethod
    def ascii_tree() -> str:
        """Generate ASCII art representation of the schema tree.

        Returns:
            String with the ASCII tree.
        """
        return Context.schema._ascii_tree("")
