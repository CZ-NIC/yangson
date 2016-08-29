"""
Essential data model structures and methods.

This module implements the following classes:

* ModuleData: Data related to a YANG module or submodule.
* Context: Repository of data model structures and methods.
* FeatureExprParser: Parser for if-feature expressions.

The module defines the following exceptions:

* ModuleNotFound: YANG module not found.
* ModuleNotRegistered: Module is not registered in YANG library.
* BadYangLibraryData: Invalid YANG library data.
* BadPath: Invalid schema path
* UnknownPrefix: Unknown namespace prefix.
* InvalidFeatureExpression: Invalid if-feature expression.
* FeaturePrerequisiteError: A supported feature depends on
  another that isn't supported.
* MultipleImplementedRevisions: YANG library specifies multiple
  revisions of an implemented module.
* CyclicImports: Imports of YANG modules form a cycle.
"""

from typing import Dict, List, MutableSet, Optional, Tuple
from .exceptions import YangsonException
from .parser import Parser, ParserException
from .statement import DefinitionNotFound, ModuleParser, Statement
from .typealiases import *

class ModuleData:
    """Data related to a YANG module or submodule."""

    def __init__(self, main_module: YangIdentifier):
        """Initialize the class instance."""
        self.main_module = main_module # type: ModuleId
        """Main module of the receiver."""
        self.statement = None # type: Statement
        """Corresponding (sub)module statements."""
        self.prefix_map = {} # type: Dict[YangIdentifier, ModuleId]
        """Map of prefixes to module identifiers."""
        self.features = set() # type: MutableSet[YangIdentifier]
        """Set of supported features."""
        self.submodules = set() # type: MutableSet[ModuleId]
        """Set of submodules."""

class Context:
    """Global repository of data model structures and utility methods."""

    @classmethod
    def _initialize(cls) -> None:
        """Initialize the data model structures."""
        cls.module_search_path = [] # type: List[str]
        """List of directories where to look for YANG modules."""
        cls.modules = {} # type: Dict[ModuleId, ModuleData]
        """Dictionary of module data."""
        cls.implement = {} # type: Dict[YangIdentifier, RevisionDate]
        """Dictionary of implemented revisions."""
        cls.identity_bases = {} # type: Dict[QualName, MutableSet[QualName]]
        """Dictionary of identity bases."""
        cls._module_sequence = [] # type: List[ModuleId]
        """List that defines the order of module processing."""

    @classmethod
    def _from_yang_library(cls, yang_lib: Dict[str, Any],
                           mod_path: List[str]) -> None:
        """Set the data model structures from YANG library data.

        This method requires that the class variable `schema` be
        initialized beforehand with a GroupNode instance.

        Args:
            yang_lib: Dictionary with YANG library data.
            mod_path: Value for `Context.module_search_path`.

        Raises:
            BadYangLibraryData: If YANG library data is invalid.
            FeaturePrerequisiteError: If a pre-requisite feature isn't
                supported.
            MultipleImplementedRevisions: If multiple revisions of an
                implemented module are listed in YANG library.
            ModuleNotFound: If a YANG module wasn't found in any of the
                directories specified in `mod_path`.
        """
        cls._initialize()
        cls.module_search_path = mod_path
        cls.schema._config = True
        try:
            for item in yang_lib["ietf-yang-library:modules-state"]["module"]:
                name = item["name"]
                rev = item["revision"]
                mid = (name, rev)
                mdata = ModuleData(mid)
                cls.modules[mid] = mdata
                if item["conformance-type"] == "implement":
                    if name in cls.implement:
                        raise MultipleImplementedRevisions(name)
                    cls.implement[name] = rev
                mod = cls._load_module(name, rev)
                mdata.statement = mod
                if "feature" in item:
                    mdata.features.update(item["feature"])
                locpref = mod.find1("prefix", required=True).argument
                mdata.prefix_map[locpref] = mid
                if "submodule" in item:
                    for s in item["submodule"]:
                        sname = s["name"]
                        smid = (sname, s["revision"])
                        sdata = ModuleData(mid)
                        cls.modules[smid] = sdata
                        mdata.submodules.add(smid)
                        submod = cls._load_module(*smid)
                        sdata.statement = submod
                        bt = submod.find1("belongs-to", name, required=True)
                        locpref = bt.find1("prefix", required=True).argument
                        sdata.prefix_map[locpref] = mid
        except KeyError as e:
            raise BadYangLibraryData("missing " + str(e)) from None
        cls._process_imports()
        cls._check_feature_dependences()
        for mid in cls._module_sequence:
            cls.schema._new_ns = cls.namespace(mid)
            cls.schema._handle_substatements(cls.modules[mid].statement, mid)
        cls._apply_augments()
        cls.schema._post_process()
        cls.schema._make_schema_patterns()

    @classmethod
    def _load_module(cls, name: YangIdentifier,
                    rev: RevisionDate) -> Statement:
        """Read and parse a YANG module or submodule."""
        for d in cls.module_search_path:
            fn = "{}/{}".format(d, name)
            if rev: fn += "@" + rev
            fn += ".yang"
            try:
                with open(fn, encoding='utf-8') as infile:
                    res = ModuleParser(infile.read()).parse()
            except FileNotFoundError:
                continue
            return res
        raise ModuleNotFound(name, rev)

    @classmethod
    def _process_imports(cls) -> None:
        impl = set(cls.implement.items())
        deps = { mid: set() for mid in impl }
        impby = { mid: set() for mid in impl }
        for mid in cls.modules:
            mod = cls.modules[mid].statement
            for impst in mod.find_all("import"):
                impn = impst.argument
                prefix = impst.find1("prefix", required=True).argument
                revst = impst.find1("revision-date")
                if revst:
                    imid = (impn, revst.argument)
                    if imid not in cls.modules:
                        raise ModuleNotRegistered(impn, rev)
                else:                              # use last revision
                    imid = cls.last_revision(impn)
                cls.modules[mid].prefix_map[prefix] = imid
                mm = cls.modules[mid].main_module
                if mm in impl and imid in impl:
                    deps[mm].add(imid)
                    impby[imid].add(mm)
        free = [mid for mid in deps if len(deps[mid]) == 0]
        if not free: raise CyclicImports()
        while free:
            nid = free.pop()
            cls._module_sequence.append(nid)
            cls._module_sequence.extend(cls.modules[nid].submodules)
            for mid in impby[nid]:
                deps[mid].remove(nid)
                if len(deps[mid]) == 0:
                    free.append(mid)
        if [mid for mid in deps if len(deps[mid]) > 0]:
            raise CyclicImports()

    @classmethod
    def _check_feature_dependences(cls):
        """Verify feature dependences."""
        for mid in cls.modules:
            for fst in cls.modules[mid].statement.find_all("feature"):
                fn, fid = cls.resolve_pname(fst.argument, mid)
                if fn not in cls.modules[fid].features: continue
                if not cls.if_features(fst, mid):
                    raise FeaturePrerequisiteError(*fn)

    @classmethod
    def _apply_augments(cls) -> None:
        """Apply top-level augments from all implemented modules."""
        for mid in cls._module_sequence:
            mod = cls.modules[mid].statement
            for aug in mod.find_all("augment"):
                cls.schema._augment_stmt(aug, mid)

    @classmethod
    def namespace(cls, mid: ModuleId) -> YangIdentifier:
        """Return the namespace corresponding to a module or submodule.

        Args:
            mid: Module identifier.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
        """
        try:
            mdata = cls.modules[mid]
        except KeyError:
            raise ModuleNotRegistered(*mid) from None
        return mdata.main_module[0]

    @classmethod
    def last_revision(cls, name: YangIdentifier) -> ModuleId:
        """Return the last revision of a module that's part of the data model.

        Args:
            name: Name of a module or submodule.

        Raises:
            ModuleNotRegistered: If the module `name` is not present in the
                data model.
        """
        revs = [mn for mn in cls.modules if mn[0] == name]
        if not revs:
            raise ModuleNotRegistered(impn)
        return sorted(revs, key=lambda x: x[1])[-1]

    @classmethod
    def prefix2ns(cls, prefix: YangIdentifier, mid: ModuleId) -> YangIdentifier:
        """Return the namespace corresponding to a prefix.

        Args:
            prefix: Prefix associated with a module and its namespace.
            mid: Identifier of the module in which the prefix is declared.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
            UnknownPrefix: If `prefix` is not declared.
        """
        try:
            mdata = cls.modules[mid]
        except KeyError:
            raise ModuleNotRegistered(*mid) from None
        try:
            return mdata.prefix_map[prefix][0]
        except KeyError:
            raise UnknownPrefix(prefix) from None

    @classmethod
    def resolve_pname(cls, pname: PrefName,
                      mid: ModuleId) -> Tuple[YangIdentifier, ModuleId]:
        """Return the name and module identifier in which the name is defined.

        Args:
            pname: Name with an optional prefix.
            mid: Identifier of the context module.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
            UnknownPrefix: If the prefix specified in `pname` is not declared.
        """
        p, s, loc = pname.partition(":")
        try:
            mdata = cls.modules[mid]
        except KeyError:
            raise ModuleNotRegistered(*mid) from None
        try:
            return (loc, mdata.prefix_map[p]) if s else (p, mdata.main_module)
        except KeyError:
            raise UnknownPrefix(p) from None

    @classmethod
    def translate_pname(cls, pname: PrefName, mid: ModuleId) -> QualName:
        """Translate a prefixed name to a qualified name.

        Args:
            pname: Name with an optional prefix.
            mid: Identifier of the context module.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
            UnknownPrefix: If the prefix specified in `pname` is not declared.
        """
        loc, nid = cls.resolve_pname(pname, mid)
        return (loc, cls.namespace(nid))

    @classmethod
    def sid2route(cls, sid: SchemaNodeId, mid: ModuleId) -> SchemaRoute:
        """Translate a schema node identifier to a schema route.

        Args:
            sid: Schema node identifier (absolute or relative).
            mid: Identifier of the context module.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
            UnknownPrefix: If a prefix specified in `sid` is not declared.
        """
        nlist = sid.split("/")
        return [ cls.translate_pname(qn, mid)
                 for qn in (nlist[1:] if sid[0] == "/" else nlist) ]

    @staticmethod
    def path2route(path: SchemaPath) -> SchemaRoute:
        """Translate a schema/data path to a schema/data route.

        Args:
            path: Schema path.

        Raises:
            BadPath: Invalid path.
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
    def get_definition(cls, stmt: Statement,
                       mid: ModuleId) -> Tuple[Statement, ModuleId]:
        """Find the statement defining a grouping or derived type.

        Args:
            stmt: YANG "uses" or "type" statement.
            mid: Identifier of the context module.

        Returns:
            A tuple consisting of the definition statement ('grouping' or
            'typedef') and indentifier of the module where it appears.

        Raises:
            ValueError: If `stmt` is neither "uses" nor "type" statement.
            ModuleNotRegistered: If `mid` is not registered in the data model.
            UnknownPrefix: If the prefix specified in the argument of `stmt`
                is not declared.
            DefinitionNotFound: If the corresponding definition is not found.
        """
        if stmt.keyword == "uses":
            kw = "grouping"
        elif stmt.keyword == "type":
            kw = "typedef"
        else:
            raise ValueError("not a 'uses' or 'type' statement")
        loc, did = cls.resolve_pname(stmt.argument, mid)
        if did == mid:
            return (stmt.get_definition(loc, kw), mid)
        dstmt = cls.modules[did].statement.find1(kw, loc)
        if dstmt: return (dstmt, did)
        for sid in cls.modules[did].submodules:
            dstmt = cls.modules[sid].statement.find1(kw, loc)
            if dstmt: return (dstmt, sid)
        raise DefinitionNotFound(kw, stmt.argument)

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
    def if_features(cls, stmt: Statement, mid: ModuleId) -> bool:
        """Evaluate ``if-feature`` substatements on a statement, if any.

        Args:
            stmt: Yang statement that is tested on if-features.
            mid: Identifier of the context module.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
            InvalidFeatureExpression: If a if-feature expression is not
                syntactically correct.
            UnknownPrefix: If a prefix specified in `sid` is not declared.
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

        Args:
            mid: Identifier of the context module.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
        """
        super().__init__(text)
        try:
            self.mdata = Context.modules[mid]
        except KeyError:
            raise ModuleNotRegistered(*mid) from None

    def parse(self) -> bool:
        """Parse and evaluate a complete feature expression.

        Raises:
            InvalidFeatureExpression: If the if-feature expression is not
                syntactically correct.
            UnknownPrefix: If a prefix of a feature name is not declared.
        """
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
        n, p = self.prefixed_name()
        self.skip_ws()
        if p is None:
            fid = self.mdata.main_module
        else:
            try:
                fid = self.mdata.prefix_map[p]
            except KeyError:
                raise UnknownPrefix(p) from None
        return n in Context.modules[fid].features

class _MissingModule(YangsonException):
    """Abstract exception – a module is missing."""

    def __init__(self, name: YangIdentifier, rev: str = "") -> None:
        self.name = name
        self.rev = rev

    def __str__(self) -> str:
        if self.rev:
            return self.name + "@" + self.rev
        return self.name

class ModuleNotFound(_MissingModule):
    """A module or submodule registered in YANG library is not found."""
    pass

class ModuleNotRegistered(_MissingModule):
    """An imported module is not registered in YANG library."""
    pass

class BadYangLibraryData(YangsonException):
    """Broken YANG library data."""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def __str__(self) -> str:
        return self.reason

class BadPath(YangsonException):
    """Invalid schema or data path."""

    def __init__(self, path: str) -> None:
        self.path = path

    def __str__(self) -> str:
        return self.path

class UnknownPrefix(YangsonException):
    """Unknown namespace prefix."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def __str__(self) -> str:
        return self.prefix

class InvalidFeatureExpression(ParserException):
    """Invalid **if-feature** expression."""
    pass

class FeaturePrerequisiteError(YangsonException):
    """Pre-requisite feature is not supported."""

    def __init__(self, name: YangIdentifier, ns: YangIdentifier) -> None:
        self.name = name
        self.ns = ns

    def __str__(self) -> str:
        return "{}:{}".format(self.ns, self.name)

class MultipleImplementedRevisions(YangsonException):
    """A module has multiple implemented revisions."""

    def __init__(self, module: YangIdentifier) -> None:
        self.module = module

    def __str__(self) -> str:
        return self.module

class CyclicImports(YangsonException):
    """YANG modules are imported in a cyclic fashion."""
    pass
