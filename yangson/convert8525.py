# Copyright © 2016-2025 CZ.NIC, z. s. p. o.
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

"""Conversion of YANG library formats.

This module defines an entry point for converting RFC-8525-style YANG
library data to the old RFC 7895 format that is used by Yangson.
"""

import argparse
from collections.abc import MutableMapping
import json
import os
import sys
from typing import cast, Optional
from yangson import DataModel
from yangson.enumerations import ContentType
from yangson.exceptions import (
    NonexistentInstance, ValidationError, RawDataError)
from yangson.instvalue import ObjectValue
from yangson.typealiases import RawObject

YL7895 = """
{
  "ietf-yang-library:modules-state": {
    "module-set-id": "",
    "module": [
      {
        "name": "ietf-yang-library",
        "revision": "2016-06-21",
        "namespace": "urn:ietf:params:xml:ns:yang:ietf-yang-library",
        "conformance-type": "implement"
      },
      {
        "name": "ietf-inet-types",
        "revision": "2013-07-15",
        "namespace": "urn:ietf:params:xml:ns:yang:ietf-inet-types",
        "conformance-type": "import"
      },
      {
        "name": "ietf-yang-types",
        "revision": "2013-07-15",
        "namespace": "urn:ietf:params:xml:ns:yang:ietf-yang-types",
        "conformance-type": "import"
      }
    ]
  }
}
"""

YL8525 = """
{
  "ietf-yang-library:modules-state": {
    "module-set-id": "",
    "module": [
      {
        "name": "ietf-yang-library",
        "revision": "2019-01-04",
        "namespace": "urn:ietf:params:xml:ns:yang:ietf-yang-library",
        "conformance-type": "implement"
      },
      {
        "name": "ietf-inet-types",
        "revision": "2013-07-15",
        "namespace": "urn:ietf:params:xml:ns:yang:ietf-inet-types",
        "conformance-type": "import"
      },
      {
        "name": "ietf-datastores",
        "revision": "2018-02-14",
        "namespace": "urn:ietf:params:xml:ns:yang:ietf-datastores",
        "conformance-type": "implement"
      },
      {
        "name": "ietf-yang-types",
        "revision": "2013-07-15",
        "namespace": "urn:ietf:params:xml:ns:yang:ietf-yang-types",
        "conformance-type": "import"
      }
    ]
  }
}
"""


class ModuleData:

    def __init__(self, val: ObjectValue):
        """Initialize the receiver."""
        self.name: str = val["name"]
        self.revision: str = val.get("revision", "")
        self.location: list[str] = [
            loc.strip() for loc in val.get("location", [])]

    def key(self) -> tuple[str, str]:
        """Return the receiver's key (module name & revision)."""
        return (self.name, self.revision)

    def as_raw(self) -> RawObject:
        """Return the receiver represented as an RFC 7895 entry."""
        res: MutableMapping = {
            "name": self.name,
            "revision": self.revision
        }
        if self.location:
            res["schema"] = list(self.location)[0]
        return res


class MainModuleData(ModuleData):

    def __init__(self, val: ObjectValue, import_only: bool):
        """Initialize the receiver."""
        super().__init__(val)
        self.import_only = import_only
        self.namespace: str = val["namespace"].strip()
        self.submodule: dict[tuple[str, str], ModuleData] = {}
        if "submodule" in val:
            for s in val["submodule"]:
                self.add_submodule(s)
        self.feature: list[str] = val.get("feature", [])
        self.deviation: list[tuple[str, str]] = []
        if "deviation" in val:
            for dev in val["deviation"]:
                dmod = dev._deref()[0]
                try:
                    rev = dmod.sibling("revision").value
                except NonexistentInstance:
                    rev = ""
                self.deviation.append((dmod.value, rev))

    def add_submodule(self, sub_entry: ObjectValue):
        """Add submodule defined in an RFC 8525 submodule entry."""
        smod = ModuleData(sub_entry)
        self.submodule[smod.key()] = smod

    def as_raw(self) -> RawObject:
        """Extend the superclass method."""
        res: MutableMapping = super().as_raw()
        res["conformance-type"] = "import" if self.import_only else "implement"
        res["namespace"] = self.namespace
        if self.submodule:
            res["submodule"] = [self.submodule[s].as_raw()
                                for s in self.submodule]
        if self.feature:
            res["feature"] = self.feature
        if self.deviation:
            res["deviation"] = [
                { "name": n, "revision": r } for (n,r) in self.deviation]
        return res


def main() -> int:
    """Entry-point for a conversion script.
    """
    parser = argparse.ArgumentParser(
        prog="convert8525",
        description=("Convert NMDA-compatible YANG library data to"
                     " the old style of RFC 7985."))
    parser.add_argument(
        "ylib", metavar="YLIB",
        help=("name of the input file containing JSON-encoded"
                " YANG library data conforming to the RFC 8525 schema"))
    parser.add_argument(
        "-o", "--output", metavar="OUTFILE",
        help="Direct output to OUTFILE instead of standard output")
    parser.add_argument(
        "-p", "--path",
        help=("colon-separated list of directories to search"
              " for YANG modules"))
    xgroup = parser.add_mutually_exclusive_group()
    xgroup.add_argument(
        "-d", "--datastore", metavar="DSTORE",
        default="running",
        help="name of a datastore")
    xgroup.add_argument(
        "-s", "--schema", metavar="SCHEMA",
        help="name of a schema")
    args = parser.parse_args()
    fn8525: str = args.ylib
    fn7895: Optional[str] = args.output
    path: Optional[str] = args.path
    datastore: str = args.datastore
    schema: Optional[str] = args.schema
    sp = path if path else os.environ.get("YANG_MODPATH", ".")
    dm8525 = DataModel(YL8525, sp.split(":"))
    try:
        with open(fn8525) as infile:
            ri = json.load(infile)
        inst = dm8525.from_raw(ri)
        inst.validate(ctype=ContentType.nonconfig)
    except (FileNotFoundError, PermissionError, json.decoder.JSONDecodeError,
            RawDataError, ValidationError) as e:
        print ("Invalid input data:", str(e), file=sys.stderr)
        return 1
    top = inst["ietf-yang-library:yang-library"]
    if schema is None:
        try:
            schema = cast(str, top["datastore"].look_up(
                name=(datastore, "ietf-datastores"))["schema"].value)
        except NonexistentInstance:
            print(f"No such datastore: 'ietf-datastores:{datastore}'",
                  file=sys.stderr)
            return 2
    try:
        msets = top["schema"].look_up(name=schema)["module-set"]
    except NonexistentInstance:
        print(f"No such schema: '{schema}'", file=sys.stderr)
        return 2
    modules: dict[tuple[str, str], MainModuleData] = {}
    for ms in msets:
        msentry = top["module-set"].look_up(name=ms.value)
        if "module" in msentry:
            for yam in msentry["module"]:
                ment = MainModuleData(yam.value, import_only = False)
                modules[ment.key()] = ment
        if "import-only-module" in msentry:
            for yam in msentry["import-only-module"]:
                ment = MainModuleData(yam.value, import_only = True)
                modules[ment.key()] = ment
    dm7895 = DataModel(YL7895, sp.split(":"))
    res = dm7895.from_raw(
        { "ietf-yang-library:modules-state":
          { "module-set-id": cast(str, top["content-id"].value) }})
    rtop = res["ietf-yang-library:modules-state"]
    res = rtop.put_member(
        "module", [modules[m].as_raw() for m in modules], raw = True).top()
    res.validate(ctype=ContentType.nonconfig)
    try:
        outf = open(args.output, mode="w") if args.output else sys.stdout
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 3
    json.dump(res.raw_value(), outf, indent=2)
    outf.write("\n")
    outf.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
