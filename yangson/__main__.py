# Copyright © 2016–2026 CZ.NIC, z. s. p. o.
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
# You should have received a copy of the GNU Lesser General Public License
# along with Yangson.  If not, see <http://www.gnu.org/licenses/>.

"""This module defines the entry point for a validation script."""

import argparse
import importlib.metadata
import json
import os
import pickle
import sys

from yangson import DataModel
from yangson.enumerations import ContentType, ValidationScope
from yangson.exceptions import (
    BadSchemaNodeType,
    BadYangLibraryData,
    FeaturePrerequisiteError,
    ModuleNotFound,
    ModuleNotRegistered,
    MultipleImplementedRevisions,
    NonexistentSchemaNode,
    RawMemberError,
    RawTypeError,
    SchemaError,
    SemanticError,
    YangTypeError,
)
from yangson.typealiases import SchemaPath


def main(model: str | None = None, pickled: bool = False,
         path: str | None = None, subschema: SchemaPath | None = None,
         command: str | None = None, no_types: bool = False,
         dumpfile: str | None = None, ctype: ContentType | None = None,
         scope: ValidationScope = ValidationScope.all,
         instance: str | None = None) -> int:
    """Entry-point for the command-line utility.

    Args:
        model: Name of the input file with YANG library or pickled data model
        pickled: Interpret the input file as a pickled data model object
        path: Colon-separated list of directories to search  for YANG modules
        subschema: Prefixed name of an RPC or notification subschema
        command: Operation (schema-id, digest, dump, tree, validate)
        no_types: If `True`, don't print types in schema tree
        dumpfile: The name of a file to which the pickled model is to be dumped
        scope: Validation scope (syntax, semantics or all)
        ctype: Content type of the data instance (config, nonconfig or all)
        instance: Name of instance file to validate against the schema.

    Returns:
        Numeric return code (0=no error, 1=JSON error, 2=YANG error)
    """
    if model is None:
        parser = argparse.ArgumentParser(
            prog="yangson",
            description="Inspect and validate YANG data models"
            " and JSON instances")
        parser.add_argument(
            "-V", "--version", action="version",
            help="show the Yangson library version number and exit",
            version=f"%(prog)s {importlib.metadata.version('yangson')}")
        parser.add_argument(
            "model", metavar="MODEL",
            help=("file name with JSON-encoded YANG library [RFC 7895]"
                  " or pickled data model"))
        igrp = parser.add_mutually_exclusive_group()
        igrp.add_argument(
            "-p", "--path",
            help=("colon-separated list of directories to search"
                  " for YANG modules"))
        igrp.add_argument(
            "-P", "--pickled", action="store_true",
            help="interpret MODEL as pickled data model")
        parser.add_argument(
            "-S", "--subschema",
            help="prefixed name of an RPC or notification subschema")
        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser(
            "schema-id", help="print unique module set id")
        subparsers.add_parser(
            "digest", help="print schema digest in JSON format")
        dump_parser = subparsers.add_parser(
            "dump", help="write pickled data model to FILE")
        dump_parser.add_argument("dumpfile", metavar="FILE")
        tree_parser = subparsers.add_parser(
            "tree", help="print the schema tree diagram")
        tree_parser.add_argument(
            "-n", "--no-types", action="store_true",
            help="suppress type info")
        validate_parser = subparsers.add_parser(
            "validate", help="validate instance data")
        validate_parser.add_argument(
            "instance", metavar="INSTANCE", help="JSON instance file")
        validate_parser.add_argument(
            "-s", "--scope", choices=["syntax", "semantics", "all"],
            help="validation scope (default: %(default)s")
        validate_parser.add_argument(
            "-c", "--ctype", choices=["config", "state", "nonconfig", "all"],
            help="content type of the data instance")
        args = parser.parse_args()
        model = args.model
        path = args.path if args.path else path
        pickled = args.pickled if args.pickled else pickled
        subschema = args.subschema if args.subschema else subschema
        if subschema and subschema[0] != "/":
            subschema = "/" + subschema
        command = args.command if args.command else command
        match command:
            case "dump":
                dumpfile = args.dumpfile
            case "tree":
                no_types = args.no_types if args.no_types else no_types
            case "validate":
                instance = args.instance if args.instance else instance
                scope = ValidationScope[args.scope] if args.scope else scope
                ctype = ContentType[args.ctype] if args.ctype else None
    if pickled:
        try:
            with open(model, "rb") as pif:
                dm = pickle.load(pif)
        except (FileNotFoundError, pickle.UnpicklingError) as e:
            print("Pickle file:", str(e), file=sys.stderr)
            return 1
    else:
        try:
            with open(model, encoding="utf-8") as ylf:
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
            print("Unsupported pre-requisite feature:", str(e),
                  file=sys.stderr)
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
    if command is None:
        return 0
    if command == "schema-id":
        print(dm.module_set_id())
        return 0
    if command == "tree":
        print(dm.ascii_tree(no_types))
        return 0
    if command == "digest":
        print(dm.schema_digest())
        return 0
    if command == "dump":
        if dumpfile is None:
            dumpfile = dm.module_set_id() +".pickle"
        with open(dumpfile, "wb") as pif:
            try:
                pickle.dump(dm, pif, pickle.HIGHEST_PROTOCOL)
                return 0
            except pickle.PicklingError as e:
                print("Pickling failed:", str(e), file=sys.stderr)
    # command: validate
    if not instance:
        print("Instance data: no file specified", file=sys.stderr)
        return 1
    try:
        with open(instance, encoding="utf-8") as instf:
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
    except BadSchemaNodeType:
        print("Not an RPC/action or notification: ", subschema,
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
