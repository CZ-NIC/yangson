# Copyright © 2016, 2017 CZ.NIC, z. s. p. o.
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

"""
Essential YANG schema structures and methods.

This module implements the following classes:

* SchemaContext: Schema data and current schema context.
* ModuleData: Data related to a YANG module or submodule.
* SchemaData: Repository of YANG schema structures and methods.
* FeatureExprParser: Parser for if-feature expressions.
"""

from typing import Dict, List, MutableSet, Optional, Tuple
from .exceptions import (
    InvalidSchemaPath, BadYangLibraryData, CyclicImports, DefinitionNotFound,
    FeaturePrerequisiteError, InvalidFeatureExpression, ModuleNotFound,
    ModuleNotImplemented, ModuleNotImported, ModuleNotRegistered,
    MultipleImplementedRevisions, UnknownPrefix)
from .parser import Parser
from .statement import ModuleParser, Statement
from .typealiases import *

class IdentityAdjacency:
    """Adjacency data for an identity."""

    def __init__(self):
        self.bases = set() # type: MutableSet[QualName]
        self.derivs = set() # type: MutableSet[QualName]

class SchemaContext:
    """Schema data and current schema context."""

    def __init__(self, schema_data: "SchemaData", default_ns: YangIdentifier,
                     text_mid: ModuleId):
        """Initialize the class instance."""
        self.schema_data = schema_data
        self.default_ns = default_ns
        """Name of the module that represents the current default namespace."""
        self.text_mid = text_mid
        """Identifier of the module that is currently being read."""

class ModuleData:
    """Data related to a YANG module or submodule."""

    def __init__(self, main_module: YangIdentifier):
        """Initialize the class instance."""
        self.features = set() # type: MutableSet[YangIdentifier]
        """Set of supported features."""
        self.main_module = main_module # type: ModuleId
        """Main module of the receiver."""
        self.prefix_map = {} # type: Dict[YangIdentifier, ModuleId]
        """Map of prefixes to module identifiers."""
        self.statement = None # type: Statement
        """Corresponding (sub)module statements."""
        self.submodules = set() # type: MutableSet[ModuleId]
        """Set of submodules."""

class SchemaData:
    """Repository of YANG schema structures and utility methods.

        Args:
            yang_lib: Dictionary with YANG library data.
            mod_path: List of directories to search for YANG modules.
    """

    def __init__(self, yang_lib: Dict[str, Any], mod_path: List[str]) -> None:
        """Initialize the schema structures."""
        self.identity_adjs = {} # type: Dict[QualName, IdentityAdjacency]
        """Dictionary of identity bases."""
        self.implement = {} # type: Dict[YangIdentifier, RevisionDate]
        """Dictionary of implemented revisions."""
        self.module_search_path = mod_path
        """List of directories where to look for YANG modules."""
        self.modules = {} # type: Dict[ModuleId, ModuleData]
        """Dictionary of module data."""
        self._module_sequence = [] # type: List[ModuleId]
        """List that defines the order of module processing."""
        self._from_yang_library(yang_lib)

    def _from_yang_library(self, yang_lib: Dict[str, Any]) -> None:
        """Set the schema structures from YANG library data.

        Args:
            yang_lib: Dictionary with YANG library data.

        Raises:
            BadYangLibraryData: If YANG library data is invalid.
            FeaturePrerequisiteError: If a pre-requisite feature isn't
                supported.
            MultipleImplementedRevisions: If multiple revisions of an
                implemented module are listed in YANG library.
            ModuleNotFound: If a YANG module wasn't found in any of the
                directories specified in `mod_path`.
        """
        try:
            for item in yang_lib["ietf-yang-library:modules-state"]["module"]:
                name = item["name"]
                rev = item["revision"]
                mid = (name, rev)
                mdata = ModuleData(mid)
                self.modules[mid] = mdata
                if item["conformance-type"] == "implement":
                    if name in self.implement:
                        raise MultipleImplementedRevisions(name)
                    self.implement[name] = rev
                mod = self._load_module(name, rev)
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
                        self.modules[smid] = sdata
                        mdata.submodules.add(smid)
                        submod = self._load_module(*smid)
                        sdata.statement = submod
                        bt = submod.find1("belongs-to", name, required=True)
                        locpref = bt.find1("prefix", required=True).argument
                        sdata.prefix_map[locpref] = mid
        except KeyError as e:
            raise BadYangLibraryData("missing " + str(e)) from None
        self._process_imports()
        self._check_feature_dependences()

    def _load_module(self, name: YangIdentifier,
                    rev: RevisionDate) -> Statement:
        """Read and parse a YANG module or submodule."""
        for d in self.module_search_path:
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

    def _process_imports(self) -> None:
        impl = set(self.implement.items())
        if len(impl) == 0: return
        deps = { mid: set() for mid in impl }
        impby = { mid: set() for mid in impl }
        for mid in self.modules:
            mod = self.modules[mid].statement
            for impst in mod.find_all("import"):
                impn = impst.argument
                prefix = impst.find1("prefix", required=True).argument
                revst = impst.find1("revision-date")
                if revst:
                    imid = (impn, revst.argument)
                    if imid not in self.modules:
                        raise ModuleNotRegistered(impn, rev)
                else:                              # use last revision
                    imid = self.last_revision(impn)
                self.modules[mid].prefix_map[prefix] = imid
                mm = self.modules[mid].main_module
                if mm in impl and imid in impl:
                    deps[mm].add(imid)
                    impby[imid].add(mm)
        free = [mid for mid in deps if len(deps[mid]) == 0]
        if not free: raise CyclicImports()
        while free:
            nid = free.pop()
            self._module_sequence.append(nid)
            self._module_sequence.extend(self.modules[nid].submodules)
            for mid in impby[nid]:
                deps[mid].remove(nid)
                if len(deps[mid]) == 0:
                    free.append(mid)
        if [mid for mid in deps if len(deps[mid]) > 0]:
            raise CyclicImports()

    def _check_feature_dependences(self):
        """Verify feature dependences."""
        for mid in self.modules:
            for fst in self.modules[mid].statement.find_all("feature"):
                fn, fid = self.resolve_pname(fst.argument, mid)
                if fn not in self.modules[fid].features: continue
                if not self.if_features(fst, mid):
                    raise FeaturePrerequisiteError(*fn)

    def namespace(self, mid: ModuleId) -> YangIdentifier:
        """Return the namespace corresponding to a module or submodule.

        Args:
            mid: Module identifier.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
        """
        try:
            mdata = self.modules[mid]
        except KeyError:
            raise ModuleNotRegistered(*mid) from None
        return mdata.main_module[0]

    def last_revision(self, mod: YangIdentifier) -> ModuleId:
        """Return the last revision of a module that's part of the data model.

        Args:
            mod: Name of a module or submodule.

        Raises:
            ModuleNotRegistered: If the module `mod` is not present in the
                data model.
        """
        revs = [mn for mn in self.modules if mn[0] == mod]
        if not revs:
            raise ModuleNotRegistered(mod)
        return sorted(revs, key=lambda x: x[1])[-1]

    def prefix2ns(self, prefix: YangIdentifier, mid: ModuleId) -> YangIdentifier:
        """Return the namespace corresponding to a prefix.

        Args:
            prefix: Prefix associated with a module and its namespace.
            mid: Identifier of the module in which the prefix is declared.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
            UnknownPrefix: If `prefix` is not declared.
        """
        try:
            mdata = self.modules[mid]
        except KeyError:
            raise ModuleNotRegistered(*mid) from None
        try:
            return mdata.prefix_map[prefix][0]
        except KeyError:
            raise UnknownPrefix(prefix, mid) from None

    def resolve_pname(self, pname: PrefName,
                      mid: ModuleId) -> Tuple[YangIdentifier, ModuleId]:
        """Return the name and module identifier in which the name is defined.

        Args:
            pname: Name with an optional prefix.
            mid: Identifier of the module in which `pname` appears.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
            UnknownPrefix: If the prefix specified in `pname` is not declared.
        """
        p, s, loc = pname.partition(":")
        try:
            mdata = self.modules[mid]
        except KeyError:
            raise ModuleNotRegistered(*mid) from None
        try:
            return (loc, mdata.prefix_map[p]) if s else (p, mdata.main_module)
        except KeyError:
            raise UnknownPrefix(p, mid) from None

    def translate_pname(self, pname: PrefName, mid: ModuleId) -> QualName:
        """Translate a prefixed name to a qualified name.
        Args:
            pname: Name with an optional prefix.
            mid: Identifier of the module in which `pname` appears.
        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
            UnknownPrefix: If the prefix specified in `pname` is not declared.
        """
        loc, nid = self.resolve_pname(pname, mid)
        return (loc, self.namespace(nid))

    def translate_node_id(self, ni: PrefName, sctx: SchemaContext) -> QualName:
        """Translate node identifier to a qualified name.

        Args:
            ni: Node identifier (with optional prefix).
            sctx: SchemaContext.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
            UnknownPrefix: If the prefix specified in `ni` is not declared.
        """
        p, s, loc = ni.partition(":")
        if not s: return (ni, sctx.default_ns)
        try:
            mdata = self.modules[sctx.text_mid]
        except KeyError:
            raise ModuleNotRegistered(*sctx.text_mid) from None
        try:
            return (loc, self.namespace(mdata.prefix_map[p]))
        except KeyError:
            raise UnknownPrefix(p, sctx.text_mid) from None

    def prefix(self, imod: YangIdentifier, mid: ModuleId) -> YangIdentifier:
        """Return the prefix corresponding to an implemented module.

        Args:
            imod: Name of an implemented module.
            mid: Identifier of the context module.

        Raises:
            ModuleNotImplemented: If `imod` is not implemented.
            ModuleNotRegistered: If `mid` is not registered in YANG library.
            ModuleNotImported: If `imod` is not imported in `mid`.
        """
        try:
            did = (imod, self.implement[imod])
        except KeyError:
            raise ModuleNotImplemented(imod) from None
        try:
            pmap = self.modules[mid].prefix_map
        except KeyError:
            raise ModuleNotRegistered(*mid) from None
        for p in pmap:
            if pmap[p] == did:
                return p
        raise ModuleNotImported(imod, mid)

    def sni2route(self, sni: SchemaNodeId, sctx: SchemaContext) -> SchemaRoute:
        """Translate schema node identifier to a schema route.

        Args:
            sni: Schema node identifier (absolute or relative).
            sctx: Schema context.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
            UnknownPrefix: If a prefix specified in `sni` is not declared.
        """
        nlist = sni.split("/")
        res = []
        for qn in (nlist[1:] if sni[0] == "/" else nlist):
            res.append(self.translate_node_id(qn, sctx))
        return res

    @staticmethod
    def path2route(path: SchemaPath) -> SchemaRoute:
        """Translate a schema/data path to a schema/data route.

        Args:
            path: Schema path.

        Raises:
            InvalidSchemaPath: Invalid path.
        """
        if path == "/" or path == "": return []
        nlist = path.split("/")
        prevns = None
        res = []
        for n in (nlist[1:] if path[0] == "/" else nlist):
            p, s, loc = n.partition(":")
            if s:
                if p == prevns: raise InvalidSchemaPath(path)
                res.append((loc, p))
                prevns = p
            elif prevns:
                res.append((p, prevns))
            else:
                raise InvalidSchemaPath(path)
        return res

    def get_definition(self, stmt: Statement,
                       sctx: SchemaContext) -> Tuple[Statement, SchemaContext]:
        """Find the statement defining a grouping or derived type.

        Args:
            stmt: YANG "uses" or "type" statement.
            sctx: Schema context where the definition is used.

        Returns:
            A tuple consisting of the definition statement ('grouping' or
            'typedef') and schema context of the definition.

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
        loc, did = self.resolve_pname(stmt.argument, sctx.text_mid)
        if did == sctx.text_mid:
            return (stmt.get_definition(loc, kw), sctx)
        dstmt = self.modules[did].statement.find1(kw, loc)
        if dstmt:
            return (dstmt, SchemaContext(sctx.schema_data, sctx.default_ns, did))
        for sid in self.modules[did].submodules:
            dstmt = self.modules[sid].statement.find1(kw, loc)
            if dstmt: return (
                    dstmt, SchemaContext(sctx.schema_data, sctx.default_ns, sid))
        raise DefinitionNotFound(kw, stmt.argument)

    def is_derived_from(self, identity: QualName, base: QualName) -> bool:
        """Return ``True`` if `identity` is derived from `base`."""
        try:
            bases = self.identity_adjs[identity].bases
        except KeyError:
            return False
        if base in bases: return True
        for ib in bases:
            if self.is_derived_from(ib, base): return True
        return False

    def derived_from(self, identity: QualName) -> MutableSet[QualName]:
        """Return list of identities transitively derived from `identity`."""
        try:
            res = self.identity_adjs[identity].derivs
        except KeyError:
            return set()
        for id in res.copy():
            res |= self.derived_from(id)
        return res

    def derived_from_all(self, identities: List[QualName]) -> MutableSet[QualName]:
        """Return list of identities transitively derived from all `identity`."""
        if not identities: return set()
        res = self.derived_from(identities[0])
        for id in identities[1:]:
            res &= self.derived_from(id)
        return res

    def if_features(self, stmt: Statement, mid: ModuleId) -> bool:
        """Evaluate ``if-feature`` substatements on a statement, if any.

        Args:
            stmt: Yang statement that is tested on if-features.
            mid: Identifier of the module in which `stmt` is present.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
            InvalidFeatureExpression: If a if-feature expression is not
                syntactically correct.
            UnknownPrefix: If a prefix specified in a feature name is not
                declared.
        """
        iffs = stmt.find_all("if-feature")
        if not iffs:
            return True
        for i in iffs:
            if not FeatureExprParser(i.argument, self, mid).parse():
                return False
        return True

class FeatureExprParser(Parser):
    """Parser and evaluator for if-feature expressions."""

    def __init__(self, text: str, schema_data: SchemaData, mid: ModuleId):
        """Initialize the parser instance.

        Args:
            text: Feature expression text.
            schema_data: Data for the current schema.
            mid: Identifier of the context module.

        Raises:
            ModuleNotRegistered: If `mid` is not registered in the data model.
        """
        super().__init__(text)
        self.mid = mid
        self.schema_data = schema_data

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
        try:
            mdata = self.schema_data.modules[self.mid]
        except KeyError:
            raise ModuleNotRegistered(*self.mid) from None
        if p is None:
            fid = mdata.main_module
        else:
            try:
                fid = mdata.prefix_map[p]
            except KeyError:
                raise UnknownPrefix(p, self.mid) from None
        return n in self.schema_data.modules[fid].features
