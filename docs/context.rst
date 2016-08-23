==================
Data Model Context
==================

.. module:: yangson.context
   :synopsis: Global repository of data model information and methods.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

.. testsetup::

   import os
   os.chdir("examples/ex3")

.. testcleanup::

   os.chdir("../..")
   del DataModel._instances[DataModel]

Essential data model structures and methods

This module implements the following classes:

* :class:`Context`: Repository of data model structures and methods.
* :class:`FeatureExprParser`: Parser for **if-feature** expressions.

The module defines the following exceptions:

* :exc:`ModuleNotFound`: YANG module not found.
* :exc:`BadYangLibraryData`: Invalid YANG library data.
* :exc:`BadPath`: Invalid :term:`schema path`
* :exc:`UnknownPrefix`: Unknown namespace prefix.
* :exc:`InvalidFeatureExpression`: Invalid **if-feature** expression.
* :exc:`FeaturePrerequisiteError`: A supported feature depends on
  another that isn't supported.
* :exc:`MultipleImplementedRevisions`: YANG library specifies multiple
  revisions of an implemented module.
* :exc:`CyclicImports`: Imports of YANG modules form a cycle.

.. class:: Context

   This class serves as a global repository of the data model schema and
   several other important data structures that are stored as class
   attributes. This means that

   * it is possible to work with only one data model at a time,

   * no instances of this class are expected to be created.

   The :class:`Context` class also provides a number of class methods
   for retrieving and transforming this global data.

   Other Python modules that need the data model information and/or
   methods should import the :class:`Context` class.

   .. doctest::

      >>> from yangson import DataModel
      >>> from yangson.context import Context
      >>> dm = DataModel.from_file("yang-library-ex3.json")

   .. attribute:: features

      Set of supported features.

      Each entry is the :term:`qualified name` of a feature that is
      declared as supported in YANG library data.

      .. doctest::

	 >>> fs = Context.features
	 >>> ('fea1', 'a') in fs
	 True
	 >>> ('fea2', 'a') in fs
	 True

   .. attribute:: module_search_path

      List of directories where to look for YANG modules.

      All YANG modules and submodules listed in YANG library data have
      to be located in one of these directories.

      .. doctest::

	 >>> Context.module_search_path
	 ['.']

   .. attribute:: modules

      Dictionary of modules and submodules comprising the data model.

      The keys are :term:`module identifier`\ s, and the values are
      corresponding **module** or **submodule** statements (see
      :class:`Statement`).

      .. doctest::

	 >>> len(Context.modules)
	 3

   .. attribute:: implement

      List of modules with conformance type “implement”.

   .. attribute:: revisions

      Dictionary of module and submodule revisions.

      The keys are module and submodule names, and each value is a list of
      revisions that are used in the data model.
      For an :term:`implemented module`, this list must be a
      singleton, whereas :term:`imported-only module`\ s may be present
      in multiple revisions.

   .. attribute:: prefix_map

      Dictionary of prefix mappings.

      The keys are :term:`module identifier`\ s, and each value
      contains a mapping of prefixes for the module. The keys of this
      mapping are prefixes, and the values are :term:`module
      identifier`\ s.
      
   .. attribute:: ns_map

      Dictionary of module and submodule namespaces.

      The keys are module and submodule names, and the values are
      :term:`namespace identifier`\ s.

   .. attribute:: identity_bases

      Dictionary of identity bases.

      The keys are :term:`qualified name`\ s of identities, and each
      value is a list of :term:`qualified name`\ s of identities that
      are defined as bases for the key identity.
