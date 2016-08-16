**************************
 Persistent Data Instances
**************************

.. module:: yangson.instance
   :synopsis: Persistent data instances.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

.. testsetup::

   import json
   import os
   from yangson import DataModel
   os.chdir("examples/ex1")

The *Yangson* library represents instance data nodes using a
`persistent structure`__ so that we can edit it while keeping the
original version intact, and sharing as much data as possible between
both versions.

__ https://en.wikipedia.org/wiki/Persistent_data_structure

.. class:: InstanceNode(value, parinst, schema_node, timestamp)

   This abstract class for instance nodes has the following
   attributes:

   * *value* – scalar or structured value of the node,

   * *parinst* – parent instance node (``None`` for the root node),

   * *schema_node* – schema node corresponding to the instance,

   * *timestamp* – time of the last modification.

   Each instance variable is initialized from the constructor's
   parameter of the same name.

   In addition, :class:`InstanceNode` defines the following
   :class:`property` attributes:

   .. attribute:: qualName

      The :term:`qualified name` of the instance node. For the root
      node that has no name it is ``None``.

   .. attribute:: namespace

      The :term:`namespace identifier` of the instance node. For the root
      node that doesn't belong to any namespace it is ``None``.

   The :class:`InstanceNode` class implements a *zipper* interface for
   JSON-like values pretty much along the lines of Gérard Huet's
   original paper [Hue97]_. However, due to the heterogeneity of
   JSON-like values, the zipper interface is not as simple and elegant
   as for normal trees. In particular, sibling instance nodes have
   different representations depending on the class on the instance
   node, which can be either :class:`ObjectMember` (for nodes that are
   object members) or :class:`ArrayEntry` (for nodes that are array
   entries). The details can be found in the documentation of these
   classes below.

   The easiest way to create an :class:`InstanceNode` is to use the
   :meth:`DataModel.from_raw` method:

   .. doctest::

      >>> dm = DataModel.from_file("yang-library-ex2.json")
      >>> with open("example-data.json") as infile:
      ...   ri = json.load(infile)
      >>> inst = dm.from_raw(ri)
      >>> inst.value
      {'example-2:top': {'foo': [1, 2], 'bar': True}}

   Inside the larger structure of a data tree, an
   :class:`InstanceNode` represents “focus” on a particular node of
   the structure. The focus can be moved to a neighbour instance
   (parent, child, sibling) and the value of an instance node can be
   created, deleted and updated by using the methods described
   below. Each of the methods returns a new :class:`InstanceNode` that
   shares, as much as possible, portions of the surrounding data tree
   with the original instance node.  However, any modifications to the
   new instance node – if performed through the methods of the
   :class:`InstanceNode` class and its subclasses – leave other
   instance nodes intact.

   .. method:: validate(content = ContentType.config)

      Validate the receiver's value. The method returns ``None`` if
      the validation succeeds, otherwise and exception is raised:

      * :exc:yangson.schema.SchemaError – if the value doesn't conform
	to the schema,

      * :exc:yangson.schema.SemanticError – if the value violates a
	semantic constraint.

      .. doctest::

	 >>> inst.validate()
	 >>> inst.value['example-2:top']['baz'] = "ILLEGAL"
	 >>> inst.validate()
	 Traceback (most recent call last):
	 ...
	 yangson.schema.SchemaError: [/example-2:top] not allowed: member 'baz'

   .. method:: path()

      Return the JSON Pointer [RFC6901]_ of the receiver.

   .. method:: update(value)

      Return a new :class:`InstanceNode` that is a copy of the
      receiver with the value updated from the *value* argument.

      .. doctest::

	 >>> ri['example-2:top']['bar'] = False
	 >>> inst2 = inst.update_from_raw(ri)
	 >>> inst2.value
	 {'example-2:top': {'foo': [1, 2], 'bar': False}}
	 >>> inst.value
	 {'example-2:top': {'foo': [1, 2], 'bar': True}}

   .. method:: update_from_raw(rvalue)

      This method is similar to :meth:`update`, only the argument
      *rvalue* has to be a :term:`raw value`.

   .. method:: up()

      Move the focus to the parent instance node. If the receiver is
      the root of the data tree, exception :exc:`NonexistentInstance`
      is raised.

   .. method:: top()

      Move the focus to the root instance node.

   .. method:: goto(iroute)

      Move the focus to an :class:`InstanceNode` inside the receiver's
      value. The argument *iroute* is an
      :const:`yangson.typealiases.InstanceRoute` that identifies the
      new focus. The instance node that is the new focus is
      returned, or one of the following exceptions is raised:

      * :exc:`InstanceTypeError` – if the argument isn't compatible
	with the schema,
      * :exc:`NonexistentInstance` – if the new focus doesn't exist.

   .. method:: peek(ii: InstanceIdentifier) -> Value

      Return the value inside the receiver's value subtree identified by
      the instance identifier *ii* (see TODO). This
      method doesn't create a new instance, so the access to the
      returned value should in general be read-only, because
      modifications would destroy persistence properties.

   .. method:: update(newval: Value) -> Instance

      Return a new instance that is identical to the receiver, only
      its value is replaced with *newval*. The receiver does not
      change.

   .. method:: up() -> Instance

      Return the instance of the parent structure (object or
      array). Raises :exc:`NonexistentInstance` if called on a
      top-level instance.

   .. method:: top() -> Instance

      Return the instance of the top-level structure. This essentially
      means “zipping” the whole data tree.

   .. method:: is_top() -> bool

      Return ``True`` if the receiver is the top-level instance.

Methods for :class:`ObjectValue` Instances
------------------------------------------

   .. method:: member(name: QName) -> Instance

      Return the instance of the receiver's member specified by
      *name*. Raises :exc:`InstanceTypeError` if called on a
      non-object, and :exc:`NonexistentInstance` if a member of that
      name doesn't exist.

   .. method:: new_member(name: QName, value: Value) -> Instance

      Add a new member to the receiver object with the name and value
      specified in the method's parameters, and return the instance of
      the new member. As always, the receiver instance is not
      modified, so the new member only exists in the returned
      instance. The method raises :exc:`InstanceTypeError` if called
      on a non-object, and :exc:`DuplicateMember` if a member of that
      name already exists.

   .. method:: remove_member(name: QName) -> Instance

      Return a new object instance in which the receiver's member specified
      by *name* is removed. Raises :exc:`InstanceTypeError` if called on a
      non-object, and :exc:`NonexistentInstance` if a member of that
      name doesn't exist.

Methods for Object Member Instances
-----------------------------------

   .. method:: sibling(name: QName) -> Instance

      Return the instance of the sibling member specified by
      *name*. Raises :exc:`InstanceTypeError` if called on a
      non-member, and :exc:`NonexistentInstance` if a sibling member
      of that name doesn't exist.

Methods for :class:`ArrayValue` Instances
------------------------------------------

   .. method:: entry(index: int) -> Instance

      Return the instance of the receiver's entry specified by
      *index*. Raises :exc:`InstanceTypeError` if called on a
      non-array, and :exc:`NonexistentInstance` if an entry of that
      index doesn't exist.

   .. method:: remove_entry(index: int) -> Instance

      Return a new array instance in which the receiver's entry
      specified by *index* is removed. Raises :exc:`InstanceTypeError`
      if called on a non-array, and :exc:`NonexistentInstance` if an
      entry of that index doesn't exist.

   .. method:: first_entry() -> Instance

      Return the instance of the receiver's first entry. Raises
      :exc:`InstanceTypeError` if called on a non-array, and
      :exc:`NonexistentInstance` if the array is empty.

   .. method:: last_entry() -> Instance

      Return the instance of the receiver's last entry. Raises
      :exc:`InstanceTypeError` if called on a non-array, and
      :exc:`NonexistentInstance` if the array is empty.

   .. method:: look_up(keys: Dict[QName, ScalarValue]) -> Instance

      Return the instance of the receiver's entry specified by
      *keys*. The paremeter is a dictionary of key-value pairs that
      the selected entry matches. This method is intended to be used
      on YANG list instances. It raises :exc:`InstanceTypeError` if
      called on a non-array, and :exc:`NonexistentInstance` if the
      matching entry doesn't exist.

Methods for Array Entry Instances
---------------------------------

   .. method:: next() -> Instance

      Return the instance of the following entry. Raises
      :exc:`InstanceTypeError` if called on a non-entry, and
      :exc:`NonexistentInstance` if called on the last entry.

   .. method:: previous() -> Instance

      Return the instance of the preceding entry. Raises
      :exc:`InstanceTypeError` if called on a non-entry, and
      :exc:`NonexistentInstance` if called on the first entry.

   .. method:: insert_before(value: Value) -> Instance

      Insert *value* a new entry before the receiver and return the
      instance of the new entry. Raises :exc:`InstanceTypeError` if
      called on a non-entry.

   .. method:: insert_after(value: Value) -> Instance

      Insert *value* a new entry after the receiver and return the
      instance of the new entry. Raises :exc:`InstanceTypeError` if
      called on a non-entry.

Exceptions
**********

    .. exception:: NonexistentInstance

    This exception is raised if a method requests an instance that
    doesn't exist.

    .. exception:: DuplicateMember

    This exception is raised if a method tries to create an object
    member with a name that already exists.

    .. exception:: InstanceTypeError

    This exception is raised if a method is called with a receiver of
    a wrong type.

.. _sec-example:

Example
*******

Consider this very simple YANG module::

  module test {
    namespace "http://example.com/test";
    prefix t;

    container root {
      leaf foo {
        type boolean;
      }
      leaf-list bar {
        type uint8;
      }
    }
  }

In order to use this YANG module with the *Yangson* library, we need to
write a *YANG library* specification [RFC7895]_::

  {
    "ietf-yang-library:modules-state": {
      "module-set-id": "",
      "module": [
        {
          "name": "test",
          "revision": "",
          "namespace": "http://example.com/test",
          "conformance-type": "implement"
        }
      ]
    }
  }

The only useful information that this JSON snippet provides is that
our data model consists of a single YANG module, namely
``test``. Given that it is about as long as than the YANG module
itself, it looks like a serious overkill, but real-life data models
typically comprise a number of modules in various roles, support
different features, etc., and YANG library info then makes much more
sense. Anyway, we can now load our simple data model::

  >>> import json
  >>> from yangson import DataModel
  >>> module_dir = "examples" # where test.yang lives
  >>> ylfile = open("examples/yang-library.json")
  >>> dm = DataModel.from_yang_library(ylfile.read(), module_dir)

Here is a JSON document that happens to be a valid instance of the
data model::

  >>> data = """{"test:root": {"foo": true, "bar": [1, 2]}}"""

We parse the JSON data with the standard library function
:func:`json.loads` and create an :class:`Instance` from it right away::

  >>> inst = dm.from_raw(json.loads(data))

Attribute :attr:`inst.value` now holds the complete data::

  >>> inst.value
  {'test:root': {'foo': True, 'bar': [1, 2]}}

We can now use the methods in the :class:`Instance` class to “unzip”
the structure and focus on an arbitrary value inside it, for example
the ``foo`` boolean value:

  >>> foo = inst.member("test:root").member("foo")
  >>> foo.value
  True

We can change this value and get a new :class:`Instance` with the
modified value, while ``foo`` still keeps the original value::

  >>> mfoo = foo.update(False)
  >>> mfoo.value
  False
  >>> foo.value
  True

So far it doesn't look very exciting, but the important point here is
that both ``foo`` and ``mfoo`` keep complete information about the
ancestor structures, and in fact share most of them. From ``minst`` we
can easily get back to the top and see the whole structure again,
but with the modified value of the ``foo`` member::

  >>> minst = mfoo.top()
  >>> minst.value
  {'test:root': {'foo': False, 'bar': [1, 2]}}

However, the ``inst`` variable still points to the data structure that
we started with, it wasn't affected at all::

  >>> inst.value
  {'test:root': {'foo': True, 'bar': [1, 2]}}

But the nicest thing is that ``inst`` and ``minst`` still *share* the
parts of the structure that we didn't touch. How can we see this?
Easy. We just use the standard Python way for accessing structure
elements and modify the left array entry in the ``bar`` member of ``inst``::

  >>> inst.value["test:root"]["bar"][0] = 111
  >>> inst.value
  {'test:root': {'foo': True, 'bar': [111, 2]}}
  >>> minst.value
  {'test:root': {'foo': False, 'bar': [111, 2]}}

Sure enough, the value changed not only in ``inst`` but also in
``minst``, so the array is indeed shared! If we use the
:class:`Instance` methods for changing the other entry of the same
array, the result will be quite different::

  >>> bar = inst.member("test:root").member("bar").entry(1)
  >>> bar.value
  2
  >>> minst2 = bar.update(222).top()
  >>> minst2.value
  {'test:root': {'bar': [111, 222], 'foo': True}}
  >>> inst.value
  {'test:root': {'foo': True, 'bar': [111, 2]}}
  >>> minst.value
  {'test:root': {'foo': False, 'bar': [111, 2]}}

The new :class:`Instance` ``minst2`` contains the modified value, but
neither ``inst`` nor ``minst`` changed.

The syntax of an instance identifier is given by the production rule
``instance-identifier`` in `sec. 14`_ of [Bjo16]_.

The syntax of a resource identifier is given by the production rule
``api-path`` in `sec. 3.5.1.1`_ of [BBW16]_.

.. _sec. 14: https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis-12#section-14
.. _sec. 3.5.1.1: https://tools.ietf.org/html/draft-ietf-netconf-restconf-13#section-3.5.1.1
