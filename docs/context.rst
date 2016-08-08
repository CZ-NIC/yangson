==================
Data Model Context
==================

.. module:: yangson.context
   :synopsis: Global repository of data model information and methods.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

The *Yangson* library requires two pieces of information in order to
be able to construct the data model:

* *YANG library* data [RFC7895]_ with a list of YANG modules and
  submodules that comprise the data model, supported features, and a
  few other details;

* list of filesystem directories from which the YANG modules can be
  retrieved.

*Yangson* reads the YANG library data and tries to locate all modules
and submodules specified in YANG library data. Names of files in which
(sub)modules are stored must be of the form specified in [Bjo16]_,
sec. `5.2`__::

    module-or-submodule-name ['@' revision-date] '.yang'

*Yangson* is currently able to parse only the compact format of YANG
files. The alternative XML format (YIN) may be supported in a future
version.

__ https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis-14#section-5.2

If a revision date is specified for a (sub)module in YANG library
data, then it must also appear in the file name. 

All modules and submodules are then processed into the data model
schema plus a number of other data structures that are needed in other
Python modules. To make them globally available, *Yangson* stores
these data structures in the :class:`Context` class.

.. class:: Context

   This class serves as a global storage of the data model schema and
   several other important data model structures as class attributes.
   This means that it is possible to work with only one data model at
   a time.
   
   The :class:`Context` also provides a number of class methods for
   retrieving and using this global data. 

   No instances of this class are expected to be created.

   .. attribute:: module_search_path

      List of directories where to look for YANG modules.

      All YANG modules and submodules listed in YANG library
      data [RFC7895]_ have to be located in one of these
      directories. Names of

   .. attribute:: modules

      Dictionary of modules and submodules comprising the data model.

      The keys are :term:`module identifier`\ s, and the values are
      corresponding **module** or **submodule** statements (see
      :class:`Statement`).

   .. attribute:: implement

      List of modules with conformance type “implement”.

      The revisions aren't specified because the data model cannot contain
      more than one revision of each implemented module.

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

   .. attribute:: features

      Set of supported features.

      Each entry is the :term:`qualified name` of a feature that is
      declared as supported in YANG library data.

   .. automethod:: from_yang_library

      This class method bootstraps the data model. The `yang_lib`
      dictionary is supposed to be parsed from JSON-encoded YANG
      library data (see the factory method of the
      :class:`~yangson.datamodel.DataModel` class.

   .. automethod:: module_set_id

   .. automethod:: resolve_pname

   .. automethod:: translate_pname

   .. automethod:: sid2route

   .. automethod:: path2route

   .. automethod:: get_definition

   .. automethod:: if_features

   .. automethod:: feature_test

   .. automethod:: feature_expr
