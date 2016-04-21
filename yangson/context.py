import re
from typing import Dict, MutableSet
from .constants import pname_re, YangsonException
from .statement import Statement
from .typealiases import *

"""Context for schema generation."""

class Context:
    """This class provides context for schema generation.

    The information is installed in class varables, which means that
    different schemas cannot be generated in parallel.
    """

    modules = {} # type: Dict[ModuleId, Statement]
    """Dictionary of parsed modules comprising the data model."""

    prefix_map = {} # type: Dict[ModuleId, Dict[YangIdentifier, ModuleId]]
    """Per-module prefix assignments."""

    ns_map = {} # type: Dict[YangIdentifier, YangIdentifier]
    """Map of module and submodule names to namespaces."""

    derived_identities = {} # type Dict[QualName, MutableSet[QualName]]

    features = set() # type: MutableSet[QualName]

    # Regular expressions
    not_re = re.compile(r"not\s+")
    and_re = re.compile(r"\s+and\s+")
    or_re = re.compile(r"\s+or\s+")

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
                    der = cls.derived_identities.setdefault(bn, set())
                    der.add(idn)

    # Feature handling

    @classmethod
    def check_feature_dependences(cls):
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

class BadPath(YangsonException):
    """Exception to be raised for invalid schema or data path."""

    def __init__(self, path: str) -> None:
        self.path = path

    def __str__(self) -> str:
        return self.path

class BadPrefName(YangsonException):
    """Exception to be raised for a broken prefixed name."""

    def __init__(self, pname: str) -> None:
        self.pname = pname

    def __str__(self) -> str:
        return self.pname

class BadFeatureExpression(YangsonException):
    """Exception to be raised for a broken "if-feature" argument."""

    def __init__(self, expr: str) -> None:
        self.expr = expr

    def __str__(self) -> str:
        return self.expr

class FeaturePrerequisiteError(YangsonException):
    """Exception to be raised for missing feature dependences."""

    def __init__(self, fname, ns) -> None:
        self.fname = fname
        self.ns = ns

    def __str__(self) -> str:
        return "{}:{}".format(self.ns, self.fname)
