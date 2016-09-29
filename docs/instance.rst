**************************
 Persistent Data Instances
**************************

.. module:: yangson.instance
   :synopsis: Persistent data instances.

.. testsetup::

   import json
   import os
   from yangson import DataModel
   from yangson.instance import (InstanceIdParser, InstanceRoute,
                                 ResourceIdParser)
   os.chdir("examples/ex2")

.. testcleanup::

   os.chdir("../..")
   del DataModel._instances[DataModel]

The *instance* module implements the following classes:

* :class:`InstanceNode`: Abstract class for instance nodes.
* :class:`RootNode`: Root of the data tree.
* :class:`ObjectMember`: Instance node that is an object member.
* :class:`ArrayEntry`: Instance node that is an array entry.
* :class:`InstanceRoute`: Route into an instance value.
* :class:`ResourceIdParser`: Parser for RESTCONF :term:`resource
  identifier`\ s.
* :class:`InstanceIdParser`: Parser for :term:`instance identifier`\ s.

This module also defines the following exceptions:

* :exc:`InstanceException`: Base class for exceptions related to
  operations on instance nodes.
* :exc:`InstanceValueError`: The instance value is incompatible with
  the called method.
* :exc:`NonexistentInstance`: Attempt to access an instance node that
  doesn't exist.

.. class:: InstanceNode(value: Value, parinst: Optional[InstanceNode], \
	   schema_node: DataNode, timestamp: datetime.datetime)

   This class and its subclasses implement the *zipper* interface for
   instance data along the lines of Gérard Huet's original
   paper [Hue97]_, only adapted for the specifics of JSON-like
   structures. An important property of the zipper interface is that
   it makes the underlying data structure persistent__: any changes to
   the data realized through the methods of the :class:`InstanceNode`
   class return an updated *copy* of the original instance without
   changing the latter. As much as possible, the data are shared
   between the original instance and the updated copy.

   __ https://en.wikipedia.org/wiki/Persistent_data_structure

   Whilst the zipper interface slightly complicates access to instance
   data, it provides the advantages of persistent structures that are
   known from functional programming languages:

   * The structures are thread-safe.

   * It is easy to edit the data and then return to the original
     version, for example if new version isn't valid according to the
     data model.

   * Staging datastores, such as *candidate* in NETCONF (sec. `8.3`_
     in [RFC6241]_) can be implemented in a space-efficient way.

   .. rubric:: Instance Attributes

   .. attribute:: parinst

      Parent instance node, or ``None`` for the root node.

   .. attribute:: schema_node

      Data node in the schema corresponding to the instance node.

   .. attribute:: timestamp

      The time when the instance node was last modified.

   .. attribute:: value

      Scalar or structured value of the node, see module :mod:`instvalue`.

   The arguments of the :class:`InstanceNode` constructor provide
   values for instance attributes of the same name.

   .. rubric:: Properties

   .. attribute:: namespace

      The :term:`namespace identifier` of the instance node. For the root
      node it is ``None``.

   .. attribute:: qual_name

      The :term:`qualified name` of the receiver. For the root node it
      is ``None``.

   An :class:`InstanceNode` structure can be created from scratch, or
   read from JSON text using :meth:`.DataModel.from_raw` method as in
   the following example:

   .. doctest::

      >>> dm = DataModel.from_file('yang-library-ex2.json')
      >>> with open('example-data.json') as infile:
      ...   ri = json.load(infile)
      >>> inst = dm.from_raw(ri)

   The internal representation of :class:`InstanceNode` values is very
   similar to the JSON encoding of data modelled with
   YANG [RFC7951]_. In particular, member names have to be in the form
   specified in sec. `4`_ of that document:

   .. productionlist::
      member-name: [identifier ":"] identifier

   where the first identifier is a module name and the second is a
   data node name. The longer (namespace-qualified) form is used if
   and only if the member is defined in a different YANG module than
   its parent.

   .. doctest::

      >>> inst.value["example-2:bag"]["bar"]
      True

   A structured :class:`InstanceNode` value is represented as either
   :class:`~.instvalue.ObjectValue` or
   :class:`~.instvalue.ArrayValue`, see :mod:`instvalue` for
   details. The representation of a scalar value depends on its type
   (see :mod:`datatype` module). Structured values, and some scalar
   values as well, are *not* the same as the values provided by the
   generic JSON parsing functions :func:`json.load` and
   :func:`json.loads`. Therefore, values read from JSON text need some
   additional processing, or “cooking”. *Yangson* methods such as
   :meth:`.DataModel.from_raw` take care of this step.

   .. doctest::

      >>> type(inst.value)
      <class 'yangson.instvalue.ObjectValue'>

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

      .. doctest::

	 >>> inst.is_internal()
	 True

   .. automethod:: json_pointer

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

	 >>> bag = inst.member('example-2:bag')
	 >>> foo = bag.member('foo')
	 >>> foo.json_pointer()
	 '/example-2:bag/foo'
	 >>> bag.member('baz')
	 Traceback (most recent call last):
	 ...
	 yangson.instance.NonexistentInstance: [/example-2:bag] member baz

   .. method:: put_member(name: InstanceName, value: Union[RawValue, \
	       Value], raw: bool = False) -> InstanceNode

      Return receiver's member *name* with a new value specified by the
      *value* argument. The *raw* flag has to be set to ``True`` if
      *value* is a :term:`raw value`.

      If member *name* doesn't exist in the receiver's value, it is
      created (provided that the schema permits it).

      This method raises :exc:`InstanceValueError` if the receiver's
      value is not an object, and :exc:`NonexistentSchemaNode` if the
      schema doesn't permit member *name*.

      .. doctest::

	 >>> nbar = bag.put_member('bar', False)
	 >>> nbar.value
	 False
	 >>> bag.value['bar']                       # bag is unchanged
	 True
	 >>> e2bag = bag.put_member('baz', 3.1415926).up()  # baz is created
	 >>> sorted(e2bag.value.keys())
	 ['bar', 'baz', 'foo']
	 >>> bag.put_member('quux', 0)
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

	 >>> xbag = e2bag.delete_member('baz')
	 >>> sorted(xbag.value.keys())
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

      .. doctest::

	 >>> foo3 = foo.look_up({'number': 3})
	 >>> foo3.json_pointer()
	 '/example-2:bag/foo/1'

   .. method:: entry(index: int) -> ArrayEntry

      Return an instance node corresponding to the receiver's entry
      whose index is specified by the *index* argument.

      This method raises :exc:`InstanceValueError` if the receiver's
      value is not an array, and :exc:`NonexistentInstance` if entry
      *index* is not present in the receiver's value.

      .. doctest::

	 >>> foo6 = foo.entry(0)
	 >>> foo6.value['number']
	 6

   .. method:: last_entry() -> ArrayEntry

      Return an instance node corresponding to the receiver's last entry.

      :exc:`InstanceValueError` is raised if the receiver's value is
      not an array, and :exc:`NonexistentInstance` is raised if the
      receiver is an empty array.

      .. doctest::

	 >>> foo.last_entry().json_pointer()
	 '/example-2:bag/foo/1'

   .. method:: delete_entry(index: int) -> InstanceNode

      Return a new instance node that is an exact copy of the
      receiver, except that the entry specified by *index* is deleted
      from its value.

      This method raises :exc:`InstanceValueError` if the receiver is
      not an array, and :exc:`NonexistentInstance` if entry *index* is
      not present in the actual receiver's value.

      >>> xfoo = foo.delete_entry(0)
      >>> len(xfoo.value)
      1
      >>> len(foo.value)
      2

   .. method:: up() -> InstanceNode

      Return an instance node corresponding to the receiver's parent.

      This method raises :exc:`NonexistentInstance` if the receiver is
      the root of the data tree and thus has no parent.

      .. doctest::

	 >>> foo.up().name
	 'example-2:bag'
	 >>> inst.up()
	 Traceback (most recent call last):
	 ...
	 yangson.instance.NonexistentInstance: [/] up of top

   .. automethod:: top() -> InstanceNode

      .. doctest::

	 >>> e2inst = e2bag.top()
	 >>> e2inst.value['example-2:bag']['baz']
	 3.1415926

   .. method:: update(value: Union[RawValue, Value], raw: bool = \
	       False) -> InstanceNode

      Return a new instance node that is a copy of the receiver with a
      value specified by the *value* argument. The *raw* flag has to
      be set to ``True`` if *value* is a :term:`raw value`.

      .. doctest::

	 >>> ebar = bag.member('bar').update(False)
	 >>> ebar.value
	 False

      In the following example, the string ``'2.7182818'`` is an
      acceptable :term:`raw value` for the *baz* leaf whose type is
      **decimal64** (see sec. `6.1`_ in [RFC7951]_). Since the *raw*
      flag is set, the :meth:`update` method “cooks” the raw value
      first into the Python's :class:`decimal.Decimal` type.

      >>> e3baz = e2bag.member('baz').update_from_raw('2.7182818')
      >>> e3baz.value
      Decimal('2.7182818')

   .. method:: goto(iroute: InstanceRoute) -> InstanceNode

      Return an :class:`InstanceNode` corresponding to a target
      instance arbitrarily deep inside the receiver's value. The
      argument *iroute* is an :class:`InstanceRoute` (relative to the
      receiver) that identifies the target instance.

      The easiest way for obtaining an :class:`InstanceRoute` is to
      parse it either from a :term:`resource identifier` (see
      :class:`ResourceIdParser`) or an :term:`instance identifier`
      (see :class:`InstanceIdParser`).

      .. doctest::

	 >>> irt = ResourceIdParser('/example-2:bag/foo=3/in-words').parse()
	 >>> irt2 = InstanceIdParser('/example-2:bag/baz').parse()

      This method raises :exc:`InstanceValueError` if *iroute* isn't
      compatible with the schema, and :exc:`NonexistentInstance` if
      the target instance doesn't exist in the receiver's value.

      .. doctest::

	 >>> inst.goto(irt).value
	 'three'
	 >>> inst.goto(irt2)
	 Traceback (most recent call last):
	 ...
	 yangson.instance.NonexistentInstance: [/example-2:bag] member baz

   .. method:: peek(iroute: InstanceRoute) -> Optional[Value]

      Return the value of a target instance arbitrarily deep inside
      the receiver's value. The argument *iroute* is an
      :class:`InstanceRoute` (relative to the receiver) that
      identifies the target instance. ``None`` is returned if the
      target instance doesn't exist.

      .. doctest::

	 >>> inst.peek(irt)
	 'three'

      .. CAUTION:: This method doesn't create a new instance, so the
         access to the returned value should in general be read-only.
         Any modifications of the returned value also affect the
         receiver, as shown in the next example. This means that the
         persistence property for the receiver is lost.

      .. doctest::

	 >>> irt3 = ResourceIdParser('/example-2:bag/foo=3').parse()
	 >>> e2inst.peek(irt3)['in-words'] = 'tres'
	 >>> e2inst.value['example-2:bag']['foo'][1]['in-words'] # changed!
	 'tres'

   .. method:: validate(content: ContentType = ContentType.config) -> None

      Perform schema validation on the receiver's value. The value of
      the *content* argument belongs to the
      :data:`~.enumerations.ContentType` enumeration and specifies
      whether the receiver's value is to be validated as configuration
      (``Content.config``) or as both configuration and state data
      (``Content.all``).

      The method returns ``None`` if the validation succeeds,
      otherwise one of the following exceptions is raised:

      * :exc:`.schema.SchemaError` – if the value doesn't conform to
	the schema,
      * :exc:`.schema.SemanticError` – if the value violates a
	semantic constraint.

      .. doctest::

	 >>> inst.validate() # no output means OK
	 >>> badinst = bag.put_member('baz', 'ILLEGAL').top()
	 >>> badinst.validate()
	 Traceback (most recent call last):
	 ...
	 yangson.schema.SchemaError: [/example-2:bag/baz] invalid type: 'ILLEGAL'

      In the following example, member ``baz`` is not allowed because
      it is a conditional leaf and its **when** constraint evaluates
      to ``False``.

      .. doctest::

	 >>> e2foo6 = e2bag.member('foo').entry(0)
	 >>> bad2 = e2foo6.update(
	 ... {'number': 42, 'in-words': 'forty-two'}, raw=True).top()
	 >>> bad2.validate()
	 Traceback (most recent call last):
	 ...
	 yangson.schema.SchemaError: [/example-2:bag] not allowed: member 'baz'

   .. method:: add_defaults(ctype: ContentType = None) -> InstanceNode

      Return a new instance node that is a copy of the receiver
      extended with default values specified the data model. Only
      default values that are “in use” are added, see sections
      `7.6.1`_ and `7.7.2`_ in [RFC7950]_.

      The argument *ctype* restricts the content type of data nodes
      whose default values will be added. For example, setting it to
      ``ContentType.config`` means that only default values of
      configuration nodes will be added. If *ctype* is ``None``
      (default), a the content type of added defaults will be the same
      as the content type of the receiver.

      .. doctest::

	 >>> wd = inst.add_defaults()
	 >>> wd.value['example-2:bag']['baz']
	 Decimal('0E-7')

   .. automethod:: raw_value() -> RawValue

      .. doctest::

	 >>> wd.member('example-2:bag').member('baz').raw_value()
	 '0.0'

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

      .. doctest::

	 >>> foo.sibling('bar').json_pointer()
	 '/example-2:bag/bar'

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

      .. doctest::

	 >>> foo6.index
	 0

   .. attribute:: name

      The :term:`instance name` of an array entry is by definition the
      same as the instance name of the parent array.

      .. doctest::

	 >>> foo6.name
	 'foo'

   .. rubric:: Public Methods

   .. method:: previous() -> ArrayEntry

      Return an instance node corresponding to the previous entry in
      the parent array.

      This method raises :exc:`NonexistentInstance` if the receiver
      is the first entry of the parent array.

      .. doctest::

	 >>> foo3.previous().json_pointer()
	 '/example-2:bag/foo/0'
	 >>> foo6.previous()
	 Traceback (most recent call last):
	 ...
	 yangson.instance.NonexistentInstance: [/example-2:bag/foo/0] previous of first

   .. method:: next() -> ArrayEntry

      Return an instance node corresponding to the next entry in the
      parent array.

      This method raises :exc:`NonexistentInstance` if the receiver is
      the last entry of the parent array.

      .. doctest::

	 >>> foo6.next().json_pointer()
	 '/example-2:bag/foo/1'
	 >>> foo3.next()
	 Traceback (most recent call last):
	 ...
	 yangson.instance.NonexistentInstance: [/example-2:bag/foo/1] next of last

   .. method:: insert_before(value: Union[RawValue, Value], raw: bool \
	       = False) -> ArrayEntry

      Insert a new entry before the receiver and return an instance
      node corresponding to the new entry. The *value* argument
      specifies the value of the new entry, and the *raw* flag has to be
      set to ``True`` if *value* is a :term:`raw value`.

      .. doctest::

	 >>> foo4 = foo3.insert_before({'number': 4, 'in-words': 'four'}, raw=True)
	 >>> [en['number'] for en in foo4.up().value]
	 [6, 4, 3]

   .. method:: insert_after(value: Union[RawValue, Value], raw: bool \
	       = False) -> ArrayEntry

      Insert a new entry after the receiver and return an instance
      node corresponding to the new entry. The *value* argument
      specifies the value of the new entry, and the *raw* flag has to
      be set to ``True`` if *value* is a :term:`raw value`.

      .. doctest::

	 >>> foo5 = foo4.insert_after({'number': 5, 'in-words': 'five'}, raw=True)
	 >>> [en['number'] for en in foo5.up().value]
	 [6, 4, 5, 3]

.. autoclass:: InstanceRoute
   :show-inheritance:

   Instances are expected to be created by using either the class
   method :meth:`from_schema_route` or one of the parser classes
   :class:`ResourceIdParser` and :class:`InstanceIdParser`.

   .. rubric:: Public Methods

   .. automethod:: __str__

      .. doctest::

	 >>> str(irt)
	 '/example-2:bag/foo[number=3]/in-words'
	 >>> str(irt2)
	 '/example-2:bag/baz'

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

.. _4: https://tools.ietf.org/html/rfc7951#section-4
.. _6.1: https://tools.ietf.org/html/rfc7951#section-6.1
.. _7.6.1: https://tools.ietf.org/html/rfc7950#section-7.6.1
.. _7.7.2: https://tools.ietf.org/html/rfc7950#section-7.7.2
.. _8.3: https://tools.ietf.org/html/rfc6241#section-8.3
.. _9: https://tools.ietf.org/html/rfc7950#section-9
