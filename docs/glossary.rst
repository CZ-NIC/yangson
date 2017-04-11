.. _glossary:

********
Glossary
********

Many important terms are also defined in the YANG
specification, see section `3`_ of [RFC7950]_.

.. glossary::
   :sorted:

   raw value

      A value of an instance that is produced by the Python parser
      from serialised JSON data. Based on its type and data model
      information, a raw value is transformed to a :term:`cooked
      value`.

   cooked value

      An instance value that is in the internal form prescribed for
      that instance. That is, scalar values are represented according
      to their types, while objects and arrays become instances of of
      :class:`.instvalue.ObjectValue` and
      :class:`.instvalue.ArrayValue`, respectively.

   canonical representation

      A normalized string value that [RFC7950]_ defines for most
      scalar types.

   content type

      Character of a schema node, i.e. whether it represents
      configuration, non-configuration, or both. Represented by the
      enumeration :data:`~.enumerations.ContentType`.

   qualified name

       A tuple in the form *(name, module)* where *name* is the name
       of a YANG entity (schema or data node, feature, identity etc.),
       and *module* is the name of the YANG module in which the entity
       is defined. Python type alias for the qualified name is
       :const:`QualName`.

   schema route

       A list of :term:`qualified name`\ s of schema nodes interpreted
       relative to a given reference schema node and uniquely
       identifies its descendant schema node. Python type alias for
       the schema route is :const:`SchemaRoute`.

   data route

       A list of :term:`qualified name`\ s of data nodes interpreted
       relative to a given reference schema node. As a :term:`schema
       route`, a data route also identifes a unique descendant schema
       node because names of data nodes belonging to the cases of the
       same choice are required to be unique, see sec. `6.2.1`_ in
       [RFC7950]_.

   prefixed name

       A string in the form [*prefix*\ :]\ *name* where *name* is the
       name of a YANG entity (schema node, feature, identity etc.),
       and *prefix* is the namespace prefix declared for the module in
       which the entity is defined. Python type alias for the prefixed
       name is :const:`PrefName`.

   YANG identifier

       A string satisfying the rules for a YANG identifier (see
       sec. `6.2`_ in [RFC7950]_): it starts with an uppercase or
       lowercase ASCII letter or an underscore character (``_``),
       followed by zero or more ASCII letters, digits, underscore
       characters, hyphens, and dots. Python type alias for the YANG
       identifier is :const:`YangIdentifier`.

   module identifier

       A tuple in the form *(module_name, revision)* that identifies a
       particular revision of a module. The second component,
       *revision*, is either a revision date (string in the form
       ``YYYY-MM-DD``) or ``None``. In the latter case the revision is
       unspecified.

   schema path

       A string of slash-separated schema node names in the form
       [*module_name*\ ``:``]\ *schema_node_name*. The initial
       component must always be qualified with a module name. Any
       subsequent component is qualified with a module name if and
       only if its namespace is different from the previous
       component. A schema path is always absolute, i.e. starts at the
       top of the schema. A leading slash is optional. Python type
       alias for the schema path is :const:`SchemaPath`.

   data path

       A special form of :term:`schema path` containing only names of
       *data nodes*. The relationship of data path and schema path is
       analogical to how :term:`data route` is related to
       :term:`schema route`.

   node identifier

      Name of a single schema node with optional namespace prefix. See
      production ``node-identifier`` in [RFC7950]_, sec. `14`_.

   schema node identifier

       A sequence of :term:`prefixed name`\ s of schema nodes
       separated with slashes. A schema node identifier that starts
       with a slash is absolute, otherwise it is relative. See
       [RFC7950]_, sec. `6.5`_.

   instance name

       A string in the form [*module_name*\ ``:``]\ *name* where
       *name* is a name of a data node. Instance names identify nodes
       in the data tree, and are used both as :class:`ObjectValue`
       keys and member names in JSON serialization. See [RFC7951]_,
       sec. `4`_ for details. Python type alias for the instance name
       is :const:`InstanceName`.

   instance identifier

       A string that identifies a unique instance in the data
       tree. The syntax of instance identifiers is defined in
       [RFC7950]_, sec. `9.13`_, and [RFC7951]_, sec. `6.11`_.

   resource identifier

       A string identifying an instance in the data tree that is
       suitable for use in URLs. The syntax of resource identifiers is
       defined in [RFC8040]_, sec. `3.5.3`_.

   implemented module

       A YANG module that contributes data nodes to the data model. In
       YANG library, implemented modules have the *conformance-type*
       parameter set to ``implement``. See [RFC7895]_, sec. `2.2`_.

   imported-only module

       A YANG module whose data nodes aren't contributed to the data
       model. Other modules import such a module in order to use its
       typedefs and/or groupings. In YANG library, implemented modules
       have the *conformance-type* parameter set to ``import``. See
       [RFC7895]_, sec. `2.2`_.

   namespace identifier

       A string identifying the namespace of names defined in a YANG
       module or submodule. For main modules, the namespace identifier
       is identical to the module name whereas for submodules it is
       the name of the main module to which the submodule belongs.

   schema error

      The value of instance node violates a schema constraint, i.e.
      one of the following: grammar defined by the hierarchy of schema
      nodes (also taking into account conditions specified by **when**
      and **if-feature** statements), type of the value, presence and
      uniqueness of list keys.

   semantic error

      The value of an instance node violates a semantic rule, i.e. one
      of the following: **must** expression, referential integrity
      constraint (for **leaf** nodes with *leafref* or
      *instance-identifier* type), number of list entries prescribed
      by **min-elements** and **max-elements** statements, **unique**
      constraint specified for a **list** node, non-unique values of a
      **leaf-list** node that represents configuration.

.. _2.2: https://tools.ietf.org/html/rfc7895#section-2.2
.. _3: https://tools.ietf.org/html/rfc7950#section-3
.. _3.5.3: https://tools.ietf.org/html/rfc8040#section-3.5.3
.. _4: https://tools.ietf.org/html/rfc7951#section-4
.. _6.2: https://tools.ietf.org/html/rfc7950#section-6.2
.. _6.2.1: https://tools.ietf.org/html/rfc7950#section-6.2.1
.. _6.11: https://tools.ietf.org/html/rfc7951#section-6.11
.. _6.5: https://tools.ietf.org/html/rfc7950#section-6.5
.. _9.13: https://tools.ietf.org/html/rfc7950#section-9.13
.. _14: https://tools.ietf.org/html/rfc7950#section-14
