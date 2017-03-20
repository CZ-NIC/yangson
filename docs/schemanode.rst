************
Schema Nodes
************


.. module:: yangson.schemanode
   :synopsis: Classes representing YANG schema nodes

.. testsetup::

   import json
   import os
   from yangson import DataModel
   from yangson.enumerations import ContentType
   os.chdir("examples/ex4")

.. testcleanup::

   os.chdir("../..")

The *schemanode* module implements the following classes:

* :class:`SchemaNode`: Abstract class for schema nodes.
* :class:`InternalNode`: Abstract class for schema nodes that have children.
* :class:`GroupNode`: Anonymous group of schema nodes.
* :class:`SchemaTreeNode`: Root node of a schema tree.
* :class:`DataNode`: Abstract class for data nodes.
* :class:`TerminalNode`: Abstract class for schema nodes that have no children.
* :class:`ContainerNode`: YANG **container** node.
* :class:`SequenceNode`: Abstract class for schema nodes that
  represent a sequence.
* :class:`ListNode`: YANG **list** node.
* :class:`ChoiceNode`: YANG **choice** node.
* :class:`CaseNode`: YANG **case** node.
* :class:`RpcActionNode`: YANG **rpc** or **action** node.
* :class:`InputNode`: YANG **input** node.
* :class:`OutputNode`: YANG **output** node.
* :class:`NotificationNode`: YANG **notification** node.
* :class:`LeafNode`: YANG **leaf** node.
* :class:`LeafListNode`: YANG **leaf-list** node.
* :class:`AnyContentNode`: Abstract superclass for YANG **anydata**
  or **anyxml** nodes.
* :class:`AnydataNode`: YANG **anydata** or **anyxml** node.
* :class:`AnydataNode`: YANG **anydata** or **anyxml** node.

Doctest__ snippets for this module use the data model and instance
document from :ref:`sec-ex4`.

__ http://www.sphinx-doc.org/en/stable/ext/doctest.html

.. doctest::

   >>> dm = DataModel.from_file('yang-library-ex4.json',
   ... mod_path=['.', '../../../yang-modules/ietf'])
   >>> fsn = dm.get_schema_node('/example-4-a:bag/foo')
   >>> rsn = dm.get_schema_node('/example-4-a:bag/opts/example-4-b:fooref/fooref')
   >>> with open('example-data.json') as infile:
   ...     ri = json.load(infile)
   >>> inst = dm.from_raw(ri)

.. class:: SchemaNode

   This class serves as the top-level abstract superclass for all
   schema node classes.

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
	 <class 'yangson.schemanode.CaseNode'>
	 >>> rsn.parent.name
	 'fooref'
	 >>> rsn.parent.ns
	 'example-4-b'

   .. attribute:: description

      Description string for the schema node, or ``None`` if the
      schema node's definition contains no description.

      .. doctest::

	 >>> dm.get_data_node('/example-4-a:bag').description
	 'Top-level container.'
	 >>> rsn.description is None
	 True

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

	 >>> fsn.config
	 True

   .. attribute:: mandatory

      This boolean property is ``True`` if the receiver is a mandatory
      node, and ``False`` otherwise.

      .. doctest::

	 >>> rsn.mandatory
	 False

   .. rubric:: Public Methods

   .. automethod:: schema_root() -> GroupNode

      .. doctest::

	 >>> rsn.schema_root().parent is None
	 True

   .. automethod:: content_type() -> ContentType

      .. doctest::

	 >>> rsn.content_type().name
	 'config'

   .. method:: data_parent() -> Optional[InternalNode]

      Return the closest ancestor schema node that is also a data
      node, or ``None`` if there is no such schema node.

      .. doctest::

	 >>> bsn = rsn.data_parent()
	 >>> bsn.qual_name
	 ('bag', 'example-4-a')

   .. method:: iname() -> InstanceName

      Return :term:`instance name` corresponding to the receiver.

      .. doctest::

	 >>> bsn.iname()
	 'example-4-a:bag'
	 >>> fsn.iname()
	 'foo'

   .. method:: data_path() -> DataPath

      Return the receiver's :term:`data path`.

      .. doctest::

	 >>> fsn.data_path()
	 '/example-4-a:bag/foo'
	 >>> rsn.data_path()
	 '/example-4-a:bag/example-4-b:fooref'

   .. method:: state_roots() -> List[DataPath]

      Return a list of :term:`data path`\ s of the roots of all state
      data subtrees that are descendant to the receiver. If the
      receiver itself is a state data node, then the returned list
      contains only its data path. An empty list is returned if the
      receiver has no descendant state data nodes.

      .. doctest::

	 >>> bsn.state_roots()
	 ['/example-4-a:bag/bar']

   .. method:: from_raw(rval: RawValue, jptr: JSONPointer = "") -> Value

      Return a :term:`cooked value` transformed from :term:`raw value`
      *rval* as dictated by the receiver and its subtree in the
      schema. The *jptr* argument gives the JSON Pointer [RFC6901]_ of
      the instance node for the cooked value is intended (if known,
      otherwise the second argument needn't be present).

      This method raises :exc:`~.NonexistentSchemaNode` if *rval*
      contains a member that is not defined in the schema, and
      :exc:`~.YangTypeError` if a scalar value inside *rval*
      is of incorrect type.

      .. doctest::

	 >>> raw = {'baz': [None]}
	 >>> type(raw)
	 <class 'dict'>
	 >>> cooked = bsn.from_raw(raw, '/example-4-a:bag')
	 >>> cooked
	 {'baz': (None,)}
	 >>> type(cooked)
	 <class 'yangson.instvalue.ObjectValue'>

.. class:: InternalNode

   This is an abstract superclass for schema nodes that can have
   children in the schema tree. It is a subclass of :class:`SchemaNode`.

   .. rubric:: Instance Attributes

   .. attribute:: children

      The list of the schema node's children.

      .. doctest::

	 >>> [c.name for c in bsn.children]
	 ['foo', 'bar', 'opts']

   .. rubric:: Public Methods

   .. method:: get_child(name: YangIdentifier, ns: YangIdentifier = \
	       None) -> Optional[SchemaNode]

      Return receiver's child schema node whose name is *name* and
      namespace *ns*. If the *ns* argument is ``None`` (default), then
      the receiver's namespace is used. ``None`` is returned if the
      child isn't found.

      .. doctest::

	 >>> barsn = bsn.get_child('bar', 'example-4-a')
	 >>> barsn.qual_name
	 ('bar', 'example-4-a')

   .. method:: get_schema_descendant(route: SchemaRoute) -> Optional[SchemaNode]

      Return the descendant schema node identified by the
      :term:`schema route` *route*, which is interpreted relative to
      the receiver. ``None`` is returned if the node is not found.

      .. doctest::

	 >>> bazsn = bsn.get_schema_descendant(
	 ... [('opts','example-4-a'), ('a','example-4-a'), ('baz','example-4-a')])
	 >>> bazsn.qual_name
	 ('baz', 'example-4-a')


   .. method:: get_data_child(name: YangIdentifier, ns: YangIdentifier \
	       = None) -> Optional[DataNode]

      Return receiver's data child whose name is *name* and namespace
      *ns*. If the *ns* argument is ``None`` (default), then the receiver's
      namespace is used. ``None`` is returned if the data child is not
      found.

      Unlike :meth:`get_child`, this method finds the data node
      identified by *name* and *ns* also if it is separated from the
      receiver only by non-data nodes (i.e. **choice** and **case**
      nodes), as it is the case in the following example:

      .. doctest::

	 >>> bsn.get_data_child('baz', 'example-4-a').qual_name
	 ('baz', 'example-4-a')

   .. method:: filter_children(ctype: ContentType = None) -> List[SchemaNode]

      Return the list of receiver's children that are of the :term:`content
      type` specified by the argument *ctype*. If the argument is
      ``None``, then the returned list contains children of the same
      content type as the receiver. Children that are instances of
      either :class:`RpcActionNode` or :class:`NotificationNode` are
      always omitted.

      .. doctest::

	 >>> [c.name for c in bsn.filter_children(ContentType.config)]
	 ['foo', 'opts']
	 >>> [c.name for c in bsn.filter_children(ContentType.nonconfig)]
	 ['bar', 'opts']

   .. method:: data_children() -> List[DataNode]

      Return the list of receiver's data children, i.e. descendant
      data nodes that are either direct children of the receiver, or
      that have no ancestor data nodes that are also descendants of
      the receiver. Child nodes that are instances of
      :class:`SchemaTreeNode` (i.e. rpc, action, input, output or
      notification node) are not included. See also
      :meth:`get_data_child`.

      .. doctest::

	 >>> [c.name for c in bsn.data_children()]
	 ['foo', 'bar', 'baz', 'fooref']

.. class:: GroupNode

This class is a subclass of :class:`InternalNode`. Its instances are
used as anonymous groups of schema nodes contained in an **augment**
or **uses** statement if this statement is conditional, i.e. has a
**when** substatement.

.. class:: SchemaTreeNode

This class is a subclass of :class:`GroupNode`. Each instance
represents the root node of a schema tree (main tree, RPC operation or
action, input or output node, or notification).

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

      .. doctest::

	 >>> fsn.default_deny
	 <DefaultDeny.write: 2>

   .. rubric:: Public Methods

   .. method:: orphan_instance(rval: RawValue) -> ObjectMember

      Return an :class:`~.instance.ObjectMember` as an isolated
      instance of the receiver data node, i.e. one that has neither
      parent instance nor siblings. The *rval* argument provides the
      :term:`raw value` to be cooked and used for the instance.

      .. doctest::

	 >>> obag = bsn.orphan_instance({'foo': 54, 'bar': True})
	 >>> obag.name
	 'example-4-a:bag'
	 >>> obag['foo'].value
	 54
	 >>> obag.parinst is None
	 True
	 >>> obag.siblings
	 {}

   .. method:: split_instance_route(route: InstanceRoute) -> \
	       Optional[Tuple[InstanceRoute, InstanceRoute]]

      Split *route* into two :class:`~.instance.InstanceRoute`\ s. The
      first item of the returned tuple is the part up to the receiver,
      and the second item is the rest.

      .. doctest::

	 >>> irt = dm.parse_resource_id('/example-4-a:bag/foo')
	 >>> pre, post = bsn.split_instance_route(irt)
	 >>> str(pre)
	 '/example-4-a:bag'
	 >>> str(post)
	 '/foo'

.. class:: TerminalNode

   This is the abstract superclass for terminal nodes, i.e. schema
   nodes that have no children. It is a subclass of
   :class:`SchemaNode`.

   .. rubric:: Instance Attributes

   .. attribute:: type

      A :class:`~.datatype.DataType` object specifying the type of the
      instance.

      .. doctest::

	 >>> type(rsn.type)
	 <class 'yangson.datatype.LeafrefType'>

   .. rubric:: Properties

   .. attribute:: default

      Default value of the receiver or ``None`` if no default is
      applicable. Note that the default may also come from receiver's
      type.

      .. doctest::

	 >>> barsn.default
	 True

.. class:: ContainerNode

   This class is a subclass of :class:`DataNode` and
   :class:`InternalNode`. Its instances represent YANG **container**
   nodes.

   The `method resolution order`_ for this class is as follows:

   :class:`ContainerNode` ► :class:`DataNode` ► :class:`InternalNode` ►
   :class:`SchemaNode`

   .. rubric:: Instance Attributes

   .. attribute:: presence

      A boolean value specifying whether the instance is a container
      with presence.

      .. doctest::

	 >>> bsn.presence
	 True

.. class:: SequenceNode

   Abstract superclass for data nodes representing a sequence,
   i.e. **list** and **leaf-list**. It is a subclass of
   :class:`DataNode`.

   .. rubric:: Instance Attributes

   .. attribute:: min_elements

      An integer value specifying the minimum number of list or
      leaf-list entries set by the **min-elements** statement. The
      default is 0.

      .. doctest::

	 >>> qsn = dm.get_data_node('/example-4-b:quux')
	 >>> qsn.min_elements
	 0

   .. attribute:: max_elements

      An integer value specifying the maximum number of list or
      leaf-list entries set by the **max-elements** statement. The
      default value is ``None``, which means that no maximum is
      specified.

      .. doctest::

	 >>> qsn.max_elements
	 2

   .. attribute:: user_ordered

      A boolean value specifying whether the list or leaf-list entries
      are ordered by user. This attribute is set by the **ordered-by**
      statement. The value of ``False`` (default) means that the
      (leaf-)list is ordered by system, i.e. the server may rearrange
      the entries.

      .. doctest::

	 >>> qsn.user_ordered
	 True

   .. rubric:: Public Methods

   .. method:: entry_from_raw(rval: RawEntry, jptr: JSONPointer = "") -> EntryValue

      Return a :term:`cooked value` of an array entry transformed from
      :term:`raw value` *rval* as dictated by the receiver and/or its
      subtree in the schema. The *jptr* argument gives the JSON
      Pointer [RFC6901]_ of the entry for the cooked value is intended
      (if known, otherwise the second argument needn't be present).

      This method raises :exc:`~.NonexistentSchemaNode` if *rval*
      contains a member that is not defined in the schema, and
      :exc:`~.YangTypeError` if a scalar value inside *rval*
      is of incorrect type.

      .. doctest::

	 >>> qsn.entry_from_raw('2.7182')
	 Decimal('2.7182')

.. class:: ListNode

   This class is a subclass of :class:`SequenceNode` and
   :class:`InternalNode`. Its instances represent YANG **list**
   nodes.

   The `method resolution order`_ for this class is as follows:

   :class:`ListNode` ► :class:`SequenceNode` ► :class:`DataNode` ►
   :class:`InternalNode` ► :class:`SchemaNode`

   .. rubric:: Instance Attributes

   .. attribute:: keys

      List containing :term:`qualified name`\ s of all keys defined by
      the **key** statement.

   .. attribute:: unique

      List of lists of schema routes. Each internal list represents a
      group of descendant leafs whose values are required to be unique
      across all list entries. See **unique** statement in [RFC7950]_,
      sec. `7.8.3`_.

   .. rubric:: Public Methods

   .. method:: orphan_entry(rval: RawObject) -> ArrayEntry

      Return an :class:`~.instance.ArrayEntry` as an isolated entry of
      the receiver list, i.e. one that has neither parent instance nor
      sibling entries. The *rval* argument provides the :term:`raw
      value` (object) to be cooked and used for the entry.

.. class:: ChoiceNode(InternalNode)

   This class is a subclass of :class:`InternalNode`. Its instances
   represent YANG **choice** nodes.

   .. rubric:: Instance Attributes

   .. attribute:: default_case

      :term:`Qualified name` specifying the default case defined by
      the **default** substatement of **choice**. The value of
      ``None`` (default) means that no case is defined as default.

      .. doctest::

	 >>> osn = bsn.get_child('opts', 'example-4-a')
	 >>> osn.default_case
	 ('a', 'example-4-a')

.. class:: CaseNode

   This class is a subclass of :class:`InternalNode`. Its instances
   represent YANG **case** nodes.

   A :class:`CaseNode` is present in the internal schema tree even if
   it is defined as a “shorthand” case in a YANG module (see
   sec. `7.9.2`_ of [RFC7950]_).

.. class:: LeafNode

   This class is a subclass of :class:`DataNode` and :class:`TerminalNode`.
   Its instances represent YANG **leaf** nodes.

   The `method resolution order`_ for this class is as follows:

   :class:`LeafNode` ► :class:`DataNode` ► :class:`TerminalNode` ►
   :class:`SchemaNode`

.. class:: LeafListNode

   This class is a subclass of :class:`SequenceNode` and
   :class:`TerminalNode`. Its instances represent YANG **leaf-list**
   nodes.

   The `method resolution order`_ for this class is as follows:

   :class:`LeafListNode` ► :class:`SequenceNode` ► :class:`DataNode` ►
   :class:`TerminalNode` ► :class:`SchemaNode`

.. class:: AnyContentNode

   This class is an abstract superclass for both **anydata** and
   **anyxml** nodes. It is a subclass od :class:`DataNode`.

.. class:: AnydataNode

   This class is a subclass of :class:`AnyContentNode`. Its instances
   represent YANG **anydata** nodes.

.. class:: AnyxmlNode

   This class is a subclass of :class:`AnyContentNode`. Its instances
   represent YANG **anyxml** nodes.

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

.. _7.5.3: https://tools.ietf.org/html/rfc7950#section-7.5.3
.. _7.8.3: https://tools.ietf.org/html/rfc7950#section-7.8.3
.. _7.9.2: https://tools.ietf.org/html/rfc7950#section-7.9.2
.. _7.21.5: https://tools.ietf.org/html/rfc7950#section-7.21.5
.. _method resolution order: https://www.python.org/download/releases/2.3/mro/
