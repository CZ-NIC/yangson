***********
Schema Data
***********

.. module:: yangson.schemadata
   :synopsis: Repository of schema data extracted from YANG modules + related methods.

.. testsetup::

   import os
   from yangson import DataModel
   from yangson.schemadata import SchemaContext
   os.chdir("examples/ex3")

.. testcleanup::

   os.chdir("../..")

The *schemadata* module implements the following classes:

* :class:`IdentityAdjacency`: Adjacency data for an identity.
* :class:`SchemaContext`: Schema data and current schema context.
* :class:`ModuleData`: Data related to a YANG module or submodule.
* :class:`SchemaData`: Repository of data model structures and methods.
* :class:`FeatureExprParser`: Parser for **if-feature** expressions.

Doctest__ snippets for this module use the data model from :ref:`sec-ex3`.

__ http://www.sphinx-doc.org/en/stable/ext/doctest.html

.. doctest::

   >>> dm = DataModel.from_file("yang-library-ex3.json",
   ... [".", "../../../yang-modules/ietf"])

.. class:: IdentityAdjacency()

   Objects of this class hold information about adjacencies of an
   identity, i.e. (i) its base identities and (ii) identities that are
   directly derived from it.

   These objects are intended to be used only as values of the
   :attr:`SchemaData.identity_adjs` – each describes adjacencies of
   the identity appearing in the corresponding key (henceforth denoted
   as the “key identity”).

   .. rubric:: Instance Attributes

   .. attribute:: bases

      Mutable set of :term:`qualified name`\ s of identities that are defined
      as bases of the key identity.

   .. attribute:: derivs

      Mutable set of :term:`qualified name`\ s of identities that are
      directly derived from the key identity.

.. class:: SchemaContext(schema_data: SchemaData, default_ns: \
	   YangIdentifier, text_mid: ModuleId)

   An object of this class contains the current schema context that is
   passed along during the processing of YANG modules. Its instance
   attributes are initialized from constructor arguments of the same
   name.

   .. rubric:: Instance Attributes

   .. attribute:: schema_data

      An object of the :class:`SchemaData` class.

   .. attribute:: default_ns

      Current default namespace (module name) that is assigned to
      unprefixed node identifiers. This attribute may differ from the
      namespace of the module identified by *text_mid* inside a
      **grouping** or **typedef** definition that is used in another
      module (see [RFC7950]_, sec. `6.4.1`_).

   .. attribute:: text_mid

      Identifier of the current YANG module that defines the context
      for resolving namespace prefixes.

.. class:: ModuleData(main_module: YangIdentifier)

   An object of this class contains data related to a single module or
   submodule that is a part of the data model. Such objects are values
   of the dictionary :attr:`SchemaData.modules`.

   The constructor argument *main_module* contains the value for
   :attr:`main_module` instance attribute.

   .. rubric:: Instance Attributes

   .. attribute:: features

      Set of features defined in the receiver module that are
      supported by the data model.

   .. attribute:: main_module

      This attribute contains the :term:`module identifier` of the
      main module corresponding to the receiver.

   .. attribute:: prefix_map

      Dictionary that maps prefixes declared in the receiver module
      to :term:`module identifier`\ s.

   .. attribute:: statement

      The **module** or **submodule** statement corresponding to the
      receiver. It is the entry point to the hierarchy of the
      (sub)module statements.

   .. attribute:: submodules

      Set of submodules of the receiver module. If the receiver is a
      submodule, then this set is by definition empty.

.. class:: SchemaData(yang_lib: Dict[str, Any], mod_path: List[str])

   This class serves as a global for various data structures related
   to the schema that are extracted from YANG modules, and provides a
   number of methods for retrieving and processing this data.

   The *yang_lib* constructor argument contains a dictionary with YANG
   library data [RFC7895]_ that is typically parsed from JSON text
   using the functions :func:`json.load` or :func:`json.loads`. The
   second constructor argument, *mod_path*, initializes the instance
   attribute :attr:`module_search_path`.

   .. rubric:: Instance Attributes

   .. attribute:: identity_adjs

      Dictionary containing adjacency data of all identities defined
      by the data model.

      The keys are :term:`qualified name`\ s of identities, and each
      value is an object of the :class:`IdentityAdjacency` class.

      .. doctest::

	 >>> sorted(dm.schema_data.identity_adjs[('idZ', 'example-3-b')].bases)
	 [('idX', 'example-3-a'), ('idY', 'example-3-b')]
	 >>> dm.schema_data.identity_adjs[('idX', 'example-3-a')].derivs
	 {('idZ', 'example-3-b')}

   .. attribute:: implement

      Dictionary of implemented modules. They correspond to YANG
      library entries that have conformance type ``implement``. For
      each module, only one revision can be implemented – other
      revisions may be present but only with conformance type ``import``.

      The keys of this dictionary are module names, and the values are
      revision dates.

      .. doctest::

	 >>> dm.schema_data.implement['example-3-b']
	 '2016-08-22'

   .. attribute:: module_search_path

      List of directories where to look for YANG modules.

      All YANG modules and submodules listed in YANG library data have
      to be located in one of these directories.

      .. doctest::

	 >>> dm.schema_data.module_search_path
	 ['.', '../../../yang-modules/ietf']

   .. attribute:: modules

      Dictionary of modules and submodules comprising the data model.

      The keys are :term:`module identifier`\ s, and the values are
      objects of the :class:`ModuleData` class.

      .. doctest::

	 >>> len(dm.schema_data.modules)
	 5
	 >>> dm.schema_data.modules[('example-3-a', '2016-06-18')].main_module
	 ('example-3-a', '2016-06-18')
	 >>> dm.schema_data.modules[('example-3-suba', '2016-07-21')].main_module
	 ('example-3-a', '2016-06-18')
	 >>> dm.schema_data.modules[('example-3-suba', '2016-07-21')].prefix_map['inet']
	 ('ietf-inet-types', '2013-07-15')
	 >>> sorted(dm.schema_data.modules[('example-3-a', '2016-06-18')].features)
	 ['fea1', 'fea2']

   .. rubric:: Public Methods

   .. method:: namespace(mid: ModuleId) -> YangIdentifier

      Return the namespace corresponding to a module or submodule. The
      argument *mid* is the :term:`module identifier` of the
      (sub)module.

      Note that *Yangson* uses main module module names rather than
      URIs as namespace identifiers.

      This method raises :exc:`~.ModuleNotRegistered` if the (sub)module
      identified by *mid* is not part of the data model.

      .. doctest::

	 >>> dm.schema_data.namespace(('example-3-suba', '2016-07-21'))
	 'example-3-a'

   .. method:: last_revision(name: YangIdentifier) -> ModuleId

      Return :term:`module identifier` of the most recent revision of
      a module or submodule *name*.

      The method raises :exc:`~.ModuleNotRegistered` if no (sub)module
      of that name is part of the data model.

      .. doctest::

	 >>> dm.schema_data.last_revision('ietf-inet-types')
	 ('ietf-inet-types', '2013-07-15')

   .. method:: prefix2ns(prefix: YangIdentifier, mid: ModuleId) \
		    -> YangIdentifier

      Return namespace identifier corresponding to *prefix*. The
      module or submodule context, in which the prefix is resolved, is
      specified by the *mid* argument.

      This method raises :exc:`~.ModuleNotRegistered` if the (sub)module
      identified by *mid* is not part of the data model, and
      :exc:`~.UnknownPrefix` if *prefix* is not declared in that
      (sub)module.

      .. doctest::

	 >>> dm.schema_data.prefix2ns('oin', ('example-3-b', '2016-08-22'))
	 'ietf-inet-types'

   .. method:: resolve_pname(pname: PrefName, mid: ModuleId) \
		    -> Tuple[YangIdentifier, ModuleId]

      Resolve :term:`prefixed name` *pname* and return a tuple
      consisting of an unprefixed name and a :term:`module identifier`
      of the (sub)module in which that name is defined. The argument
      *mid* specifies the (sub)module in which *pname* is to be
      resolved. If *pname* has no prefix, *mid* is used as the second
      component of the result.

      This method raises :exc:`~.ModuleNotRegistered` if the (sub)module
      identified by *mid* is not part of the data model, and
      :exc:`~.UnknownPrefix` if the prefix specified in *pname* is not
      declared in that (sub)module.

      .. doctest::

	 >>> dm.schema_data.resolve_pname('oin:port-number', ('example-3-b', '2016-08-22'))
	 ('port-number', ('ietf-inet-types', '2010-09-24'))


   .. method:: translate_pname(pname: PrefName, mid: ModuleId) \
	       -> QualName

      Translate :term:`prefixed name` *pname* to a :term:`qualified
      name`. The argument *mid* specifies the (sub)module in which
      *pname* is to be resolved. If *pname* has no prefix, the
      namespace of the module identified by *mid* is assigned by
      default.

      This method raises :exc:`~.ModuleNotRegistered` if the (sub)module
      identified by *mid* is not part of the data model, and
      :exc:`~.UnknownPrefix` if the prefix specified in *pname* is not
      declared in that (sub)module.

      .. doctest::

	 >>> dm.schema_data.translate_pname('oin:port-number', ('example-3-b', '2016-08-22'))
	 ('port-number', 'ietf-inet-types')

   .. method:: translate_node_id(ni: PrefName, sctx:SchemaContext) \
	       -> QualName

      Translate :term:`node identifier` *ni* to a :term:`qualified
      name`. The argument *sctx* contains a :class:`SchemaContext` in
      which *ni* is resolved.

      This method raises :exc:`~.ModuleNotRegistered` if the (sub)module
      identified by the :attr:`~.SchemaContext.text_mid` attribute of
      *sctx* is not part of the data model, and :exc:`~.UnknownPrefix`
      if the prefix specified in *ni* is not declared in that
      (sub)module.

      .. doctest::

         >>> sctx1 = SchemaContext(dm.schema_data, 'example-3-b', ('example-3-a', '2016-08-18'))
         >>> dm.schema_data.translate_node_id('bar', sctx1)
	 ('bar', 'example-3-b')

   .. method:: prefix(imod: YangIdentifier, mid: ModuleId) -> \
		    YangIdentifier

      Return namespace prefix declared for :term:`implemented module`
      *imod* in the module or submodule whose :term:`module
      identifier` is *mid*.

      This method may raise the following exceptions:

      * :exc:`~.ModuleNotImplemented` – if module *imod* is not
	implemented.
      * :exc:`~.ModuleNotRegistered` – if (sub)module identified by
	*mid* is not registered in YANG library.
      * :exc:`~.ModuleNotImported` – if *imod* is not imported in the
	(sub)module identified by *mid*.

      .. doctest::

	 >>> dm.schema_data.prefix("example-3-a", ("example-3-b", "2016-08-22"))
	 'ex3a'

   .. method:: sni2route(sni: SchemaNodeId, sctx: SchemaContext) \
		    -> SchemaRoute

      Translate :term:`schema node identifier` *sni* to a
      :term:`schema route`.  The argument *sctx* specifies the
      schema context in which *sni* is to be resolved.

      This method raises :exc:`~.ModuleNotRegistered` if the (sub)module
      identified by *mid* is not part of the data model, and
      :exc:`~.UnknownPrefix` if a prefix specified in *sni* is not
      declared in that (sub)module.

      .. doctest::

         >>> sctx2 = SchemaContext(dm.schema_data, 'example-3-b', ('example-3-b', '2016-08-22')) 
	 >>> dm.schema_data.sni2route('/ex3a:top/ex3a:bar', sctx2)
	 [('top', 'example-3-a'), ('bar', 'example-3-a')]

   .. staticmethod:: path2route(path: SchemaPath) -> SchemaRoute

      Translate :term:`schema path` or :term:`data path` in the *path*
      argument to a :term:`schema route` or :term:`data route`,
      respectively.

      This method raises :exc:`~.BadPath` if *path* is not a valid
      schema or data path.

      .. doctest::

	 >>> dm.schema_data.path2route('/example-3-a:top/bar')
	 [('top', 'example-3-a'), ('bar', 'example-3-a')]

   .. method:: get_definition(stmt: Statement, sctx: SchemaContext) \
		    -> Tuple[Statement, SchemaContext]

      Find the **grouping** or **typedef** statement to which the
      statement in the *stmt* argument refers. The argument *sctx*
      specifies the schema context in which the name of the grouping
      or type is to be resolved. The returned value is a tuple
      consisting of the definition statement and a new
      :class:`SchemaContext` in which the definition appears.

      This method may raise the following exceptions:

      * :exc:`~.ValueError` – if the *stmt* statement is neither
	**uses** nor **type** statement.
      * :exc:`~.ModuleNotRegistered` – if the (sub)module identified by
	*mid* is not part of the data model.
      * :exc:`~.UnknownPrefix` – if the prefix specified in the argument
	of the *stmt* statement is not declared in the *mid*
	(sub)module.
      * :exc:`~.DefinitionNotFound` – if the corresponding definition
	statement is not found.

      .. doctest::

	 >>> bmod = dm.schema_data.modules[('example-3-b', '2016-08-22')].statement
	 >>> baztype = bmod.find1("augment").find1("leaf").find1("type")
	 >>> pn = dm.schema_data.get_definition(baztype, sctx2)
	 >>> pn[0].keyword
	 'typedef'
	 >>> pn[0].argument
	 'port-number'
	 >>> pn[1].text_mid
	 ('ietf-inet-types', '2010-09-24')

   .. method:: is_derived_from(identity: QualName, base: \
		    QualName) -> bool

      Return ``True`` if the identity specified in the *identity*
      argument is derived (directly or transitively) from the identity
      *base*, otherwise return ``False``.

      .. doctest::

	 >>> dm.schema_data.is_derived_from(('idZ', 'example-3-b'), ('idX', 'example-3-a'))
	 True

   .. method:: derived_from(identity: QualName) -> MutableSet[QualName]

      Return the set of :term:`qualified name`\ s of identities that
      are transitively derived from *identity*.

      .. doctest::

	 >>> dm.schema_data.derived_from(('idX', 'example-3-a'))
	 {('idZ', 'example-3-b')}

   .. method:: derived_from_all(identities: List[QualName]) -> MutableSet[QualName]

      Return the set of :term:`qualified name`\ s of identities that
      are transitively derived from all identities contained in the
      *identities* list.

      .. doctest::

	 >>> dm.schema_data.derived_from_all([('idX', 'example-3-a'), ('idY', 'example-3-b')])
	 {('idZ', 'example-3-b')}
	 >>> dm.schema_data.derived_from_all([('idX', 'example-3-a'), ('idZ', 'example-3-b')])
	 set()

   .. method:: if_features(stmt: Statement, mid: ModuleId) -> bool

      Evaluate all **if-feature** statements that are substatements of
      *stmt*. Return ``False`` if any of them is false, otherwise
      return ``True``. If the statement *stmt* has no **if-feature**
      substatements, ``True`` is returned. The argument *mid*
      specifies the (sub)module in which features names are to be
      resolved.

      This method may raise the following exceptions:

      * :exc:`~.InvalidFeatureExpression` – if the argument of an
	**if-feature** statement is not syntactically correct.
      * :exc:`~.ModuleNotRegistered` – if the (sub)module identified by
	*mid* is not part of the data model.
      * :exc:`~.UnknownPrefix` – if a prefix of a feature name is not
	declared in the *mid* (sub)module.

      .. doctest::

	 >>> amod = dm.schema_data.modules[('example-3-a', '2016-06-18')].statement
	 >>> foo = amod.find1("container").find1("leaf")
	 >>> dm.schema_data.if_features(foo, ('example-3-a', '2016-06-18'))
	 True

.. class:: FeatureExprParser(text: str, schema_data: SchemaData, mid: ModuleId)

   This class implements a parser and evaluator of expressions
   appearing in the argument of **if-feature** statements. It is a
   subclass of :class:`~.parser.Parser`.

   The arguments of the class constructor are:

   * *text* – feature expression text to parse,
   * *schema_data* - 
   * *mid* – value for :attr:`mid` attribute.

   The constructor may raise :exc:`~.ModuleNotRedistered` if the
   (sub)module identified by *mid* is not part of the data model.

   .. rubric:: Instance Attributes

   .. attribute:: mid

      This attribute is a :term:`module identifier` of the (sub)module
      that provides context for parsing and evaluating the feature
      expression.

   .. attribute:: schema_data

      This attribute contains a :class:`SchemaData` object describing the
      current schema for which the feature expression is to be evaluated.

   Two other instance attributes (:attr:`~.Parser.input` and
   :attr:`~.Parser.offset`) are inherited from the :class:`Parser`
   class.

   .. rubric:: Public Methods

   .. method:: parse() -> bool

      Parse and evaluate a feature expression, and return the result.

      This method may raise the following exceptions:

      * :exc:`~.InvalidFeatureExpression` – if the input is not a
	syntactically correct feature expression.
      * :exc:`~.UnknownPrefix` – if a prefix of a feature name is not
	declared.

      .. doctest::

	 >>> from yangson.schemadata import FeatureExprParser
	 >>> FeatureExprParser('ex3a:fea1 and not (ex3a:fea1 or ex3a:fea2)',
	 ... dm.schema_data, ('example-3-a', '2016-06-18')).parse()
	 False

.. _5.6.5: https://tools.ietf.org/html/rfc7950#section-5.6.5
.. _5.1: https://tools.ietf.org/html/rfc7950#section-5.1
.. _6.4.1: https://tools.ietf.org/html/rfc7950#section-6.4.1
