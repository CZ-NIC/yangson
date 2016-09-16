=================
Data Model Schema
=================

.. module:: yangson.schema
   :synopsis: Classes representing YANG schema nodes

.. testsetup::

   import json
   import os
   from yangson import DataModel
   os.chdir("examples/ex4")

.. testcleanup::

   os.chdir("../..")
   del DataModel._instances[DataModel]

The *schema* module defines the following classes:

* :class:`SchemaNode`: Abstract class for schema nodes.
* :class:`InternalNode`: Abstract class for schema nodes that have children.
* :class:`GroupNode`: Anonymous group of schema nodes.
* :class:`DataNode`: Abstract class for data nodes.
* :class:`TerminalNode`: Abstract class for schema nodes that have no children.
* :class:`ContainerNode`: YANG **container** node.
* :class:`SequenceNode`: Abstract class for schema nodes that represent a sequence.
* :class:`ListNode`: YANG **list** node.
* :class:`ChoiceNode`: YANG **choice** node.
* :class:`CaseNode`: YANG **case** node.
* :class:`RpcActionNode`: YANG **rpc** or **action** node.
* :class:`InputNode`: YANG **input** node.
* :class:`OutputNode`: YANG **output** node.
* :class:`NotificationNode`: YANG **notification** node.
* :class:`LeafNode`: YANG **leaf** node.
* :class:`LeafListNode`: YANG **leaf-list** node.
* :class:`AnydataNode`: YANG **anydata** or **anyxml** node.

This module also defines the following exceptions:

* :exc:`SchemaNodeException`: Abstract exception class for schema node errors.
* :exc:`NonexistentSchemaNode`: A schema node doesn't exist.
* :exc:`BadSchemaNodType`: A schema node is of a wrong type.
* :exc:`BadLeafrefPath`: A leafref path is incorrect.
* :exc:`ValidationError`: Abstract exeption class for instance validation errors.
* :exc:`SchemaError`: An instance violates a schema constraint, see :term:`schema error`.
* :exc:`SemanticError`: An instance violates a semantic rule, see :term:`semantic error`.


.. class:: SchemaNode

   This class serves as the top-level abstract superclass for all
   schema node classes.

   .. doctest::

      >>> dm = DataModel.from_file('yang-library-ex4.json')
      >>> fsn = dm.get_schema_node("/example-4-a:bag/foo")
      >>> type(fsn)
      <class 'yangson.schema.LeafNode'>
      >>> rsn = dm.get_schema_node("/example-4-a:bag/opts/example-4-b:fooref/fooref")

   .. rubric:: Instance Attributes

   .. attribute:: name

      Name of the schema node.

      .. doctest::

	 >>> fsn.name
	 'foo'

   .. attribute:: ns

      Namespace of the schema node, which is the name of the YANG
      module in which the node is defined.

      .. doctest::

	 >>> fsn.ns
	 'example-4-a'

   .. attribute:: parent

      Parent schema node, if there is any.

      .. doctest::

	 >>> type(rsn.parent)
	 <class 'yangson.schema.CaseNode'>
	 >>> rsn.parent.name
	 'fooref'
	 >>> rsn.parent.ns
	 'example-4-b'

   .. attribute:: must

      List of **must** expressions that are attached to the schema
      node. Each entry is a tuple consisting of an instance of the
      :class:`~.xpathast.Expr` class and the corresponding error
      message (or ``None`` if no error message is defined for the
      **must** expression). See sec. `7.5.3`_ in [RFC7950]_.

   .. attribute:: when

      Optional **when** expression that makes the schema node
      conditional. The value is an instance of the
      :class:`~.xpathast.Expr` class or ``None`` if no **when**
      expression is defined for the schema node. See sec. `7.21.5`_ in
      [RFC7950]_.

   .. rubric:: Properties

   .. attribute:: qual_name

      :term:`Qualified name` of the schema node.

      .. doctest::

	 >>> fsn.qual_name
	 ('foo', 'example-4-a')

   .. attribute:: config

      This boolean property is ``True`` if the receiver represents
      configuration, and ``False`` otherwise.

      .. doctest::

	 >>> rsn.config
	 True

   .. attribute:: mandatory

      This boolean property is ``True`` if the receiver is a mandatory
      node, and ``False`` otherwise.

      .. doctest::

	 >>> rsn.mandatory
	 False

   .. rubric:: Public Methods

   .. method:: data_parent() -> Optional[InternalNode]

      Return the closest ancestor schema node that is also a data
      node, or ``None`` if there is no such schema node.

      .. doctest::

	 >>> bsn = rsn.data_parent()
	 >>> bsn.qual_name
	 ('bag', 'example-4-a')

   .. method:: iname() -> InstanceName

      Return :term:`instance name` corresponding to the receiver.

   .. method:: data_path() -> DataPath

      Return the receiver's :term:`data path`.

   .. method:: follow_leafref(xpath: Expr) -> Optional[DataNode]

      Return the data node referred to by a **leafref** path. The
      argument *xpath* is an instance of :class:`.xpathast.Expr` that
      was compiled from a **leafref** path. Return ``None`` if the
      data node being referred to doesn't exist.

   .. method:: state_roots() -> List[DataPath]

      Return a list of :term:`data path`\ s of the roots of all state
      data subtrees that are descendant to the receiver. If the
      receiver itself is a state data node, then the returned list
      contains only its data path. An empty list is returned if the
      receiver has no descendant state data nodes.

   .. method:: default_value() -> Optional[Value]

      Return an instance value representing the default content as
      defined for the receiver's subtree in the schema. ``None`` is
      returned if there is no default content.

   .. method:: validate(inst: InstanceNode, content: ContentType) -> None

      Validate an :class:`~.instance.InstanceNode` *inst* against the
      receiver. The *content* argument specifies the content type of
      the value of *inst*. Permitted values are defined by the
      :data:`~.enumerations.ContentType` enumeration, currently
      supported are ``ContentType.config`` (configuration) and
      ``ContentType.all`` (both configuration and state data).

      ``None`` is returned if the instance is valid. If a
      :term:`schema error` or :term:`semantic error` is detected, then
      :exc:`SchemaError` or :exc:`SemanticError` is raised,
      respectively.

   .. method:: from_raw(rval: RawValue) -> Value

      Return a :term:`cooked value` transformed from :term:`raw value`
      *rval* as dictated by the receiver and its subtree in the
      schema.

      This method raises :exc:`NonexistentSchemaNode` if *rval*
      contains a member that is not defined in the schema, and
      :exc:`~.datatype.YangTypeError` if a scalar value inside *rval*
      is of incorrect type.

.. class:: InternalNode

   This is an abstract superclass for schema nodes that can have
   children in the schema tree. It is a subclass of :class:`SchemaNode`.

   .. rubric:: Instance Attributes

   .. attribute:: children

      The list of the schema node's children.

   .. attribute:: default_children

      The list of the children that may be added as default content to
      the receiver's instance.

   .. rubric:: Public Methods

   .. method:: get_child(name: YangIdentifier, ns: YangIdentifier = \
	       None) -> Optional[SchemaNode]

      Return receiver's child schema node whose name is *name* and
      namespace *ns*. If the *ns* argument is ``None`` (default), then
      the receiver's namespace is used. ``None`` is returned if the
      child isn't found.

   .. method:: add_child(node: SchemaNode) -> None

      Add *node* as a new child of the receiver.

   .. method:: get_schema_descendant(route: SchemaRoute) -> Optional[SchemaNode]

      Return the descendant schema node identified by the
      :term:`schema route` *route*, which is interpreted relative to
      the receiver. ``None`` is returned if the node is not found.

   .. method:: get_data_child(name: YangIdentifier, ns: YangIdentifier
	       = None) -> Optional[DataNode]

      Return receiver's data child whose name is *name* and namespace
      *ns*. If the *ns* argument is ``None`` (default), then the receiver's
      namespace is used. ``None`` is returned if the data child is not
      found.

      Unlike :meth:`getchild`, this method finds the data node
      identified by *name* and *ns* also if it is separated from the
      receiver only by non-data nodes (i.e. **choice** and **case**
      nodes).

.. class:: GroupNode

This class is a subclass of :class:`InternalNode`. Its instances are
used as anonymous groups of schema nodes contained in an **augment**
or **uses** statement if this statement is conditional, i.e. has a
**when** substatement.

.. class:: DataNode

   This is an abstract superclass for all data nodes. It is a subclass
   of :class:`SchemaNode`.

   .. rubric:: Instance Attributes

   .. attribute:: default_deny

      Default deny attribute as defined by the NETCONF Access Control
      Model [RFC6536]_ and set using YANG extension statements
      ``nacm:default-deny-write`` or
      ``nacm:default-deny-all``. Permitted values are defined by the
      :data:`~.enumerations.DefaultDeny` enumeration, the default is
      ``DefaultDeny.none``.

.. class:: TerminalNode

   This is the abstract superclass for terminal nodes, i.e. schema
   nodes that have no children. It is a subclass of
   :class:`SchemaNode`.

   .. rubric:: Instance Attributes

   .. attribute:: type

      A :class:`~.datatype.DataType` object specifying the type of the
      instance.

   .. attribute:: default

      Default value defined for the instance.

.. class:: ContainerNode

   This class is a subclass of :class:`InternalNode` and
   :class:`DataNode`. Its instances represent YANG **container**
   nodes.

   .. rubric:: Instance Attributes

   .. attribute:: presence

      A boolean value specifying whether the instance is a container
      with presence.

.. class:: SequenceNode

   Abstract superclass for data nodes representing a sequence,
   i.e. **list** and **leaf-list**. It is a subclass of
   :class:`DataNode`.

   .. rubric:: Instance Attributes

   .. attribute:: min_elements

      An integer value specifying the minimum number of list or
      leaf-list entries set by the **min-elements** statement. The
      default is 0.

   .. attribute:: max_elements

      An integer value specifying the maximum number of list or
      leaf-list entries set by the **max-elements** statement. The
      default value is ``None``, which means that no maximum is
      specified.

   .. attribute:: user_ordered

      A boolean value specifying whether the list or leaf-list entries
      are ordered by user. This attribute is set by the **ordered-by**
      statement. The value of ``False`` (default) means that the
      (leaf-)list is ordered by system, i.e. the server may rearrange
      the entries.

   .. rubric:: Public Methods

   .. method:: entry_from_raw(rval: RawEntry) -> EntryValue

      Return a :term:`cooked value` of an array entry transformed from
      :term:`raw value` *rval* as dictated by the receiver and its
      subtree in the schema.

      This method raises :exc:`NonexistentSchemaNode` if *rval*
      contains a member that is not defined in the schema, and
      :exc:`~.datatype.YangTypeError` if a scalar value inside *rval*
      is of incorrect type.

.. class:: ListNode

   This class is a subclass of :class:`SequenceNode` and
   :class:`InternalNode`. Its instances represent YANG **list**
   nodes.

   .. rubric:: Instance Attributes

   .. attribute:: keys

      List containing :term:`qualified name`\ s of all keys defined by
      the **key** statement.

   .. attribute:: unique

      List of lists of schema routes. Each internal list represents a
      group of descendant leafs whose values are required to be unique
      across all list entries. See **unique** statement in [RFC7950]_,
      sec. `7.8.3`_.

.. class:: ChoiceNode(InternalNode)

   This class is a subclass of :class:`InternalNode`. Its instances
   represent YANG **choice** nodes.

   .. rubric:: Instance Attributes

   .. attribute:: default_case

      :term:`Qualified name` specifying the default case defined by
      the **default** substatement of **choice**. The value of
      ``None`` (default) means that no case is defined as default.

   .. rubric:: Public Methods

   .. method:: active_case(value: ObjectValue) -> Optional[CaseNode]

      Return the receiver's case that is active in *value*, or
      ``None`` if there is no such case. Active is the case whose
      descendant data nodes have instance(s) in *value*.

.. class:: CaseNode

   This class is a subclass of :class:`InternalNode`. Its instances
   represent YANG **case** nodes.

   A :class:`CaseNode` is present in the internal schema tree even if
   it is defined as a “shorthand” case in a YANG module (see
   sec. `7.9.2`_ of [RFC7950]_).

.. class:: LeafNode

   This class is a subclass of :class:`TerminalNode` and
   :class:`DataNode`. Its instances represent YANG **leaf** nodes.

.. class:: LeafListNode

   This class is a subclass of :class:`SequenceNode` and
   :class:`TerminalNode`. Its instances represent YANG **leaf-list**
   nodes.

.. class:: AnydataNode

   This class is a subclass of :class:`DataNode`. Its instances
   represent YANG **anydata** and **anyxml** nodes.

.. class:: RpcActionNode

   This class is a subclass of :class:`GroupNode`. Its instances
   represent YANG **rpc** and **action** nodes.

.. class:: InputNode

   This class is a subclass of :class:`GroupNode`. Its instances
   represent YANG **input** nodes containing input parameters of an
   **rpc** or **action**.

.. class:: OutputNode

   This class is a subclass of :class:`GroupNode`. Its instances
   represent YANG **output** nodes containing output parameters of an
   **rpc** or **action**.

.. class:: NotificationNode

   This class is a subclass of :class:`GroupNode`. Its instances
   represent YANG **notification** nodes.

.. autoexception:: SchemaNodeException(sn: SchemaNode)
   :show-inheritance:

   The schema node for which the exception occurred is passed in the
   *sn* argument.

.. autoexception:: NonexistentSchemaNode(sn: SchemaNode, name: \
		   YangIdentifier, ns: YangIdentifier)
   :show-inheritance:

   The arguments *name* and *ns* give the name and namespace of the
   non-existent schema node.

.. autoexception:: BadSchemaNodeType(sn: SchemaNode, expected: str)
   :show-inheritance:

   The argument *expected* describes what type was expected.

.. autoexception:: BadLeafrefPath(sn: SchemaNode)
   :show-inheritance:

.. autoexception:: ValidationError(inst: InstanceNode, detail: str)
   :show-inheritance:

   The *inst* argument contains the instance node that was found
   invalid, and *detail* provides additional information about the
   error.

.. autoexception:: SchemaError
   :show-inheritance:

   See :term:`schema error`.

.. autoexception:: SemanticError
   :show-inheritance:

   See :term:`semantic error`.

.. _7.5.3: https://tools.ietf.org/html/rfc7950#section-7.5.3
.. _7.8.3: https://tools.ietf.org/html/rfc7950#section-7.8.3
.. _7.9.2: https://tools.ietf.org/html/rfc7950#section-7.9.2
.. _7.21.5: https://tools.ietf.org/html/rfc7950#section-7.21.5
