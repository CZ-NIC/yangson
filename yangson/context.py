from typing import Dict, List, MutableSet
from .constants import YangsonException
from .parser import Parser, ParserException
from .statement import ModuleParser, Statement
from .typealiases import *

"""This module provides class `Context`."""

class Context:
    """Global repository of data model structures and utility methods."""

    @classmethod
    def initialize(cls) -> None:
        """Initialize the context variables."""
        cls.module_search_path = [] # type: List[str]
        """List of directories where to look for YANG modules."""
        cls.modules = {} # type: Dict[ModuleId, Statement]
        """Dictionary of modules and submodules comprising the data model."""
        cls.implement = [] # type: List[YangIdentifier]
        """List of modules with conformance type “implement”."""
        cls.revisions = {} # type: Dict[YangIdentifier, List[str]]
        """Dictionary of module and submodule revisions."""
        cls.prefix_map = {} # type: Dict[ModuleId, Dict[YangIdentifier, ModuleId]]
        """Dictionary of prefix mappings."""
        cls.ns_map = {} # type: Dict[YangIdentifier, YangIdentifier]
        """Dictionary of module and submodule namespaces."""
        cls.identity_bases = {} # type: Dict[QualName, MutableSet[QualName]]
        """Dictionary of identity bases."""
        cls.features = set() # type: MutableSet[QualName]
        """Set of supported features."""

    @classmethod
    def from_yang_library(cls, yang_lib: Dict[str, Any],
                          mod_path: List[str]) -> None:
        """Set the data model structures from YANG library data.

        :param yang_lib: dictionary with YANG library data
        :param mod_path: value for `module_search_path`
        :raises BadYangLibraryData: invalid YANG library data
        :raises MultipleImplementedRevisions: multiple revisions of an
                                              implemented module
        :raises ModuleNotFound: a YANG module wasn't found
        :raises FeaturePrerequisiteError: a pre-requisite feature isn't
                                          supported.
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
                rev = item["revision"]
                mid = (name, rev)
                ct = item["conformance-type"]
                if ct == "implement": cls.implement.append(name)
                cls.revisions.setdefault(name, []).append(rev)
                mod = cls._load_module(name, rev)
                locpref = mod.find1("prefix", required=True).argument
                cls.prefix_map[mid] = { locpref: mid }
                if "submodules" in item and "submodule" in item["submodules"]:
                    for s in item["submodules"]["submodule"]:
                        sname = s["name"]
                        cls.ns_map[sname] = name
                        rev = s["revision"]
                        smid = (sname, rev)
                        if ct == "implement": cls.implement.append(sname)
                        cls.revisions.setdefault(sname, []).append(rev)
                        submod = cls._load_module(sname, rev)
                        bt = submod.find1("belongs-to", name, required=True)
                        locpref = bt.find1("prefix", required=True).argument
                        cls.prefix_map[smid] = { locpref: mid }
        except (KeyError, AttributeError) as e:
            raise BadYangLibraryData()
        for mod in cls.revisions:
            cls.revisions[mod].sort(key=lambda r: "0" if r is None else r)
        cls._process_imports()
        cls._check_feature_dependences()
        for mn in cls.implement:
            if len(cls.revisions[mn]) > 1:
                raise MultipleImplementedRevisions(mn)
            mid = (mn, cls.revisions[mn][0])
            cls.schema._handle_substatements(cls.modules[mid], mid)
        cls._apply_augments()
        cls.schema._post_process()
        cls.schema._make_schema_patterns()

    @classmethod
    def _load_module(cls, name: YangIdentifier,
                    rev: RevisionDate) -> Statement:
        """Read, parse and register YANG module or submodule."""
        for d in cls.module_search_path:
            fn = "{}/{}".format(d, name)
            if rev: fn += "@" + rev
            fn += ".yang"
            try:
                with open(fn, encoding='utf-8') as infile:
                    res = ModuleParser(infile.read()).parse()
            except FileNotFoundError:
                continue
            cls.modules[(name, rev)] = res
            return res
        raise ModuleNotFound(name, rev)

    @classmethod
    def last_revision(cls, mname: YangIdentifier) -> ModuleId:
        """Return last revision of a module that's part of the data model."""
        return (mname, cls.revisions[mname][-1])

    @classmethod
    def _process_imports(cls) -> None:
        deps = { mn: 0 for mn in cls.implement }
        impby = { mn: [] for mn in cls.implement }
        for mid in cls.modules:
            mod = cls.modules[mid]
            for impst in mod.find_all("import"):
                impn = impst.argument
                prefix = impst.find1("prefix", required=True).argument
                revst = impst.find1("revision-date")
                rev = revst.argument if revst else None
                if rev in cls.revisions[impn]:
                    imid = (impn, rev)
                elif rev is None:             # use last revision
                    imid = cls.last_revision(impn)
                else:
                    raise ModuleNotFound(impn, rev)
                cls.prefix_map[mid][prefix] = imid
                if mid[0] in deps and impn in deps:
                    deps[mid[0]] += 1
                    impby[impn].append(mid[0])
        cls.implement = []
        free = [mn for mn in deps if deps[mn] == 0]
        if not free: raise CyclicImports()
        while free:
            n = free.pop()
            cls.implement.append(n)
            for m in impby[n]:
                deps[m] -= 1
                if deps[m] == 0:
                    free.append(m)
        if [mn for mn in deps if deps[mn] > 0]: raise CyclicImports()

    @classmethod
    def _apply_augments(cls) -> None:
        """Apply top-level augments from all implemented modules."""
        for mn in cls.implement:
            mid = (mn, cls.revisions[mn][0])
            mod = cls.modules[mid]
            for aug in mod.find_all("augment"):
                cls.schema._augment_stmt(aug, mid, True)

    @classmethod
    def prefix2ns(cls, prefix: YangIdentifier, mid: ModuleId) -> YangIdentifier:
        """Return the namespace corresponding to the prefix."""
        return cls.prefix_map[mid][prefix][0]

    @classmethod
    def resolve_pname(cls, pname: PrefName,
                      mid: ModuleId) -> Tuple[YangIdentifier, ModuleId]:
        """Return the name and module identifier in which the name is defined.

        :param pname: prefixed name
        :param mid: identifier of the context module
        :raises BadPrefName: invalid prefix
        """
        p, s, loc = pname.partition(":")
        try:
            return (loc, cls.prefix_map[mid][p]) if s else (p, mid)
        except KeyError:
            raise BadPrefName(pname) from None

    @classmethod
    def translate_pname(cls, pname: PrefName, mid: ModuleId) -> QualName:
        """Translate a prefixed name to a qualified name.

        :param pname: prefixed name
        :param mid: identifier of the context module
        """
        loc, nid = cls.resolve_pname(pname, mid)
        return (loc, cls.ns_map[nid[0]])

    @classmethod
    def sid2route(cls, sid: str, mid: ModuleId) -> SchemaRoute:
        """Translate a schema node identifier to a schema route.

        :param sid: schema node identifier (absolute or relative)
        :param mid: identifier of the context module
        """
        nlist = sid.split("/")
        return [ cls.translate_pname(qn, mid)
                 for qn in (nlist[1:] if sid[0] == "/" else nlist) ]

    @classmethod
    def path2route(cls, path: SchemaPath) -> SchemaRoute:
        """Translate a schema path to a schema route.

        :param path: schema path
        :raises BadPath: invalid path
        """
        if path == "/" or path == "": return []
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
        :param mid: identifier of the context module
        """
        kw = "grouping" if stmt.keyword == "uses" else "typedef"
        loc, did = cls.resolve_pname(stmt.argument, mid)
        dstmt = (stmt.get_definition(loc, kw) if did == mid else
                 cls.modules[did].find1(kw, loc, required=True))
        return (dstmt, did)

    @classmethod
    def is_derived_from(cls, identity: QualName, base: QualName) -> bool:
        """Return ``True`` if `identity` is derived from `base`."""
        try:
            bases = cls.identity_bases[identity]
        except KeyError:
            return False
        if base in bases: return True
        for ib in bases:
            if cls.is_derived_from(ib, base): return True
        return False

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
        """Evaluate ``if-feature`` substatements, if any.

        :param stmt: YANG statement that is tested on if-features
        :param mid: identifier of the context module
        """
        iffs = stmt.find_all("if-feature")
        if not iffs:
            return True
        for i in iffs:
            if not FeatureExprParser(i.argument, mid).parse():
                return False
        return True

class FeatureExprParser(Parser):
    """Parser and evaluator for if-feature expressions."""

    def __init__(self, text: str, mid: ModuleId) -> None:
        """Initialize the parser instance.

        :param mid: id of the context module
        """
        super().__init__(text)
        self.mid = mid

    def parse(self) -> bool:
        """Parse and evaluate a complete **if-feature** expression."""
        self.skip_ws()
        res = self._feature_disj()
        self.skip_ws()
        if not self.at_end():
            raise InvalidFeatureExpression(self)
        return res

    def _feature_disj(self) -> bool:
        x = self._feature_conj()
        if self.test_string("or"):
            if not self.skip_ws():
                raise InvalidFeatureExpression(self)
            return self._feature_disj() or x
        return x

    def _feature_conj(self) -> bool:
        x = self._feature_term()
        if self.test_string("and"):
            if not self.skip_ws():
                raise InvalidFeatureExpression(self)
            return self._feature_conj() and x
        return x

    def _feature_term(self) -> bool:
        if self.test_string("not"):
            if not self.skip_ws():
                raise InvalidFeatureExpression(self)
            return not self._feature_atom()
        return self._feature_atom()

    def _feature_atom(self) -> bool:
        if self.peek() == "(":
            self.adv_skip_ws()
            res = self._feature_disj()
            self.char(")")
            self.skip_ws()
            return res
        n, p = self.qualified_name()
        self.skip_ws()
        ns = Context.prefix2ns(p, self.mid) if p else self.mid[0]
        return (n, ns) in Context.features

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

class InvalidFeatureExpression(ParserException):
    """Exception to be raised for an invalid **if-feature** expression."""

    def __str__(self) -> str:
        return str(self.parser)

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

class CyclicImports(YangsonException):
    """An implemented module has multiple revisions."""
    pass
