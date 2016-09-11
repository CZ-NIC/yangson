**************************
 Persistent Data Instances
**************************

.. module:: yangson.instance
   :synopsis: Persistent data instances.

.. testsetup::

   import json
   import os
   from yangson import DataModel
   from yangson.instance import InstanceIdParser
   os.chdir("examples/ex2")

.. testcleanup::

   os.chdir("../..")
   del DataModel._instances[DataModel]

Instance data represented as a `persistent structure`__.

__ https://en.wikipedia.org/wiki/Persistent_data_structure

This module implements the following classes:

* :class:`InstanceNode`: Abstract class for instance nodes.
* :class:`RootNode`: Root of the data tree.
* :class:`ObjectMember`: Instance node that is an object member.
* :class:`ArrayEntry`: Instance node that is an array entry.
* :class:`InstanceRoute`: Route into an instance value.
* :class:`ResourceIdParser`: Parser for RESTCONF :term:`resource
  identifier`\ s.
* :class:`InstanceIdParser`: Parser for :term:`instance identifier`\ s.

The module defines the following exceptions:

* :exc:`InstanceException`: Base class for exceptions related to
  operations on instance nodes.
* :exc:`InstanceValueError`: The instance value is incompatible with
  the called method.
* :exc:`NonexistentInstance`: Attempt to access an instance node that
  doesn't exist.

.. class:: InstanceNode(value: Value, parinst: Optional[InstanceNode], \
	   schema_node: DataNode, timestamp: datetime.datetime)

   This class and its subclasses implement a *zipper* interface for
   JSON-like values along the lines of Gérard Huet's original
   paper [Hue97]_. However, due to the heterogeneity of JSON-like
   values, the zipper interface is not as simple and elegant as for
   normal trees. In particular, sibling instance nodes have different
   representations depending on their type, which can be either
   :class:`ObjectMember` (for nodes that are object members) or
   :class:`ArrayEntry` (for nodes that are array entries).

   Inside the larger structure of a data tree, an
   :class:`InstanceNode` represents “focus” on a particular node of
   the structure. The focus can be moved to a neighbour instance node
   (parent, child, sibling) and the value of an instance node can be
   created, deleted and updated by using the methods described
   below. Each of the methods returns a new :class:`InstanceNode` that
   shares, as much as possible, portions of the surrounding data tree
   with the original instance node.  However, any modifications to the
   new instance node – if performed through the methods of the
   :class:`InstanceNode` class and its subclasses – leave other
   instance nodes intact.

   Most methods for moving the focus inside the zipper structure and
   updating the value of an instance node are defined in the
   :class:`InstanceNode`, additional methods that are specific to an
   :class:`ObjectMember` or :class:`ArrayEntry` are defined in the
   respective class.

   The easiest way to create an :class:`InstanceNode` is to use the
   :meth:`.DataModel.from_raw` method:

   .. doctest::

      >>> dm = DataModel.from_file("yang-library-ex2.json")
      >>> with open("example-data.json") as infile:
      ...   ri = json.load(infile)
      >>> inst = dm.from_raw(ri)

   The arguments of the :class:`InstanceNode` constructor provide
   values for instance variables of the same name.

   .. rubric:: Instance Attributes

   .. attribute:: parinst

      Parent instance node, or ``None`` for the root node.

   .. attribute:: schema_node

      Data node in the schema corresponding to the instance node.

   .. attribute:: timestamp

      The time when the instance node was last modified.

   .. attribute:: value

      Scalar or structured value of the node, see module :mod:`instvalue`.

      .. doctest::

	 >>> inst.value['example-2:top']['bar']
	 True
	 >>> inst.value['example-2:top']['baz']
	 Traceback (most recent call last):
	 ...
	 KeyError: 'baz'

   .. rubric:: Properties

   .. attribute:: namespace

      The :term:`namespace identifier` of the instance node. For the root
      node it is ``None``.

   .. attribute:: qual_name

      The :term:`qualified name` of the receiver. For the root node it
      is ``None``.

   .. rubric:: Public Methods

   .. automethod:: __str__

      If the receiver's value is a scalar, then the result is the
      :term:`canonical representation` of the value, if it is defined
      for the value's type (see sec. `9`_ in [RFC7950]_). Otherwise,
      the result is the value returned by Python standard function
      :class:`str`.

   .. method:: is_internal() -> bool

      Return ``True`` if the receiver is an instance of an internal
      schema node, i.e. its :attr:`schema_node` is an
      :class:`~.schema.InternalNode`. Otherwise return ``False``.

   .. automethod:: json_pointer

      This method is used in several *doctest* examples below.

   .. method:: member(name: InstanceName) -> ObjectMember

      Return an instance node corresponding to the receiver's
      member *name*.

      This method may raise the following exceptions:

      * :exc:`InstanceValueError` – if receiver's value is not an
	object.
      * :exc:`NonexistentSchemaNode` – if the schema doesn't permit
	member *name*,
      * :exc:`NonexistentInstance` – if member *name* isn't present in
	the actual receiver's value,

      .. doctest::

	 >>> top = inst.member('example-2:top')
	 >>> foo = top.member('foo')
	 >>> foo.value[0]['number']
	 6
	 >>> top.member('baz')
	 Traceback (most recent call last):
	 ...
	 yangson.instance.NonexistentInstance: [/example-2:top] member baz

   .. method:: put_member(name: InstanceName, value: Value) -> InstanceNode

      Return a new instance node that is an exact copy of the
      receiver, except that its member *name* gets the value from the
      *value* argument. If that member doesn't exist in the receiver's
      value, it is created (provided that the schema permits it).

      This method raises :exc:`InstanceValueError` if the receiver's
      value is not an object, and :exc:`NonexistentSchemaNode` if the
      schema doesn't permit member *name*.

      .. doctest::

	 >>> etop = top.put_member("bar", False)
	 >>> etop.value['bar']
	 False
	 >>> top.value['bar']                       # top is unchanged
	 True
	 >>> e2top = top.put_member("baz", "hola")  # member baz is created
	 >>> sorted(e2top.value.keys())
	 ['bar', 'baz', 'foo']
	 >>> top.put_member("quux", 0)
	 Traceback (most recent call last):
	 ...
	 yangson.schema.NonexistentSchemaNode: quux in module example-2

   .. method:: delete_member(name: InstanceName) -> InstanceNode

      Return a new instance node that is an exact copy of the
      receiver, except that member *name* is deleted from its value.

      This method raises :exc:`InstanceValueError` if the receiver's
      value is not an object, and:exc:`NonexistentInstance` if member
      *name* isn't present in the actual receiver's value.

      .. doctest::

	 >>> xtop = e2top.delete_member('baz')
	 >>> sorted(xtop.value.keys())
	 ['bar', 'foo']

   .. method:: look_up(keys: Dict[InstanceName, ScalarValue]) -> ArrayEntry

      Return an instance node corresponding to the receiver's entry
      with keys specified by *keys*. The receiver must be a YANG list.

      The argument *keys* is a dictionary whose keys are
      :term:`instance name`\ s of the list keys, and values are the
      corresponding list key values.

      This method raises :exc:`InstanceValueError` if the receiver is
      not a YANG list, and :exc:`NonexistentInstance` if no entry with
      matching keys exists.

   .. method:: entry(index: int) -> ArrayEntry

      Return an instance node corresponding to the receiver's entry
      whose index is specified by the *index* argument.

      This method raises :exc:`InstanceValueError` if the receiver's
      value is not an array, and :exc:`NonexistentInstance` if entry
      *index* is not present in the receiver's value.

      .. doctest::

	 >>> foo0 = foo.entry(0)
	 >>> foo0.value['number']
	 6

   .. method:: last_entry() -> ArrayEntry

      Return an instance node corresponding to the receiver's last entry.

      :exc:`InstanceValueError` is raised if the receiver's value is
      not an array, and :exc:`NonexistentInstance` is raised if the
      receiver is an empty array.

      .. doctest::

	 >>> foo1 = foo.last_entry()
	 >>> foo1.value['number']
	 3

   .. method:: delete_entry(index: int) -> InstanceNode

      Return a new instance node that is an exact copy of the
      receiver, except that the entry specified by *index* is deleted
      from its value.

      This method raises :exc:`InstanceValueError` if the receiver is
      not an array, and :exc:`NonexistentInstance` if entry *index* is
      not present in the actual receiver's value.

   .. method:: up() -> InstanceNode

      Return an instance node corresponding to the receiver's parent.

      This method raises :exc:`NonexistentInstance` if the receiver is
      the root of the data tree and thus has no parent.

      .. doctest::

	 >>> foo1.up().json_pointer()
	 '/example-2:top/foo'
	 >>> inst.up()
	 Traceback (most recent call last):
	 ...
	 yangson.instance.NonexistentInstance: [/] up of top

   .. automethod:: top() -> InstanceNode

   .. method:: update(value: Value) -> InstanceNode

      Return a new instance node that is a copy of the receiver with
      a value specified by the *value* argument.

      .. doctest::



   .. method:: update_from_raw(rvalue: RawValue) -> InstanceNode

      Return a new instance node that is a copy of the receiver with
      the value constructed from the *rvalue* argument.

      This method is similar to :meth:`update`, only the argument
      *rvalue* is a :term:`raw value` that needs to be “cooked” first
      (see :mod:`instvalue`).

   .. method:: goto(iroute: InstanceRoute) -> InstanceNode

      Return an :class:`InstanceNode` corresponding to a target
      instance arbitrarily deep inside the receiver's value. The
      argument *iroute* is an :class:`InstanceRoute` (relative to the
      receiver) that identifies the target instance.

      The easiest way for obtaining an :class:`InstanceRoute` is to
      parse it from an :term:`instance identifier` (see
      :class:`InstanceIdParser`) or :term:`resource identifier` (see
      :class:`ResourceIdParser`).

      This method raises :exc:`InstanceValueError` if *iroute* isn't
      compatible with the schema, and :exc:`NonexistentInstance` if
      the target instance doesn't exist in the receiver's value.

      .. doctest::

	 >>> lbaz = wd.goto(InstanceIdParser('/example-2:top/baz').parse())
	 >>> lbaz.value
	 'hi!'
	 >>> inst.goto(InstanceIdParser('/example-2:top/baz').parse())
	 Traceback (most recent call last):
	 ...
	 yangson.instance.NonexistentInstance: [/example-2:top] member baz

   .. method:: peek(iroute: InstanceRoute) -> Optional[Value]

      Return the value of a target instance arbitrarily deep inside
      the receiver's value. The argument *iroute* is an
      :class:`InstanceRoute` (relative to the receiver) that
      identifies the target instance. ``None`` is returned if the
      target instance doesn't exist.

      .. CAUTION:: This method doesn't create a new instance, so the
      access to the returned value should in general be read-only,
      because any modifications of the returned value would also
      affect the receiver, so the persistence property would be
      violated.

   .. method:: validate(content: ContentType = ContentType.config) -> None

      Perform schema validation on the receiver's value. The *content*
      argument specifies whether the value is configuration
      (``Content.config``) or both configuration and state data
      (``Content.all``).

      The method returns ``None`` if the validation succeeds,
      otherwise one of the following exceptions is raised:

      * :exc:`.schema.SchemaError` – if the value doesn't conform to
	the schema,
      * :exc:`.schema.SemanticError` – if the value violates a
	semantic constraint.

      .. doctest::

	 >>> inst.validate()
	 >>> inst.value['example-2:top']['baz'] = "ILLEGAL"
	 >>> inst.validate()
	 Traceback (most recent call last):
	 ...
	 yangson.schema.SchemaError: [/example-2:top] not allowed: member 'baz'

   .. method:: add_defaults() -> InstanceNode

      Return a new instance node that is a copy of the receiver
      extended with default values specified the data model. Only
      default values that are “in use” are added, see sections
      `7.6.1`_ and `7.7.2`_ in [RFC7950]_.

      .. doctest::

	 >>> wd = inst.add_defaults()
	 >>> wd.value['example-2:top']['baz']
	 'hi!'

   .. automethod:: raw_value() -> RawValue

.. autoclass:: RootNode
   :show-inheritance:

   .. rubric:: Instance Attributes

   .. attribute:: name

      The :term:`instance name` of the root node is always ``None``.

.. class:: ObjectMember(name: InstanceName, siblings: \
	   Dict[InstanceName, Value], value: Value, parinst: \
	   InstanceNode, schema_node: DataNode, timestamp: \
	   datetime.datetime)

   This class represents an instance node that is a member of an
   object. It is a subclass of :class:`InstanceNode`. The additional
   constructor arguments *name* and *siblings* provide values for
   instance variables of the same name. Other arguments of the
   constructor have the same meaning as in :class:`InstanceNode`.

   .. rubric:: Instance Attributes

   .. attribute:: name

      Instance name of the receiver as a member of the parent object.

   .. attribute:: siblings

      Dictionary of the receiver's siblings (other members of the
      parent object).

   .. rubric:: Public Methods

   .. method:: sibling(name: InstanceName) -> ObjectMember

      Return the instance node corresponding to sibling member *name*.

      This method raises :exc:`NonexistentSchemaNode` if member *name*
      is not permitted by the parent's schema, and
      :exc:`NonexistentInstance` if sibling member *name* doesn't
      exist.

.. class:: ArrayEntry(before: List[Value], after: List[Value], value: \
	   Value, parinst: InstanceNode, schema_node: \
	   DataNode, timestamp: datetime.datetime)

   This class is a subclass of :class:`InstanceNode`, and represents
   an instance node that is an entry of an array, i.e. list or
   leaf-list.  The additional constructor arguments *before* and
   *after* provide values for instance variables of the same
   name. Other arguments have the same meaning as in
   :class:`InstanceNode`.

   .. rubric:: Instance Attributes

   .. attribute:: before

      Entries of the parent array that precede the receiver.

   .. attribute:: after

      Entries of the parent array that follow the receiver.

   .. rubric:: Properties

   .. attribute:: index

      The receiver's index within the parent array.

   .. attribute:: name

      The :term:`instance name` of an array entry is by definition the
      same as the instance name of the parent array.

   .. rubric:: Public Methods

   .. method:: previous() -> ArrayEntry

      Return an instance node corresponding to the previous entry in
      the parent array.

      This method raises :exc:`NonexistentInstance` if the receiver
      is the first entry of the parent array.

   .. method:: next() -> ArrayEntry

      Return an instance node corresponding to the next entry in the
      parent array.

      This method raises :exc:`NonexistentInstance` if the receiver is
      the last entry of the parent array.

   .. method:: insert_before(value: Value) -> ArrayEntry

      Insert a new entry before the receiver and return an instance
      node corresponding to the new entry. The *value* argument
      specifies the value of the new entry.

   .. method:: insert_after(value: Value, validate: bool = True) -> ArrayEntry

      Insert a new entry after the receiver and return an instance
      node corresponding to the new entry. The *value* argument
      specifies the value of the new entry.

.. autoclass:: InstanceRoute
   :show-inheritance:

   Instances are expected to be created by using either the class
   method :meth:`from_schema_route` or one of the parser classes
   :class:`ResourceIdParser` and :class:`InstanceIdParser`.

   .. rubric:: Public Methods

   .. classmethod:: from_schema_route(sroute: SchemaRoute, start: \
		    SchemaNode) -> InstanceRoute

      Return an :class:`InstanceRoute` constructed from the
      :term:`schema route` *sroute*. The *start* argument is the
      :class:`~.schema.SchemaNode` from which the schema route starts.

      This method raises :exc:`~.schema.NonexistentSchemaNode` if
      either *start* or one of the components of *sroute* doesn't
      exist in the schema tree.

.. class:: ResourceIdParser(text: str)

   This class is a subclass of :class:`~.parser.Parser`, and
   implements a parser for RESTCONF :term:`resource
   identifier`\ s. The constructor argument *text* is the resource
   identifier to be parsed.

   .. rubric:: Public Methods

   .. method:: parse() -> InstanceRoute

      Return an :class:`InstanceRoute` by parsing a :term:`resource
      identifier` contained in the instance attribute :attr:`text`.

      The returned value can be passed as the argument to
      :meth:`InstanceNode.goto` and :meth:`InstanceNode.peek` methods.

.. class:: InstanceIdParser(text: str)

   This class is a subclass of :class:`~.parser.Parser`, and
   implements a parser for :term:`instance identifier`\ s. The
   constructor argument *text* is the instance identifier to be
   parsed.

   .. rubric:: Public Methods

   .. method:: parse() -> InstanceRoute

      Return an :class:`InstanceRoute` by parsing an :term:`instance
      identifier` contained in the instance attribute :attr:`text`.

      The returned value can be passed as the argument to
      :meth:`InstanceNode.goto` and :meth:`InstanceNode.peek` methods.

.. autoexception:: InstanceException(inst: InstanceNode)
   :show-inheritance:

   The *inst* argument is the initial instance from which the failed
   operation was attempted.

.. autoexception:: InstanceValueError
   :show-inheritance:

   The *detail* argument gives details about the value mismatch.

.. autoexception:: NonexistentInstance
   :show-inheritance:

   The *detail* argument gives details about why the instance doesn't
   exist.

.. _7.6.1: https://tools.ietf.org/html/rfc7950#section-7.6.1
.. _7.7.2: https://tools.ietf.org/html/rfc7950#section-7.7.2
.. _9: https://tools.ietf.org/html/rfc7950#section-9
