# Copyright © 2016-2023 CZ.NIC, z. s. p. o.
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
import json
import os
import sys
from yangson import DataModel
from yangson.enumerations import ContentType
from yangson.exceptions import (
    NonexistentInstance, ValidationError, RawDataError)
from yangson.instance import ArrayEntry
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
    name: str
    revision: str
    location: set[str]

    def __init__(self: "ModuleData", rfc8525_entry: ArrayEntry):
        """Initialize the receiver."""
        val = rfc8525_entry.value
        self.name = val["name"]
        self.revision = val.get("revision", "")
        self.location = set([loc.strip() for loc in
                             val.get("location", [])])

    def key(self) -> tuple[str, str]:
        """Return the receiver's key (module name & revision)."""
        return (self.name, self.revision)

    def merge(self, other: "ModuleData") -> None:
        """Merge the receiver with another instance."""
        self.location |= other.location

    def as_raw(self) -> RawObject:
        """Return the receiver represented as an RFC 7895 entry."""
        res = {
            "name": self.name,
            "revision": self.revision
        }
        if self.location:
            res["schema"] = list(self.location)[0]
        return res


class MainModuleData(ModuleData):
    namespace: str
    import_only: bool
    deviation: set[str]
    feature: set[str]
    submodule: dict[tuple[str, str], ModuleData]

    def __init__(self: "MainModuleData", rfc8525_entry: ArrayEntry,
                 import_only: bool) -> None:
        """Initialize the receiver."""
        super().__init__(rfc8525_entry)
        val = rfc8525_entry.value
        self.import_only = import_only
        self.namespace = val["namespace"].strip()
        self.submodule = {}
        if "submodule" in val:
            for s in rfc8525_entry["submodule"]:
                self.add_submodule(s)
        self.feature = set(val.get("feature", []))
        self.deviation = set()
        if "deviation" in val:
            for dev in rfc8525_entry["deviation"]:
                dmod = dev._deref()[0]
                try:
                    rev = dmod.sibling("revision").value
                except NonexistentInstance:
                    rev = ""
                self.deviation.add((dmod.value, rev))

    def add_submodule(self, sub_entry: ArrayEntry):
        """Add or merge submodule defined in an RFC 8525 submodule entry."""
        smod = ModuleData(sub_entry)
        key = smod.key()
        if key in self.submodule:
            self.submodule[key].merge(smod)
        else:
            self.submodule[key] = smod

    def merge(self, other: "MainModuleData") -> None:
        """Extend the superclass method."""
        super().merge(other)
        self.deviation |= other.deviation
        self.feature |= other.feature
        self.import_only = self.import_only or other.import_only
        for sm in other.submodule:
            self.add_submodule(sm)

    def as_raw(self) -> RawObject:
        """Extend the superclass method."""
        res = super().as_raw()
        res["conformance-type"] = "import" if self.import_only else "implement"
        res["namespace"] = self.namespace
        if self.submodule:
            res["submodule"] = [self.submodule[s].as_raw()
                                for s in self.submodule]
        if self.feature:
            res["feature"] = list(self.feature)
        if self.deviation:
            res["deviation"] = [{ "name": n, "revision": r }
                                for (n,r) in self.deviation]
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
                "YANG library data conforming to the RFC 8525 schema"))
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
            schema = top["datastore"].look_up(
                name=(datastore, "ietf-datastores"))["schema"].value
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
                ment = MainModuleData(yam, import_only = False)
                modrev = ment.key()
                if modrev in modules:
                    modules[modrev].merge(ment)
                else:
                    modules[modrev] = ment
        if "import-only-module" in msentry:
            for yam in msentry["import-only-module"]:
                ment = MainModuleData(yam, import_only = True)
                modrev = ment.key()
                if modrev in modules:
                    modules[modrev].merge(ment)
                else:
                    modules[modrev] = ment
    dm7895 = DataModel(YL7895, sp.split(":"))
    res = dm7895.from_raw(
        { "ietf-yang-library:modules-state":
          { "module-set-id": top["content-id"].value }})
    rtop = res["ietf-yang-library:modules-state"]
    res = rtop.put_member("module",
                    [modules[m].as_raw() for m in modules], raw = True).up().up()
    res.validate(ctype=ContentType.nonconfig)
    try:
        outf = open(args.output, mode="w") if args.output else sys.stdout
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 3
    json.dump(res.raw_value(), outf, indent=2)
    outf.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
