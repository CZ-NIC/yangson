**************
Data Instances
**************

.. module:: yangson.instance
   :synopsis: Classes and methods for working with YANG data
	      instances.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

The standard library function :func:`json.load` parses JSON text into
convenient Python values – scalars, lists and dictionaries. For JSON-encoded
YANG data instances, we need to add a bit of extra processing and more
intelligent data structures. The reasons are as follows:

* In order to be able to generate entity tags for HTTP ``ETag``
  headers, we need a hash value for every scalar, array or
  object. Unlike scalars, though, we can't use the built-in
  :func:`hash` function to compute such a value for :class:`list` and
  :class:`dict` instances, so we need to *subclass* those two built-in
  classes and implement the :meth:`__hash__` method in the subclasses.

* We also need each array and object to keep the time stamp of its
  last modification (to be used in HTTP ``Last-Modified`` headers).

* All 64-bit numbers (of YANG types ``int64``, ``uint64`` and
  ``decimal64``) are encoded as JSON strings [Lho16]_, so we need to
  convert them to :class:`int` and :class:`decimal.decimal` values.

* From every value in the data tree, we need access to its parent
  array or object.

* Last but not least, the data tree needs to be a `persistent
  structure`__ so that we can edit it and, at the same time, keeping
  the original version intact.

The following classes and their method implement all this functionality.

__ https://en.wikipedia.org/wiki/Persistent_data_structure

This module defines a type alias representing an union of possible
types of instance values.

+-----+--------------------------------------------------------------+
|Alias|Type                                                          |
+=====+==============================================================+
|Value| Union[ScalarValue, :class:`ArrayValue`, :class:`ObjectValue`]|
+-----+--------------------------------------------------------------+


Instance Values
***************

.. class:: StructuredValue(ts:datetime.datetime=None)

   This class is an abstract superclass of both :class:`ArrayValue` and
   :class:`ObjectValue`.

   .. attribute:: last_modified

      This attribute contains a :class:`datetime.datetime` that
      records the date and time when the :class:StructuredValue
      instance was last modified.

   .. method:: time_stamp(ts: datetime.datetime = None) -> None

      Update the receiver's *last_modified* time stamp with the value
      *ts*. If *ts* is ``None``, use the current date and time.

   .. method:: __eq__(val: StructuredValue) -> bool

      Return ``True`` if the receiver and *val* are equality. Equality
      is based on their hash values (see below).

.. class:: ArrayValue(ts:datetime.datetime=None)

   This class is a subclass of both :class:`StructuredValue` and
   :class:`list`, and corresponds to a JSON array.

   .. method:: __hash__() -> int

      Return integer hash value. It is computed by converting the
      receiver to a :class:`tuple` and applying the :func:`hash`
      function to it.

.. class:: ObjectValue(ts:datetime.datetime=None)

   This class is a subclass of both :class:`StructuredValue` and
   :class:`dict`, and corresponds to a JSON object.

   All member names must be identifiers of YANG data nodes. Such a
   name must be qualified with the YANG module module name in which
   the node is defined if and only if either

   * the data node is the root of a data tree, i.e. has no parent data
     nodes, or
   * the data node's parent is defined in the same module.

   .. method:: __hash__() -> int

      Return integer hash value. It is computed by taking a sorted
      list of the receiver's items, converting it to a :class:`tuple`
      and applying the :func:`hash` function.

Persistent Instances
********************

.. class:: Instance(value: Value, crumb: Crumb)

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

TODO.
