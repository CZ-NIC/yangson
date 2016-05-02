==================
Data Model Context
==================

.. module:: yangson.context
   :synopsis: Global repository of data model information and methods.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

The *Yangson* library requires two pieces of information in order to
be able to construct the data model:

* *YANG library* data [BBW16]_ with a list of YANG modules that
  comprise the data model, and a few other details;

* list of filesystem directories from which the YANG modules can be
  retrieved.

*Yangson* reads the YANG library data and processes all the
 modules. This results in the data model schema plus a number of other
 data structures that are needed in other Python modules. To make them
 globally available, *Yangson* stores these data structures in the
 :class:`Context` class.

.. class:: Context

   This class stores several important data model structures as class
   attributes, and also provides a number of generally useful class
   methods. No instances of this class are expected to be created.

   .. attribute:: module_search_path

      A list of directories in which Yangson looks for YANG modules.

   .. attribute:: modules

      A dictionary mapping :term:`module identifier`\ s to the
      corresponding **module** or **submodule** statements.

   .. attribute:: implement

      A list of names of :term:`implemented module`\ s. Note that the
      revisions aren't specified because the data model cannot contain
      more than one revision of each implemented module.

   .. attribute:: revisions

      A dictionary mapping module names to the list of module
      revisions that are used in the data model.

   .. attribute:: prefix_map

      A dictionary that provides, for each YANG module or submodule
      that is included in the data model, the translation of prefixes
      to :term:`module identifier`\ s. The keys of the
      :attr:`prefix_map` dictionary are :term:`module identifier`\ s,
      and values are dictionaries with prefixes as keys and
      :term:`module identifier`\ s as values.

   .. attribute:: ns_map

      A dictionary mapping module and submodule names to the
      corresponding :term:`namespace identifier`\ s.

   .. attribute:: derived_identities

      A dictionary mapping :term:`qualified name`\ s of identities to
      the set of :term:`qualified name`\ s of directly derived
      identities.

   .. attribute:: features

      A set of qualified names of features that the data model
      supports.

   .. automethod:: from_yang_library

      This class method bootstraps the data model. The `yang_lib`
      dictionary is supposed to be parsed from JSON-encoded YANG
      library data (see the factory method of the
      :class:`~yangson.datamodel.DataModel` class.

   .. automethod:: resolve_pname

   .. automethod:: translate_pname

   .. automethod:: sid2route

   .. automethod:: path2route

   .. automethod:: get_definition

   .. automethod:: if_features

   .. automethod:: feature_test

   .. automethod:: feature_expr
