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
   os.chdir("examples/ex1")

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
* :class:`ResourceIdParser`: Parser for RESTCONF :term:`resource
  identifier`\ s.
* :class:`InstanceIdParser`: Parser for :term:`instance identifier`\ s.

The module defines the following exceptions:

* :exc:`InstanceException`: Base class for exceptions related to
  operations on instance nodes.
* :exc:`NonexistentInstance`: Attempt to access an instance node that
  doesn't exist.
* :exc:`InstanceTypeError`: A method is called for a wrong type of
  instance node.
* :exc:`DuplicateMember`: Attempt to create a member that already exists.
* :exc:`MandatoryMember`: Attempt to remove a mandatory member.
* :exc:`MinElements`: An array becomes shorter than the minimum number
  of elements specified in the data model..
* :exc:`MaxElements`: An array becomes longer than the maximum number
  of elements specified in the data model.

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

   The easiest way to create an :class:`InstanceNode` is to use the
   :meth:`.DataModel.from_raw` method:

   .. doctest::

      >>> dm = DataModel.from_file("yang-library-ex2.json")
      >>> with open("example-data.json") as infile:
      ...   ri = json.load(infile)
      >>> inst = dm.from_raw(ri)

   The arguments of the :class:`InstanceNode` constructor provide
   values for instance variables of the same name.

   .. rubric:: Instance Variables

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

   .. attribute:: qualName

      The :term:`qualified name` of the instance node. For the root it is ``None``.

   .. rubric:: Methods

   .. method:: member(name: InstanceName) -> ObjectMember

      Return an instance node corresponding to the receiver's
      member *name*.

      This method raises :exc:`NonexistentSchemaNode` if the schema
      doesn't permit a member of that name (or any member at all), and
      :exc:`NonexistentInstance` if that member isn't present in the
      actual receiver's value.

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

      :exc:`NonexistentSchemaNode` is raised if the schema doesn't
      permit such a member.

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

   .. method:: delete_member(name: InstanceName, validate: bool = \
	       True) -> InstanceNode

      Return a new instance node that is an exact copy of the
      receiver, except that its member *name* is deleted. The
      *validate* flag controls whether the returned value is required
      to be valid. If it is set to ``False``, the member will be
      removed even if it violates the schema.

      This method may raise the following exceptions:

      * :exc:`NonexistentSchemaNode` – if member *name* is not
	permitted by the schema.
      * :exc:`NonexistentInstance` – if member *name* is not present
	in the receiver's value.
      * :exc:`MandatoryMember` – if removing member *name* isn't
	permitted by the schema, i.e. it is a mandatory node.

      .. doctest::

	 >>> xtop = e2top.delete_member('baz')
	 >>> sorted(xtop.value.keys())
	 ['bar', 'foo']
	 >>> top.delete_member('bar')
	 Traceback (most recent call last):
	 ...
	 yangson.instance.MandatoryMember: [/example-2:top] member bar
	 >>> itop = top.delete_member('bar', validate=False)
	 >>> sorted(itop.value.keys())
	 ['foo']

   .. method:: update(value: Value) -> InstanceNode

      Return a new instance node that is a copy of the receiver with
      a value specified by the *value* argument.

      .. doctest::



   .. method:: update_from_raw(rvalue: RawValue) -> InstanceNode

      Return a new instance node that is a copy of the receiver with
      the value constructed from the *rvalue* argument.

      This method is similar to :meth:`update`, only *rvalue* is
      “cooked” first (see :mod:`instvalue`).

   .. method:: entry(index: int) -> ArrayEntry

      Return an instance node corresponding to the receiver's entry
      whose index is specified by the *index* argument.

      :exc:`InstanceTypeError` is raised if the receiver's value is
      not an array, and :exc:`NonexistentInstance` is raised if entry
      *index* is not present in the receiver's value.

      .. doctest::

	 >>> foo0 = foo.entry(0)
	 >>> foo0.value['number']
	 6

   .. method:: last_entry() -> ArrayEntry

      Return an instance node corresponding to the receiver's last entry.

      :exc:`InstanceTypeError` is raised if the receiver's value is
      not an array, and :exc:`NonexistentInstance` is raised if the
      receiver is an empty array.

      .. doctest::

	 >>> foo1 = foo.last_entry()
	 >>> foo1.value['number']
	 3

   .. automethod:: json_pointer

      .. doctest::

	 >>> foo1.json_pointer()
	 '/example-2:top/foo/1'

   .. method:: up() -> InstanceNode

      Move the focus to the parent instance node. If the receiver is
      the root of the data tree, exception :exc:`NonexistentInstance`
      is raised.

      .. doctest::

	 >>> foo1.up().json_pointer()
	 '/example-2:top/foo'
	 >>> inst.up()
	 Traceback (most recent call last):
	 ...
	 yangson.instance.NonexistentInstance: [/] up of top

   .. method:: add_defaults() -> InstanceNode

      Return a new instance node that is a copy of the receiver
      extended with default values from the data model. Only default
      values that are “in use” are added, see sections `7.6.1`_ and
      `7.7.2`_ in [Bjo16]_.

      .. doctest::

	 >>> wd = inst.add_defaults()
	 >>> wd.value['example-2:top']['baz']
	 'hi!'

   .. method:: goto(iroute: InstanceRoute) -> InstanceNode

      Move the focus to an :class:`InstanceNode` inside the receiver's
      value. The argument *iroute* is an :term:`instance route`
      (relative to the receiver) that identifies the target
      instance.

      The easiest way for obtaining an instance route is to parse it
      from a :term:`instance identifier` (see
      :class:`InstanceIdParser`) or :term:`resource identifier` (see
      :class:`ResourceIdParser`).

      The instance node corresponding to the target instance
      is returned, or one of the following exceptions is raised:

      * :exc:`InstanceTypeError` – if *iroute* isn't compatible with
	the schema.
      * :exc:`NonexistentInstance` – if the target instance doesn't exist.

      .. doctest::

	 >>> lbaz = wd.goto(InstanceIdParser('/example-2:top/baz').parse())
	 >>> lbaz.value
	 'hi!'
	 >>> inst.goto(InstanceIdParser('/example-2:top/baz').parse())
	 Traceback (most recent call last):
	 ...
	 yangson.instance.NonexistentInstance: [/example-2:top] member baz

   .. method:: delete_entry(index: int, validate: bool = True) -> \
	       InstanceNode

      Return a new instance node that is an exact copy of the
      receiver, except that its entry specified by *index* is
      deleted. The *validate* flag controls whether the returned value
      is required to be valid. If it is set to ``False``, the entry
      will be removed even if it violates the schema.

      This method may raise the following exceptions:

      * :exc:`InstanceTypeError` – if the receiver is not an array.
      * :exc:`NonexistentInstance` – if entry *index* is not present
	in the receiver's value.
      * :exc:`MinElements` – if after removing the entry the number of
	entries would drop below the minimum value specified by
	**min-elements**.

   .. method:: look_up(keys: Dict[InstanceName, ScalarValue]) -> ArrayEntry

      Return an instance node corresponding to the receiver's entry
      with keys specified by the argument *keys*.

      This method may raise the following exceptions:

      * :exc:`InstanceTypeError` – if the receiver is not a YANG list.
      * :exc:`NonexistentInstance` – if no entry with matching keys exists.

   .. method:: peek(iroute: InstanceRoute) -> Optional[Value]

      Return a value inside the receiver's subtree. The argument
      *iroute* is an :term:`instance route` (relative to the receiver)
      that identifies the target instance. ``None`` is returned if the
      target instance doesn't exist.

      .. CAUTION::
      This method doesn't create a new instance, so the
      access to the returned value should in general be read-only,
      because any modifications of the returned value would also
      affect the receiver, hence destroy the persistence property.

   .. method:: top() -> InstanceNode

      Return a root instance node.

   .. method:: validate(content: ContentType = ContentType.config) -> None

      Validate the receiver's value. The *content* argument specifies
      whether the value is configuration (``Content.config``) or both
      configuration and state data.

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

   .. method:: is_structured() -> bool

      Return ``True`` if the receiver's value is structured, i.e. it
      is an :class:`~.instvalue.ArrayValue` or
      :class:`~.instvalue.ObjectValue`.

.. autoclass:: RootNode
   :show-inheritance:

   .. rubric:: Instance Variables

   .. attribute:: name

      The :term:`instance name` of the root node is always ``None``.

.. class:: ObjectMember(name: InstanceName, siblings: \
	   Dict[InstanceName, Value], value: Value, parinst: \
	   Optional[InstanceNode], schema_node: DataNode, timestamp: \
	   datetime.datetime)

   This class represents an instance node that is a member of an
   object. It is a subclass of :class:`InstanceNode`. The additional
   constructor arguments *name* and *siblings* provide
   values for instance variables of the same name. Other arguments
   have the same meaning as in :class:`InstanceNode`.

   .. rubric:: Instance Variables

   .. attribute:: name

      Instance name of the receiver as a member of the parent object.

   .. attribute:: siblings

      Dictionary of the receiver's siblings (other members of the
      parent object).

   .. rubric:: Properties

   .. attribute:: qualName

      The :term:`qualified name` of the receiver.

   .. rubric:: Methods

   .. method:: sibling(name: InstanceName) -> ObjectMember

      Return the instance node corresponding to sibling member *name*.

      :exc:`NonexistentSchemaNode` is raised if member *name* is not
      permitted by the parent's schema, and :exc:`NonexistentInstance`
      is raised if such sibling member *name* doesn't exist.

.. class:: ArrayEntry(before: List[Value], after: List[Value], value: \
	   Value, parinst: Optional[InstanceNode], schema_node: \
	   DataNode, timestamp: datetime.datetime)

   This class is a subclass of :class:`InstanceNode`, and represents
   an instance node that is an entry of an array, i.e. list or
   leaf-list.  The additional constructor arguments *before* and
   *after* provide values for instance variables of the same
   name. Other arguments have the same meaning as in
   :class:`InstanceNode`.

   .. rubric:: Instance Variables

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

   .. attribute:: qualName

      The :term:`qualified name` of an array entry is by definition
      the same as the qualified name of the parent array.

   .. rubric:: Methods

   .. method:: following_entries() -> List["ArrayEntry"]

      Return the list of entries following the receiver in the parent array.

   .. method:: insert_after(value: Value, validate: bool = True) -> ArrayEntry

      Insert a new entry after the receiver and return an instance
      node of the new entry. The *value* argument specifies the value
      of the new entry. The *validate* flag controls whether the
      parent array is required to be valid after the new entry is
      inserted.

      :exc:`MaxElements` is raised if *validate* is ``True`` and the
      number of entries would exceed the limit specified by
      **max-elements**.

   .. method:: insert_before(value: Value, validate: bool = True) -> ArrayEntry

      Insert a new entry before the receiver and return an
      instance node of the new entry. The *value* argument specifies
      the value of the new entry. The *validate* flag controls whether
      the parent array is required to be valid after the new entry is
      inserted.

      :exc:`MaxElements` is raised if *validate* is ``True`` and the
      number of entries would exceed the limit specified by
      **max-elements**.

   .. method:: next() -> ArrayEntry

      Return an instance node corresponding to the next entry in the
      parent array. :exc:`NonexistentInstance` is raised if the
      receiver is the last entry of the parent array.

   .. method:: preceding_entries() -> List["ArrayEntry"]

      Return the list of entries preceding the receiver in the parent array.

   .. method:: previous() -> ArrayEntry

      Return an instance node corresponding to the previous entry in
      the parent array. :exc:`NonexistentInstance` is raised if the
      receiver is the first entry of the parent array.

.. class:: ResourceIdParser(text: str)

   This class is a subclass of :class:`~.parser.Parser`, and
   implements a parser for RESTCONF :term:`resource
   identifier`\ s. The constructor argument *text* is the resource
   identifier to be parsed.

   .. rubric:: Methods

   .. method:: parse() -> InstanceRoute

      Parse a :term:`resource identifier` into an :term:`instance
      route` that can be used as an argument for the methods
      :meth:`InstanceNode.goto` and :meth:`InstanceNode.peek`.

.. class:: InstanceIdParser(text: str)

   This class is a subclass of :class:`~.parser.Parser`, and
   implements a parser for :term:`instance identifier`\ s. The
   constructor argument *text* is the instance identifier to be
   parsed.

   .. rubric:: Methods

   .. method:: parse() -> InstanceRoute

      Parse an :term:`instance identifier` into an :term:`instance
      route` that can be used as an argument for the methods
      :meth:`InstanceNode.goto` and :meth:`InstanceNode.peek`.

.. autoexception:: InstanceException(inst: InstanceNode)
   :show-inheritance:

   The *inst* argument is the initial instance from which the failed
   operation was attempted.

.. autoexception:: NonexistentInstance
   :show-inheritance:

   The *detail* argument gives details about why the instance doesn't exist.

.. autoexception:: InstanceTypeError
   :show-inheritance:

   The *detail* argument gives details about the type mismatch.

.. autoexception:: DuplicateMember
   :show-inheritance:

   The *name* argument is the instance name of the duplicate member.

.. autoexception:: MandatoryMember
   :show-inheritance:

   The *name* argument is the instance name of the mandatory member.

.. autoexception:: MinElements
   :show-inheritance:

.. autoexception:: MaxElements
   :show-inheritance:

.. _7.6.1: https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis#section-7.6.1
.. _7.7.2: https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis#section-7.7.2
