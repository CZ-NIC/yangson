"""
This script reads all *.yang files in a directory that is passed as the parameter.
Each file should contain a YANG module or submodule. The script then prints YANG
library data (JSON text) for all the modules and submodules.

If a submodule is included from a main module (with revision), then the submodule
must be present in the same directory. Otherwise an error message is printed and 
exit code is 1.
"""

import json
import os
import sys

from yangson.statement import ModuleParser

ydir = sys.argv[1]
"""Name of the directory with YANG (sub)modules."""
data_kws = ["augment", "container", "leaf", "leaf-list", "list", "rpc", "notification", "identity"]
"""Keywords of statements that contribute nodes to the schema tree."""
modmap = {}
"""Dictionary for collecting module data."""
submodmap = {}
"""Dictionary for collecting submodule data."""


def module_entry(yfile):
    """Add entry for one file containing YANG module text.

    Args:
        yfile (file): File containing a YANG module or submodule.
    """
    ytxt = yfile.read()
    mp = ModuleParser(ytxt)
    mst = mp.statement()
    submod = mst.keyword == "submodule"
    import_only = True
    rev = ""
    features = []
    includes = []
    rec = {}
    for sst in mst.substatements:
        if not rev and sst.keyword == "revision":
            rev = sst.argument
        elif import_only and sst.keyword in data_kws:
            import_only = False
        elif sst.keyword == "feature":
            features.append(sst.argument)
        elif submod:
            continue
        elif sst.keyword == "namespace":
            rec["namespace"] = sst.argument
        elif sst.keyword == "include":
            rd = sst.find1("revision-date")
            includes.append((sst.argument, rd.argument if rd else None))
    rec["import-only"] = import_only
    rec["features"] = features
    if submod:
        rec["revision"] = rev
        submodmap[mst.argument] = rec
    else:
        rec["includes"] = includes
        modmap[(mst.argument, rev)] = rec


def main():
    for infile in os.listdir(ydir):
        if not infile.endswith(".yang"):
            continue
        with open(f"{ydir}/{infile}", "r", encoding="utf-8") as yf:
            module_entry(yf)
    marr = []
    for (yam, mrev) in modmap:
        men = {"name": yam, "revision": mrev}
        sarr = []
        mrec = modmap[(yam, mrev)]
        men["namespace"] = mrec["namespace"]
        fts = mrec["features"]
        imp_only = mrec["import-only"]
        for (subm, srev) in mrec["includes"]:
            sen = {"name": subm}
            try:
                srec = submodmap[subm]
            except KeyError:
                print(f"Submodule {subm} not available.", file=sys.stderr)
                return 1
            if srev is None or srev == srec["revision"]:
                sen["revision"] = srec["revision"]
            else:
                print(f"Submodule {subm} revision mismatch.", file=sys.stderr)
                return 1
            imp_only = imp_only or srec["import-only"]
            fts += srec["features"]
            sarr.append(sen)
        if fts:
            men["feature"] = fts
        if sarr:
            men["submodule"] = sarr
        men["conformance-type"] = "import" if imp_only else "implement"
        marr.append(men)
    res = {
        "ietf-yang-library:modules-state": {
            "module-set-id": "",
            "module": marr
        }
    }
    print(json.dumps(res, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
