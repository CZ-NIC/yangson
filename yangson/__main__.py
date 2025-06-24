# Copyright © 2016–2025 CZ.NIC, z. s. p. o.
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

"""This module defines the entry point for a validation script."""

import argparse
import json
import os
import pickle
import sys
import importlib.metadata
from yangson import DataModel
from yangson.enumerations import ContentType, ValidationScope
from yangson.exceptions import (
    BadYangLibraryData, FeaturePrerequisiteError, InvalidArgument,
    MultipleImplementedRevisions, ModuleNotFound, ModuleNotRegistered,
    NonexistentSchemaNode, RawMemberError, RawTypeError,
    SchemaError, SemanticError, YangTypeError)
from yangson.typealiases import PrefName


def main(infile: Optional[str] = None, pickled: bool = False, path: Optional[str] = None,
         scope: ValidationScope = ValidationScope.all,
         ctype: ContentType = ContentType.all, set_id: bool = False,
         tree: bool = False, no_types: bool = False,
         digest: bool = False, subschema: Optional[PrefName] = None,
         validate: Optional[str] = None) -> int:
    """Entry-point for the command-line utility.

    Args:
        infile: Name of the input file with YANG library or pickled data model
        pickled: Interpret the input file as a pickled data model object
        path: Colon-separated list of directories to search  for YANG modules
        scope: Validation scope (syntax, semantics or all)
        ctype: Content type of the data instance (config, nonconfig or all)
        set_id: If `True`, print module set id
        tree: If `True`, print schema tree
        no_types: If `True`, don't print types in schema tree
        digest: If `True`, print schema digest
        subschema: Prefixed name of an RPC or notification subschema
        validate: Name of file to validate against the schema.

    Returns:
        Numeric return code (0=no error, 2=YANG error, 1=other)
    """
    if infile is None:
        parser = argparse.ArgumentParser(
            prog="yangson",
            description="Validate JSON data against a YANG data model.")
        parser.add_argument(
            "-V", "--version", action="version",
            version=f"%(prog)s {importlib.metadata.version('yangson')}")
        parser.add_argument(
            "infile", metavar="INFILE",
            help=("file name with JSON-encoded YANG library [RFC 7895]"
                  " or pickled data model"))
        igrp = parser.add_mutually_exclusive_group()
        igrp.add_argument(
            "-p", "--path",
            help=("colon-separated list of directories to search"
                  " for YANG modules"))
        igrp.add_argument(
            "-P", "--pickled", action="store_true",
            help="interpret INFILE as pickled data model")
        ogrp = parser.add_mutually_exclusive_group()
        ogrp.add_argument(
            "-i", "--id", action="store_true",
            help="print module set id")
        ogrp.add_argument(
            "-t", "--tree", action="store_true",
            help="print schema tree as ASCII art")
        ogrp.add_argument(
            "-d", "--digest", action="store_true",
            help="print schema digest in JSON format")
        ogrp.add_argument(
            "-D", "--dump", metavar="FILE",
            help="dump the pickled data model to FILE")
        ogrp.add_argument(
            "-v", "--validate", metavar="INST",
            help="name of file with JSON-encoded instance data")
        parser.add_argument(
            "-s", "--scope", choices=["syntax", "semantics", "all"],
            default="all", help="validation scope (default: %(default)s)")
        parser.add_argument(
            "-c", "--ctype", choices=["config", "nonconfig", "all"],
            default="all",
            help="content type of the data instance (default: %(default)s)")
        parser.add_argument(
            "-S", "--subschema",
            help="prefixed name of an RPC or notification subschema")
        parser.add_argument(
            "-n", "--no-types", action="store_true",
            help="suppress type info in tree output")
        args = parser.parse_args()
        infile: str = args.infile
        path: Optional[str] = args.path
        pickled: bool = args.pickled
        scope = ValidationScope[args.scope]
        ctype = ContentType[args.ctype]
        set_id: bool = args.id
        tree: bool = args.tree
        dump: str = args.dump
        no_types = args.no_types
        digest: bool = args.digest
        subschema: PrefName = args.subschema
        validate: str = args.validate
    if pickled:
        try:
            with open(infile, "rb") as pif:
                dm = pickle.load(pif)
        except (FileNotFoundError, pickle.UnpicklingError) as e:
            print("Pickle file:", str(e), file=sys.stderr)
            return 1
    else:
        try:
            with open(infile, encoding="utf-8") as ylf:
                yl = ylf.read()
        except (FileNotFoundError, PermissionError, UnicodeDecodeError,
                json.decoder.JSONDecodeError) as e:
            print("YANG library:", str(e), file=sys.stderr)
            return 1
        sp = path if path else os.environ.get("YANG_MODPATH", ".")
        try:
            dm = DataModel(yl, tuple(sp.split(":")))
        except BadYangLibraryData as e:
            print("Invalid YANG library:", str(e), file=sys.stderr)
            return 2
        except FeaturePrerequisiteError as e:
            print("Unsupported pre-requisite feature:", str(e), file=sys.stderr)
            return 2
        except MultipleImplementedRevisions as e:
            print("Multiple implemented revisions:", str(e), file=sys.stderr)
            return 2
        except ModuleNotFound as e:
            print("Module not found:", str(e), file=sys.stderr)
            return 2
        except ModuleNotRegistered as e:
            print("Module not registered:", str(e), file=sys.stderr)
            return 2
    if set_id:
        print(dm.module_set_id())
        return 0
    if tree:
        print(dm.ascii_tree(no_types))
        return 0
    if digest:
        print(dm.schema_digest())
        return 0
    if dump:
        with open(dump, "wb") as pif:
            try:
                pickle.dump(dm, pif, pickle.HIGHEST_PROTOCOL)
                return 0
            except pickle.PicklingError as e:
                print("Pickling failed:", str(e), file=sys.stderr)
    if not validate:
        return 0
    try:
        with open(validate, encoding="utf-8") as instf:
            itxt = json.load(instf)
    except (FileNotFoundError, PermissionError, UnicodeDecodeError,
            json.decoder.JSONDecodeError) as e:
        print("Instance data:", str(e), file=sys.stderr)
        return 1
    try:
        i = dm.from_raw(itxt, subschema)
    except RawMemberError as e:
        print("Illegal object member:", str(e), file=sys.stderr)
        return 3
    except RawTypeError as e:
        print("Invalid type:", str(e), file=sys.stderr)
        return 3
    except InvalidArgument:
        print("Invalid subschema id:", subschema, "(missing prefix?)",
              file=sys.stderr)
        return 3
    except NonexistentSchemaNode:
        print("Subschema", subschema, "not found", file=sys.stderr)
        return 3
    try:
        i.validate(scope, ctype)
    except SchemaError as e:
        print("Schema error:", str(e), file=sys.stderr)
        return 3
    except SemanticError as e:
        print("Semantic error:", str(e), file=sys.stderr)
        return 3
    except YangTypeError as e:
        print("Invalid type:", str(e), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
