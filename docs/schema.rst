===========
YANG Schema
===========

.. module:: yangson.schema
   :synopsis: Classes and methods for working with YANG schema nodes
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

This module offers classes representing YANG schema nodes.

This module defines several type aliases representing “raw” values produced by the JSON parser :func:`json.loads`.

+--------------------+------------------------------+
|Alias               |Type                          |
+====================+==============================+
|:const:`RawObject`  |``Dict[InstanceName,          |
|                    |RawValue]``                   |
+--------------------+------------------------------+
|:const:`RawList`    |``List[RawObject]``           |
+--------------------+------------------------------+
|:const:`RawLeafList`|``List[RawScalar]``           |
+--------------------+------------------------------+
|:const:`RawValue`   |``Union[RawScalar, RawObject, |
|                    |RawList, RawLeafList]``       |
+--------------------+------------------------------+


.. class:: SchemaNode

   This class serves as the top-level abstract superclass for all schema node classes.

   .. attribute:: name

      Name of the schema node.

   .. attribute:: ns

      Namespace of the schema node (= YANG module name).

   .. attribute:: parent

      Parent schema node.

   .. attribute:: config

      This boolean attribute is ``True`` if the receiver represents
      configuration, and ``False`` otherwise. Implemented as a
      :class:`property`.

   .. automethod:: instance_route

   .. automethod:: state_roots

.. class:: InternalNode(SchemaNode)

   This is the superclass for schema nodes that have children.

   The whole schema in :attr:`Context.schema` is an instance of this
   class. Other instances should not be created.

   .. attribute:: children

      The list of children.

   .. automethod:: get_child

   .. automethod:: get_schema_descendant

   .. automethod:: get_data_child

   .. automethod:: from_raw

.. class:: DataNode(SchemaNode)

   This is the abstract superclass for data nodes.

   .. attribute:: default_deny

      NACM default deny value belonging to the :class:`DefaultDeny` enumeration.

.. class:: TerminalNode(SchemaNode)

   This is the abstract superclass for terminal nodes in the schema
   tree.

   .. attribute:: mandatory

      A boolean value specifying whether the instance is mandatory.

   .. attribute:: type

      The data type object.

   .. automethod:: from_raw

.. class:: ContainerNode(InternalNode, DataNode)

   Class representing YANG **container** node.

   .. attribute:: presence

      A boolean value specifying whether the instance is a container
      with presence.

   .. attribute:: mandatory

      A boolean value specifying whether the instance is mandatory.

.. class:: SequenceNode(DataNode)

   Abstract class for data nodes representing a sequence,
   i.e. **list** and **leaf-list**.

   .. attribute:: min_elements

      An integer value specifying the minimum number of list or
      leaf-list entries.

   .. attribute:: max_elements

      An integer value specifying the maximum number of list or
      leaf-list entries. If no maximum is specified, the value of this
      attribute is ``None``.

   .. attribute:: user_ordered

      A boolean value specifying whether the list or leaf-list entries
      are ordered by user. The value of ``False`` means the
      (leaf-)list is ordered by system, which means that the server
      may rearrange the entries.

   .. automethod:: from_raw

.. class:: ListNode(InternalNode, SequenceNode)

   Class representing YANG **list** node.

   .. attribute:: keys

      List containing qualified names of all keys.

   .. attribute:: unique

      List of lists of schema routes. Each internal list represents a
      group of descendant leafs whose values are required to be unique
      across all list entries. See [RFC7950]_, sec. `7.8.3`_.

.. class:: ChoiceNode(InternalNode)

   Class representing YANG **Choice** node.

   .. attribute:: default

      Optional qualified name specifying the default case.

   .. attribute:: mandatory

      A boolean value specifying whether one of the cases is required
      to exist.

.. class:: CaseNode(InternalNode)

   Class representing YANG **case** node.

.. class:: RpcActionNode(InternalNode)

   Class representing YANG **rpc** or **action** node.

.. class:: InputNode(InternalNode)

   Class representing YANG **input** node.

.. class:: OutputNode(InternalNode)

   Class representing YANG **output** node.

.. class:: LeafNode(TerminalNode, DataNode)

   Class representing YANG **leaf** node.

   .. attribute:: default

      Default value of the leaf instance or its type. Implemented as a
      :class:`property`.

.. class:: LeafListNode(TerminalNode, SequenceNode)

   Class representing YANG **leaf-list** node.

   .. attribute:: default

      Default value of the leaf-list instance or its type. Implemented
      as a :class:`property`.

   .. attribute:: min_elements

      An integer value specifying the minimum number of leaf-list entries.

   .. attribute:: max_elements

      An integer value specifying the maximum number of leaf-list entries.

.. class:: AnydataNode(TerminalNode, DataNode)

   Class representing YANG **anydata** node.

.. class:: AnyxmlNode(TerminalNode, DataNode)

   Class representing YANG **anyxml** node.

.. _7.8.3: https://tools.ietf.org/html/rfc7950-11#section-7.8.3
