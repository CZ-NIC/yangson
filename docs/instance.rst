**************************
 Persistent Data Instances
**************************

.. module:: yangson.instance
   :synopsis: Persistent data instances.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

The *Yangson* library represents instance data using an internal
tree-like structure that has the following useful properties:

* every node in the data data tree (except the root node) has access
  to its parent node,

* it is a `persistent structure`__ so that we can edit it and, at the
  same time, keep the original version intact.

The following classes and their method implement this functionality.

__ https://en.wikipedia.org/wiki/Persistent_data_structure

.. autoclass:: InstanceNode(value: :const:Value, parinst: Optional[InstanceNode], schema_node: DataNode, timestamp: datetime.datetime)

   Each instance variable is initialized from the constructor's
   parameter of the same name. The type alias :const:`Value`

   This class implements a *zipper* interface for JSON-like values
   pretty much along the lines of Gérard Huet's original
   paper [Hue97]_. Every :class:`Instance` contains

   * a *value*, as defined by the ``Value`` type alias;

   * a *crumb* that describes the neighborhood of the *value*.

   Inside a larger data structure, an :class:Instance represents
   “focus” on a particular element of the structure, where the *value*
   contains the element and its subtree, and *crumb* contains the rest
   of the structure: all ancestors and siblings of the focused
   element.

   The focus can be moved and values added, deleted and updated around
   the current focus by using the methods described below. Each of the
   methods returns a new :class:`Instance` that shares as much as
   possible of the entire data tree with other instances, but any
   modifications of an :class:`Instance` – if performed via the
   methods of this class – don't affect any other instances.

   Due to the heterogeneity of JSON-like values, the zipper interface is not
   as elegant as for trees: some operations are intended to work only
   with certain :class:`Instance` types. In the following subsections,
   the methods are classified according to the context for which they
   are designed.

   Section :ref:`sec-example` illustrates the zipper interface with
   several examples.

Methods for All Types of Instances
----------------------------------

   .. method:: goto(ii: InstanceIdentifier) -> Instance

      Return the instance inside the receiver's subtree identified by
      the instance identifier *ii* (see TODO). The path specified in
      *ii* is interpreted relative to the receiver.

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