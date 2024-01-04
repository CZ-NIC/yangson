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

"""This module defines the entry point for a validation script."""

import argparse
import json
import os
import sys
import pkg_resources
from yangson import DataModel
from yangson.enumerations import ContentType, ValidationScope
from yangson.exceptions import (
    BadYangLibraryData, FeaturePrerequisiteError, InvalidFileFormat,
    MultipleImplementedRevisions,
    ModuleNotFound, ModuleNotRegistered, RawMemberError, RawTypeError,
    SchemaError, SemanticError, YangTypeError)


def main(ylib: str = None, path: str = None,
         scope: ValidationScope = ValidationScope.all,
         ctype: ContentType = ContentType.config, set_id: bool = False,
         tree: bool = False, no_types: bool = False,
         digest: bool = False, instance_input: str = None,
         instance_format: str = "auto", instance_output: str = None,
         instance_output_format: str = None, instance_output_ascii: bool = False
         ) -> int:
    """Entry-point for a validation script.

    Args:
        ylib: Name of the file with YANG library
        path: Colon-separated list of directories to search  for YANG modules.
        scope: Validation scope (syntax, semantics or all).
        ctype: Content type of the data instance (config, nonconfig or all)
        set_id: If `True`, print module set id.
        tree: If `True`, print schema tree.
        no_types: If `True`, don't print types in schema tree.
        digest: If `True`, print schema digest.
        instance_input: Name of file to load and validate against the schema.
        instance_format: Format of the file to validate.

    Returns:
        Numeric return code (0=no error, 2=YANG error, 1=other)
    """
    if ylib is None:
        parser = argparse.ArgumentParser(
            prog="yangson",
            description="Validate JSON data against a YANG data model.")
        parser.add_argument(
            "-V", "--version", action="version",
            version=f"%(prog)s {pkg_resources.get_distribution('yangson').version}")
        parser.add_argument(
            "ylib", metavar="YLIB",
            help=("name of the file with description of the data model"
                  " in JSON-encoded YANG library format [RFC 7895]"))
        parser.add_argument(
            "-p", "--path",
            help=("colon-separated list of directories to search"
                  " for YANG modules"))
        grp = parser.add_mutually_exclusive_group()
        grp.add_argument(
            "-i", "--id", action="store_true",
            help="print module set id")
        grp.add_argument(
            "-t", "--tree", action="store_true",
            help="print schema tree as ASCII art")
        grp.add_argument(
            "-d", "--digest", action="store_true",
            help="print schema digest in JSON format")
        parser.add_argument(
            "-n", "--no-types", action="store_true",
            help="suppress type info in tree output")
        grp = parser.add_argument_group(
            title="Validate and translate",
            description="Validate instance data and (if output format provided)"
                        "translate into another format")
        egrp = grp.add_mutually_exclusive_group()
        egrp.add_argument(
            "-I", "--input",
            help="name of the file with CBOR, JSON or XML encoded instance data; use - for stdin")
        egrp.add_argument(
            "-v", "--validate", metavar="INPUT",
            help="name of the file with CBOR, JSON or XML encoded instance data; use - for stdin")
        grp.add_argument(
            "-F", "--from", choices=["xml", "json", "cbor", "auto"],
            default="auto",
            help="input file format (default: %(default)s)")
        grp.add_argument(
            "-s", "--scope", choices=["syntax", "semantics", "all"],
            default="all", help="validation scope (default: %(default)s)")
        grp.add_argument(
            "-c", "--ctype", type=str, choices=["config", "nonconfig", "all"],
            default="config",
            help="content type of the data instance (default: %(default)s)")
        grp.add_argument(
            "-O", "--output",
            help="where to write the output; use - for stdout")
        grp.add_argument(
            "-T", "--translate", choices=["xml", "json", "cbor"],
            help="output file format")
        grp.add_argument(
            "-A", "--output-ascii", action="store_true",
            help="output file is ASCII only (valid only for XML and JSON)")

        args = parser.parse_args()
        ylib: str = args.ylib
        path: Optional[str] = args.path
        scope = ValidationScope[args.scope]
        ctype = ContentType[args.ctype]
        set_id: bool = args.id
        tree: bool = args.tree
        no_types = args.no_types
        digest: bool = args.digest
        instance_input: str = args.validate if args.validate is not None else vars(args)["input"]
        instance_input_format: str = vars(args)["from"]
        instance_output: str = args.output
        instance_output_format: str = args.translate
        instance_output_ascii: bool = args.output_ascii

    if (instance_output is None) != (instance_output_format is None):
        print("You have to specify both -O and -T to translate the instance")
        return 1

    if instance_output is not None and instance_input is None:
        print("Translation without input (use -I)")
        return 1

    if instance_output_format == "cbor" and instance_output_ascii:
        print("CBOR is binary format, can't make it ASCII")

    try:
        with open(ylib, encoding="utf-8") as infile:
            yl = infile.read()
    except (FileNotFoundError, PermissionError,
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
    if not instance_input:
        return 0

    try:
        with open(instance_input, "rb") as infile:
            i = {
                    "auto": dm.load,
                    "xml": dm.load_xml,
                    "json": dm.load_json,
                    "cbor": dm.load_cbor,
                    }[instance_input_format](infile)
    except (FileNotFoundError, PermissionError, InvalidFileFormat) as e:
        print("Instance data load failed:", str(e), file=sys.stderr)
        return 1
    except RawMemberError as e:
        print("Illegal object member:", str(e), file=sys.stderr)
        return 3
    except RawTypeError as e:
        print("Invalid type:", str(e), file=sys.stderr)
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

    if not instance_output:
        return 0

    try:
        store, store_kwargs, open_kwargs = {
                "xml": (i.store_xml,
                        { "encoding": "us-ascii" if instance_output_ascii else "unicode" },
                        { "mode": "wb" if instance_output_ascii else "w" } ),
                "json": (i.store_json,
                         {} if instance_output_ascii else { "ensure_ascii": False },
                         { "mode": "w", "encoding": "ascii" if instance_output_ascii else "utf8" } ),
                "cbor": (i.store_cbor, {}, { "mode": "wb"}),
                }[instance_output_format]

        with open(instance_output, **open_kwargs) as outfile:
            store(outfile, **store_kwargs)
    except (PermissionError) as e:
        print("Instance data store failed:", str(e), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
