from yangson import DataModel
from yangson.enumerations import ContentType, ValidationScope
from yangson.exceptions import BadYangLibraryData, FeaturePrerequisiteError, InvalidArgument, ModuleNotFound, ModuleNotRegistered, MultipleImplementedRevisions, NonexistentSchemaNode, RawMemberError, RawTypeError, SchemaError, SemanticError, YangTypeError
from yangson.typealiases import PrefName
from typing import Optional

def main(infile: Optional[str] = None,
         pickled: bool = False,
         path: Optional[str] = None,
         scope: ValidationScope = ...,
         ctype: ContentType = ...,
         set_id: bool = False,
         tree: bool = False,
         no_types: bool = False,
         digest: bool = False,
         subschema: Optional[PrefName] = None,
         validate: Optional[str] = None) -> int: ...
