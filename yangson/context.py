import re
from typing import Dict, List, MutableSet
from .constants import pname_re, YangsonException
from .modparser import from_file
from .statement import Statement
from .typealiases import *

"""This module provides class `Context`."""

class Context:
    """Global repository of data model structures and utility methods.

    The information is installed in class varables, which means that
    different schemas cannot be generated in parallel. No instances of
    this class are expected to be created.
    """

    @classmethod
    def initialize(cls) -> None:
        """Initialize the context variables."""
        cls.module_search_path = [] # type: MutableSet[str]
        cls.modules = {} # type: Dict[ModuleId, Statement]
        cls.implement = [] # type: List[YangIdentifier]
        cls.revisions = {} # type: Dict[YangIdentifier, List[str]]
        cls.prefix_map = {} # type: Dict[ModuleId, Dict[YangIdentifier, ModuleId]]
        cls.ns_map = {} # type: Dict[YangIdentifier, YangIdentifier]
        cls.derived_identities = {} # type Dict[QualName, MutableSet[QualName]]
        cls.features = set() # type: MutableSet[QualName]

    # Regular expressions
    not_re = re.compile(r"not\s+")
    and_re = re.compile(r"\s+and\s+")
    or_re = re.compile(r"\s+or\s+")

    @classmethod
    def from_yang_library(cls, yang_lib: Dict[str, Any],
                          mod_path: List[str]) -> None:
        """Initialize the data model structures from YANG library data.

        :param yang_lib: dictionary with YANG library data
        :param mod_path: list of filesystem paths from which the
                         YANG modules listed in `yang_lib` can be
                         retrieved.
        """
        cls.initialize()
        cls.module_search_path = mod_path
        cls.schema._nsswitch = cls.schema._config = True
        try:
            for item in yang_lib["ietf-yang-library:modules-state"]["module"]:
                name = item["name"]
                cls.ns_map[name] = name
                if "feature" in item:
                    cls.features.update(
                        [ (f,name) for f in item["feature"] ])
                rev = item["revision"] if item["revision"] else None
                mid = (name, rev)
                ct = item["conformance-type"]
                if ct == "implement": cls.implement.append(name)
                cls.revisions.setdefault(name, []).append(rev)
                mod = cls.load_module(name, rev)
                locpref = mod.find1("prefix", required=True).argument
                cls.prefix_map[mid] = { locpref: mid }
                if "submodules" in item and "submodule" in item["submodules"]:
                    for s in item["submodules"]["submodule"]:
                        sname = s["name"]
                        cls.ns_map[sname] = name
                        rev = s["revision"] if s["revision"] else None
                        smid = (sname, rev)
                        if ct == "implement": cls.implement.append(sname)
                        cls.revisions.setdefault(sname, []).append(rev)
                        submod = cls.load_module(sname, rev)
                        bt = submod.find1("belongs-to", name, required=True)
                        locpref = bt.find1("prefix", required=True).argument
                        cls.prefix_map[smid] = { locpref: mid }
        except (KeyError, AttributeError):
            raise BadYangLibraryData()
        for mod in cls.revisions:
            cls.revisions[mod].sort(key=lambda r: "0" if r is None else r)
        cls.process_imports()
        cls._check_feature_dependences()
        cls.identity_derivations()
        for mn in cls.implement:
            if len(cls.revisions[mn]) > 1:
                raise MultipleImplementedRevisions(mn)
            mid = (mn, cls.revisions[mn][0])
            cls.schema._handle_substatements(cls.modules[mid], mid)
        cls.apply_augments()

    @classmethod
    def load_module(cls, name: YangIdentifier,
                    rev: RevisionDate) -> Statement:
        """Read, parse and register YANG module or submodule."""
        for d in cls.module_search_path:
            fn = "{}/{}".format(d, name)
            if rev: fn += "@" + rev
            try:
                res = from_file(fn + ".yang")
            except FileNotFoundError:
                continue
            cls.modules[(name, rev)] = res
            return res
        raise ModuleNotFound(name, rev)

    @classmethod
    def _last_revision(cls, mname: YangIdentifier) -> ModuleId:
        return (mname, cls.revisions[mname][-1])

    @classmethod
    def process_imports(cls) -> None:
        for mid in cls.modules:
            mod = cls.modules[mid]
            try:
                pos = cls.implement.index(mid[0])
            except ValueError:                # mod not implemented
                pos = None
            for impst in mod.find_all("import"):
                impn = impst.argument
                prefix = impst.find1("prefix", required=True).argument
                revst = impst.find1("revision-date")
                rev = revst.argument if revst else None
                if rev in cls.revisions[impn]:
                    imid = (impn, rev)
                elif rev is None:             # use last revision
                    imid = cls._last_revision(impn)
                else:
                    raise ModuleNotFound(impn, rev)
                cls.prefix_map[mid][prefix] = imid
                if pos is None: continue
                i = pos
                while i < len(cls.implement):
                    if cls.implement[i] == impn:
                        cls.implement[pos] = impn
                        cls.implement[i] = mid[0]
                        pos = i
                        break
                    i += 1

    @classmethod
    def apply_augments(cls) -> None:
        """Apply top-level augments from all implemented modules."""
        for mn in cls.implement:
            mid = (mn, cls.revisions[mn][0])
            mod = cls.modules[mid]
            for aug in mod.find_all("augment"):
                cls.schema._augment_refine(aug, mid, True)

    @classmethod
    def identity_derivations(cls):
        """Create the graph of identity derivations."""
        for mid in cls.modules:
            for idst in cls.modules[mid].find_all("identity"):
                if not cls.if_features(idst, mid): continue
                idn = cls.translate_pname(idst.argument, mid)
                if idn not in cls.derived_identities:
                    cls.derived_identities[idn] = set()
                for bst in idst.find_all("base"):
                    bn = cls.translate_pname(bst.argument, mid)
                    cls.derived_identities.setdefault(bn, set()).add(idn)

    @classmethod
    def resolve_pname(cls, pname: PrefName,
                      mid: ModuleId) -> Tuple[YangIdentifier, ModuleId]:
        """Resolve prefixed name.

        :param pname: prefixed name
        :param mid: identifier of the context module
        """
        p, s, loc = pname.partition(":")
        try:
            return (loc, cls.prefix_map[mid][p]) if s else (p, mid)
        except KeyError:
            raise BadPrefName(pname) from None

    @classmethod
    def translate_pname(cls, pname: PrefName, mid: ModuleId) -> QualName:
        """Translate prefixed name to a qualified name.

        :param pname: prefixed name
        :param mid: identifier of the context module
        """
        loc, nid = cls.resolve_pname(pname, mid)
        return (loc, nid[0])

    @classmethod
    def sid2route(cls, sid: str, mid: ModuleId) -> SchemaRoute:
        """Construct schema route from a schema node identifier.

        :param sid: schema node identifier (absolute or relative)
        :param mid: identifier of the context module
        """
        nlist = sid.split("/")
        return [ cls.translate_pname(qn, mid)
                 for qn in (nlist[1:] if sid[0] == "/" else nlist) ]

    @classmethod
    def path2route(cls, path: SchemaPath) -> SchemaRoute:
        """Translate schema path to schema route.

        :param path: schema path
        """
        nlist = path.split("/")
        prevns = None
        res = []
        for n in (nlist[1:] if path[0] == "/" else nlist):
            p, s, loc = n.partition(":")
            if s:
                if p == prevns: raise BadPath(path)
                res.append((loc, p))
                prevns = p
            elif prevns:
                res.append((p, prevns))
            else:
                raise BadPath(path)
        return res

    @classmethod
    def get_definition(cls, stmt: Statement, mid: ModuleId) -> Statement:
        """Return the statement defining a grouping or derived type.

        :param stmt: "uses" or "type" statement
        :param mid: YANG module context
        """
        kw = "grouping" if stmt.keyword == "uses" else "typedef"
        loc, did = cls.resolve_pname(stmt.argument, mid)
        dstmt = (stmt.get_definition(loc, kw) if did == mid else
                 cls.modules[did].find1(kw, loc, required=True))
        return (dstmt, did)

    # Feature handling

    @classmethod
    def _check_feature_dependences(cls):
        """Verify feature dependences."""
        for mid in cls.modules:
            for fst in cls.modules[mid].find_all("feature"):
                fn = cls.translate_pname(fst.argument, mid)
                if fn not in cls.features: continue
                if not cls.if_features(fst, mid):
                    raise FeaturePrerequisiteError(*fn)

    @classmethod
    def if_features(cls, stmt: Statement, mid: ModuleId) -> bool:
        """Check ``if-feature`` substatements, if any.

        :param stmt: YANG statement
        :param mid: YANG module context
        """
        iffs = stmt.find_all("if-feature")
        if not iffs:
            return True
        for i in iffs:
            if cls.feature_expr(i.argument, mid):
                continue
            return False
        return True

    @classmethod
    def feature_test(cls, fname: PrefName, mid: ModuleId) -> bool:
        """Test feature support.

        :param fname: prefixed name of a feature
        :param mid: YANG module context
        """
        return cls.translate_pname(fname, mid) in cls.features

    @classmethod
    def feature_expr(cls, fexpr: str, mid: ModuleId) -> bool:
        """Evaluate feature expression.

        :param fexpr: feature expression
        :param mid: YANG module context
        """
        x, px = cls._feature_disj(fexpr, 0, mid)
        if px < len(fexpr):
            raise BadFeatureExpression(fexpr)
        return x

    @classmethod
    def _feature_atom(cls, fexpr: str, ptr: int,
                      mid: ModuleId) -> Tuple[bool, int]:
        if fexpr[ptr] == "(":
            x, px = cls._feature_disj(fexpr, ptr + 1, mid)
            if fexpr[px] == ")":
                return (x, px + 1)
        else:
            mo = pname_re.match(fexpr, ptr)
            if mo:
                return (cls.feature_test(mo.group(), mid), mo.end())
        raise BadFeatureExpression(fexpr)

    @classmethod
    def _feature_term(cls, fexpr: str, ptr: int,
                      mid: ModuleId) -> Tuple[bool, int]:
        mo = cls.not_re.match(fexpr, ptr)
        if mo:
            x, px = cls._feature_atom(fexpr, mo.end(), mid)
            return (not x, px)
        return cls._feature_atom(fexpr, ptr, mid)

    @classmethod
    def _feature_conj(cls, fexpr: str, ptr: int,
                      mid: ModuleId) -> Tuple[bool, int]:
        x, px = cls._feature_term(fexpr, ptr, mid)
        mo = cls.and_re.match(fexpr, px)
        if mo:
            y, py = cls._feature_conj(fexpr, mo.end(), mid)
            return (x and y, py)
        return (x, px)

    @classmethod
    def _feature_disj(cls, fexpr: str, ptr: int,
                      mid: ModuleId) -> Tuple[bool, int]:
        x, px = cls._feature_conj(fexpr, ptr, mid)
        mo = cls.or_re.match(fexpr, px)
        if mo:
            y, py = cls._feature_disj(fexpr, mo.end(), mid)
            return (x or y, py)
        return (x, px)

class ModuleNotFound(YangsonException):
    """A module is not found."""

    def __init__(self, name: YangIdentifier, rev: str = None) -> None:
        self.name = name
        self.rev = rev

    def __str__(self) -> str:
        if self.rev:
            return self.name + "@" + self.rev
        return self.name

class BadYangLibraryData(YangsonException):
    """Broken YANG Library data."""

    def __init__(self, reason: str = "broken yang-library data") -> None:
        self.reason = reason

    def __str__(self) -> str:
        return self.reason

class BadPath(YangsonException):
    """Invalid schema or data path."""

    def __init__(self, path: str) -> None:
        self.path = path

    def __str__(self) -> str:
        return self.path

class BadPrefName(YangsonException):
    """Broken prefixed name."""

    def __init__(self, pname: str) -> None:
        self.pname = pname

    def __str__(self) -> str:
        return self.pname

class BadFeatureExpression(YangsonException):
    """Broken "if-feature" argument."""

    def __init__(self, expr: str) -> None:
        self.expr = expr

    def __str__(self) -> str:
        return self.expr

class FeaturePrerequisiteError(YangsonException):
    """Missing feature dependences."""

    def __init__(self, fname: YangIdentifier, ns: YangIdentifier) -> None:
        self.fname = fname
        self.ns = ns

    def __str__(self) -> str:
        return "{}:{}".format(self.ns, self.fname)

class MultipleImplementedRevisions(YangsonException):
    """An implemented module has multiple revisions."""

    def __init__(self, module: YangIdentifier) -> None:
        self.module = module

    def __str__(self) -> str:
        return self.module
