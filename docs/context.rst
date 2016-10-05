******************
Data Model Context
******************

.. module:: yangson.context
   :synopsis: Global repository of data model information and methods.

.. testsetup::

   import os
   from yangson import DataModel
   os.chdir("examples/ex3")

.. testcleanup::

   os.chdir("../..")
   del DataModel._instances[DataModel]

The *context* module implements the following classes:

* :class:`ModuleData`: Data related to a YANG module or submodule.
* :class:`Context`: Repository of data model structures and methods.
* :class:`FeatureExprParser`: Parser for **if-feature** expressions.

This module also defines the following exceptions:

* :exc:`BadPath`: Invalid :term:`schema path` or :term:`data path`.
* :exc:`BadYangLibraryData`: Broken YANG library data.
* :exc:`CyclicImports`: YANG modules are imported in a cyclic fashion.
* :exc:`FeaturePrerequisiteError`: Pre-requisite feature is not supported.
* :exc:`InvalidFeatureExpression`: Invalid **if-feature** expression.
* :exc:`ModuleNotFound`: A module or submodule registered in YANG library is not found.
* :exc:`ModuleNotImported`: A module is not imported.
* :exc:`ModuleNotRegistered`: An imported module is not registered in YANG library.
* :exc:`MultipleImplementedRevisions`: A module has multiple implemented revisions.
* :exc:`UnknownPrefix`: Unknown namespace prefix.

.. class:: ModuleData(main_module: YangIdentifier)

   An object of this class contains data related to a single module or
   submodule that is a part of the data model. Such objects are values
   of the dictionary :attr:`Context.modules`.

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

.. class:: Context

   This class serves as a global repository for the data model schema
   and several other important data structures that are stored as
   class attributes. This means that

   * it is possible to work with only one data model at a time,

   * no instances of this class are expected to be created.

   The :class:`Context` class also provides a number of class methods
   for retrieving and transforming this global data.

   Other Python modules that need the data model information and/or
   methods should import the :class:`Context` class.

   .. doctest::

      >>> from yangson.context import Context
      >>> dm = DataModel.from_file("yang-library-ex3.json", [".", "../../../examples/ietf"])

   .. rubric:: Class Attributes

   .. attribute:: identity_bases

      Dictionary of identity bases.

      The keys are :term:`qualified name`\ s of identities, and each
      value is a set of :term:`qualified name`\ s of identities that
      are defined as bases for the key identity.

      .. doctest::

	 >>> sorted(Context.identity_bases[('idZ', 'example-3-b')])
	 [('idX', 'example-3-a'), ('idY', 'example-3-b')]

   .. attribute:: implement

      Dictionary of implemented modules. They correspond to YANG
      library entries that have conformance type ``implement``. For
      each module, only one revision can be implemented – other
      revisions may be present but only with conformance type ``import``.

      The keys of this dictionary are module names, and the values are
      revision dates.

      .. doctest::

	 >>> Context.implement['example-3-b']
	 '2016-08-22'

   .. attribute:: module_search_path

      List of directories where to look for YANG modules.

      All YANG modules and submodules listed in YANG library data have
      to be located in one of these directories.

      .. doctest::

	 >>> Context.module_search_path
	 ['.', '../../../examples/ietf']

   .. attribute:: modules

      Dictionary of modules and submodules comprising the data model.

      The keys are :term:`module identifier`\ s, and the values are
      objects of the :class:`ModuleData` class.

      .. doctest::

	 >>> len(Context.modules)
	 5
	 >>> Context.modules[('example-3-a', '2016-06-18')].main_module
	 ('example-3-a', '2016-06-18')
	 >>> Context.modules[('example-3-suba', '2016-07-21')].main_module
	 ('example-3-a', '2016-06-18')
	 >>> Context.modules[('example-3-suba', '2016-07-21')].prefix_map['inet']
	 ('ietf-inet-types', '2013-07-15')
	 >>> sorted(Context.modules[('example-3-a', '2016-06-18')].features)
	 ['fea1', 'fea2']

   .. rubric:: Public Methods

   .. classmethod:: namespace(mid: ModuleId) -> YangIdentifier

      Return the namespace corresponding to a module or submodule. The
      argument *mid* is the :term:`module identifier` of the
      (sub)module.

      Note that *Yangson* uses main module module names rather than
      URIs as namespace identifiers.

      This method raises :exc:`ModuleNotRegistered` if the (sub)module
      identified by *mid* is not part of the data model.

      .. doctest::

	 >>> Context.namespace(('example-3-suba', '2016-07-21'))
	 'example-3-a'

   .. classmethod:: last_revision(name: YangIdentifier) -> ModuleId

      Return :term:`module identifier` of the most recent revision of
      a module or submodule *name*.

      The method raises :exc:`ModuleNotRegistered` if no (sub)module
      of that name is part of the data model.

      .. doctest::

	 >>> Context.last_revision('ietf-inet-types')
	 ('ietf-inet-types', '2013-07-15')

   .. classmethod:: prefix2ns(prefix: YangIdentifier, mid: ModuleId) \
		    -> YangIdentifier

      Return namespace identifier corresponding to *prefix*. The
      module or submodule context, in which the prefix is resolved, is
      specified by the *mid* argument.

      This method raises :exc:`ModuleNotRegistered` if the (sub)module
      identified by *mid* is not part of the data model, and
      :exc:`UnknownPrefix` if *prefix* is not declared in that
      (sub)module.

      .. doctest::

	 >>> Context.prefix2ns('oin', ('example-3-b', '2016-08-22'))
	 'ietf-inet-types'

   .. classmethod:: resolve_pname(pname: PrefName, mid: ModuleId) \
		    -> Tuple[YangIdentifier, ModuleId]

      Resolve :term:`prefixed name` *pname* and return a tuple
      consisting of an unprefixed name and a :term:`module identifier`
      of the (sub)module in which that name is defined. The argument
      *mid* specifies the (sub)module in which *pname* is to be
      resolved.

      This method raises :exc:`ModuleNotRegistered` if the (sub)module
      identified by *mid* is not part of the data model, and
      :exc:`UnknownPrefix` if the prefix specified in *pname* is not
      declared in that (sub)module.

      .. doctest::

	 >>> Context.resolve_pname('oin:port-number', ('example-3-b', '2016-08-22'))
	 ('port-number', ('ietf-inet-types', '2010-09-24'))


   .. classmethod:: translate_pname(pname: PrefName, mid: ModuleId) \
		    -> QualName

      Translate :term:`prefixed name` *pname* to a :term:`qualified
      name`. The argument *mid* specifies the (sub)module in which
      *pname* is to be resolved.

      This method raises :exc:`ModuleNotRegistered` if the (sub)module
      identified by *mid* is not part of the data model, and
      :exc:`UnknownPrefix` if the prefix specified in *pname* is not
      declared in that (sub)module.

      .. doctest::

	 >>> Context.translate_pname('oin:port-number', ('example-3-b', '2016-08-22'))
	 ('port-number', 'ietf-inet-types')

   .. classmethod:: prefix(imod: YangIdentifier, mid: ModuleId) -> \
		    YangIdentifier

      Return namespace prefix declared for :term:`implemented module`
      *imod* in the module or submodule whose :term:`module
      identifier` is *mid*.

      This method may raise the following exceptions:

      * :exc:`ModuleNotImplemented` – if module *imod* is not
	implemented.
      * :exc:`ModuleNotRegistered` – if (sub)module identified by
	*mid* is not registered in YANG library.
      * :exc:`ModuleNotImported` – if *imod* is not imported in the
	(sub)module identified by *mid*.

      .. doctest::

	 >>> Context.prefix("example-3-a", ("example-3-b", "2016-08-22"))
	 'ex3a'

   .. classmethod:: sni2route(sni: SchemaNodeId, mid: ModuleId) \
		    -> SchemaRoute

      Translate :term:`schema node identifier` *sni* to a
      :term:`schema route`.  The argument *mid* specifies the
      (sub)module in which *sni* is to be resolved.

      This method raises :exc:`ModuleNotRegistered` if the (sub)module
      identified by *mid* is not part of the data model, and
      :exc:`UnknownPrefix` if a prefix specified in *sni* is not
      declared in that (sub)module.

      .. doctest::

	 >>> Context.sni2route('/ex3a:top/ex3a:bar', ('example-3-b', '2016-08-22'))
	 [('top', 'example-3-a'), ('bar', 'example-3-a')]

   .. classmethod:: path2route(path: SchemaPath) -> SchemaRoute

      Translate :term:`schema path` or :term:`data path` in the *path*
      argument to a :term:`schema route` or :term:`data route`,
      respectively.

      This method raises :exc:`BadPath` if *path* is not a valid
      schema or data path.

      .. doctest::

	 >>> Context.path2route('/example-3-a:top/bar')
	 [('top', 'example-3-a'), ('bar', 'example-3-a')]

   .. classmethod:: get_definition(stmt: Statement, mid: ModuleId) \
		    -> Tuple[Statement, ModuleId]

      Find the **grouping** or **typedef** statement to which the
      statement in the *stmt* argument refers. The argument *mid*
      specifies the (sub)module in which the name of the grouping or
      type is to be resolved. The returned value is a tuple consisting
      of the definition statement and :term:`module identifier` of the
      (sub)module where the definition appears.

      This method may raise the following exceptions:

      * :exc:`ValueError` – if the *stmt* statement is neither
	**uses** nor **type** statement.
      * :exc:`ModuleNotRegistered` – if the (sub)module identified by
	*mid* is not part of the data model.
      * :exc:`UnknownPrefix` – if the prefix specified in the argument
	of the *stmt* statement is not declared in the *mid*
	(sub)module.
      * :exc:`DefinitionNotFound` – if the corresponding definition
	statement is not found.

      .. doctest::

	 >>> bmod = Context.modules[('example-3-b', '2016-08-22')].statement
	 >>> baztype = bmod.find1("augment").find1("leaf").find1("type")
	 >>> pn = Context.get_definition(baztype, ('example-3-b', '2016-08-22'))
	 >>> pn[0].keyword
	 'typedef'
	 >>> pn[0].argument
	 'port-number'
	 >>> pn[1]
	 ('ietf-inet-types', '2010-09-24')

   .. classmethod:: is_derived_from(identity: QualName, base: \
		    QualName) -> bool

      Return ``True`` if the identity specified in the *identity*
      argument is derived (directly or transitively) from the identity
      *base*, otherwise return ``False``.

      .. doctest::

	 >>> Context.is_derived_from(('idZ', 'example-3-b'), ('idX', 'example-3-a'))
	 True

   .. classmethod:: if_features(stmt: Statement, mid: ModuleId) -> bool

      Evaluate all **if-feature** statements that are substatements of
      *stmt*. Return ``False`` if any of them is false, otherwise
      return ``True``. If the statement *stmt* has no **if-feature**
      substatements, ``True`` is returned. The argument *mid*
      specifies the (sub)module in which features names are to be
      resolved.

      This method may raise the following exceptions:

      * :exc:`InvalidFeatureExpression` – if the argument of an
	**if-feature** statement is not syntactically correct.
      * :exc:`ModuleNotRegistered` – if the (sub)module identified by
	*mid* is not part of the data model.
      * :exc:`UnknownPrefix` – if a prefix of a feature name is not
	declared in the *mid* (sub)module.

      .. doctest::

	 >>> amod = Context.modules[('example-3-a', '2016-06-18')].statement
	 >>> foo = amod.find1("container").find1("leaf")
	 >>> Context.if_features(foo, ('example-3-a', '2016-06-18'))
	 True

.. class:: FeatureExprParser(text: str, mid: ModuleId)

   This class implements a parser and evaluator of expressions
   appearing in the argument of **if-feature** statements. It is a
   subclass of :class:`~.parser.Parser`.

   The arguments of the class constructor are:

   * *text* – text to parse,
   * *mid* – value for :attr:`mid` attribute.

   The constructor may raise :exc:`ModuleNotRedistered` if the
   (sub)module identified by *mid* is not part of the data model.

   .. rubric:: Instance Attributes

   .. attribute:: mid

      This attribute is a :term:`module identifier` of the (sub)module
      that provides context for parsing and evaluating the feature
      expression.

   Two other instance variables (:attr:`~.Parser.input` and
   :attr:`~.Parser.offset`) are inherited from the :class:`Parser`
   class.

   .. rubric:: Public Methods

   .. method:: parse() -> bool

      Parse and evaluate a feature expression, and return the result.

      This method may raise the following exceptions:

      * :exc:`InvalidFeatureExpression` – if the input is not a
	syntactically correct feature expression.
      * :exc:`UnknownPrefix` – if a prefix of a feature name is not
	declared.

      .. doctest::

	 >>> from yangson.context import FeatureExprParser
	 >>> FeatureExprParser('ex3a:fea1 and not (ex3a:fea1 or ex3a:fea2)',
	 ... ('example-3-a', '2016-06-18')).parse()
	 False

.. autoexception:: MissingModule(name: YangIdentifier, rev: str = "")

   The arguments specify the name and optional revision of the missing
   module.

.. autoexception:: ModuleNotFound(name: YangIdentifier, rev: str = "")
   :show-inheritance:

.. autoexception:: ModuleNotRegistered(name: YangIdentifier, rev: str = "")
   :show-inheritance:

.. autoexception:: ModuleNotImplemented(name: YangIdentifier, rev: str = "")
   :show-inheritance:

.. autoexception:: BadYangLibraryData
   :show-inheritance:

   The *reason* argument is a text describing the problem.

.. autoexception:: BadPath
   :show-inheritance:

   The *path* argument contains the invalid path.

.. autoexception:: UnknownPrefix
   :show-inheritance:

   The *prefix* argument contains the unknown prefix.

.. autoexception:: ModuleNotImported(mod: YangIdentifier, mid: ModuleId)
   :show-inheritance:

   Module *mod* is expected to be imported from a module or
   submodule whose :term:`module identifier` is *mid*.

.. autoexception:: InvalidFeatureExpression
   :show-inheritance:

.. autoexception:: FeaturePrerequisiteError(name: YangIdentifier, ns: YangIdentifier)
   :show-inheritance:

   The *name* and *ns* arguments contain the name and namespace of the
   feature for which a pre-requisite feature is not supported by the
   data model.

.. autoexception:: MultipleImplementedRevisions(module: YangIdentifier)
   :show-inheritance:

   See sec. `5.6.5`_ of [RFC7950]_ for further explanation. The *module*
   argument contains the name of the module with multiple implemented revisions.

.. autoexception:: CyclicImports
   :show-inheritance:

   See sec. `5.1`_ of [RFC7950]_ for further explanation.

.. _5.6.5: https://tools.ietf.org/html/rfc7950#section-5.6.5
.. _5.1: https://tools.ietf.org/html/rfc7950#section-5.1
