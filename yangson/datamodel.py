# Copyright © 2016–2023 CZ.NIC, z. s. p. o.
#
# This file is part of Yangson.
#
# Yangson is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Yangson is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with Yangson.  If not, see <http://www.gnu.org/licenses/>.

"""Basic access to the Yangson library.

This module implements the following class:

* DataModel: Basic entry point to the YANG data model.
"""
import hashlib
import json
from typing import Optional
import xml.etree.ElementTree as ET
from .enumerations import ContentType
from .exceptions import BadYangLibraryData
from .instance import (InstanceRoute, InstanceIdParser, ResourceIdParser,
                       RootNode)
from .schemadata import SchemaData, SchemaContext
from .schemanode import DataNode, SchemaTreeNode, RawObject, SchemaNode
from .typealiases import DataPath, SchemaPath


class DataModel:
    """Basic user-level entry point to Yangson library."""

    @classmethod
    def from_file(cls, name: str, mod_path: tuple[str] = (".",),
                  description: str = None) -> "DataModel":
        """Initialize the data model from a file with YANG library data.

        Args:
            name: Name of a file with YANG library data.
            mod_path: Tuple of directories where to look for YANG modules.
            description:  Optional description of the data model.

        Returns:
            The data model instance.

        Raises:
            The same exceptions as the class constructor above.
        """
        with open(name, encoding="utf-8") as infile:
            yltxt = infile.read()
        return cls(yltxt, mod_path, description)

    def __init__(self: "DataModel", yltxt: str, mod_path: tuple[str] = (".",),
                 description: str = None):
        """Initialize the class instance.

        Args:
            yltxt: JSON text with YANG library data.
            mod_path: Tuple of directories where to look for YANG modules.
            description: Optional description of the data model.

        Raises:
            BadYangLibraryData: If YANG library data is invalid.
            FeaturePrerequisiteError: If a pre-requisite feature isn't
                supported.
            MultipleImplementedRevisions: If multiple revisions of an
                implemented module are listed in YANG library.
            ModuleNotFound: If a YANG module wasn't found in any of the
                directories specified in `mod_path`.
        """
        try:
            self.yang_library = json.loads(yltxt)
        except json.JSONDecodeError as e:
            raise BadYangLibraryData(str(e)) from None
        self.schema_data = SchemaData(self.yang_library, mod_path)
        self.schema = SchemaTreeNode(self.schema_data)
        self.schema._ctype = ContentType.all
        self._build_schema()
        self.schema.description = description if description else (
            "Data model ID: " +
            self.yang_library["ietf-yang-library:modules-state"]
            ["module-set-id"])

    def module_set_id(self: "DataModel") -> str:
        """Compute unique id of YANG modules comprising the data model.

        Returns:
            String consisting of hexadecimal digits.
        """
        fnames = sorted(["@".join(m) for m in self.schema_data.modules])
        return hashlib.sha1("".join(fnames).encode("ascii")).hexdigest()

    def from_raw(self: "DataModel", robj: RawObject) -> RootNode:
        """Create an instance node from a raw data tree.

        Args:
            robj: Dictionary representing a raw data tree.

        Returns:
            Root instance node.
        """
        cooked = self.schema.from_raw(robj)
        return RootNode(cooked, self.schema, self.schema_data, cooked.timestamp)

    def from_xml(self: "DataModel", root: ET.Element) -> RootNode:
        """Create an instance node from a raw data tree.

        Args:
            robj: Dictionary representing a raw data tree.

        Returns:
            Root instance node.
        """
        cooked = self.schema.from_xml(root)
        return RootNode(cooked, self.schema, self.schema_data, cooked.timestamp)

    def get_schema_node(self: "DataModel", path: SchemaPath) -> Optional[SchemaNode]:
        """Return the schema node addressed by a schema path.

        Args:
            path: Schema path.

        Returns:
            Schema node if found in the schema, or ``None``.

        Raises:
            InvalidSchemaPath: If the schema path is invalid.
        """
        return self.schema.get_schema_descendant(
            self.schema_data.path2route(path))

    def get_data_node(self: "DataModel", path: DataPath) -> Optional[DataNode]:
        """Return the data node addressed by a data path.

        Args:
            path: Data path.

        Returns:
            Data node if found in the schema, or ``None``.

        Raises:
            InvalidSchemaPath: If the schema path is invalid.
        """
        addr = self.schema_data.path2route(path)
        node = self.schema
        for p in addr:
            node = node.get_data_child(*p)
            if node is None:
                return None
        return node

    def ascii_tree(self: "DataModel", no_types: bool = False, val_count: bool = False) -> str:
        """Generate ASCII art representation of the schema tree.

        Args:
            no_types: Suppress output of data type info.
            val_count: Show accumulated validation counts.

        Returns:
            String with the ASCII tree.
        """
        return self.schema._ascii_tree("", no_types, val_count)

    def clear_val_counters(self: "DataModel"):
        """Clear validation counters in the entire schema tree."""
        self.schema.clear_val_counters()

    def parse_instance_id(self: "DataModel", text: str) -> InstanceRoute:
        return InstanceIdParser(text).parse()

    def parse_resource_id(self: "DataModel", text: str) -> InstanceRoute:
        return ResourceIdParser(text, self.schema).parse()

    def schema_digest(self: "DataModel") -> str:
        """Generate schema digest (to be used primarily by clients).

        Returns:
            Condensed information about the schema in JSON format.
        """
        res = self.schema._node_digest()
        res["config"] = True
        return json.dumps(res)

    def _build_schema(self: "DataModel") -> None:
        for mid in self.schema_data._module_sequence:
            sctx = SchemaContext(
                self.schema_data, self.schema_data.namespace(mid), mid)
            self.schema._handle_substatements(
                self.schema_data.modules[mid].statement, sctx)
        for mid in self.schema_data._module_sequence:
            sctx = SchemaContext(
                self.schema_data, self.schema_data.namespace(mid), mid)
            mod = self.schema_data.modules[mid].statement
            for aug in mod.find_all("augment"):
                self.schema._augment_stmt(aug, sctx)
        for mid in self.schema_data._module_sequence:
            sctx = SchemaContext(
                self.schema_data, self.schema_data.namespace(mid), mid)
            mod = self.schema_data.modules[mid].statement
            for dev in mod.find_all("deviation"):
                self.schema._deviation_stmt(dev, sctx)
        self.schema._post_process()
