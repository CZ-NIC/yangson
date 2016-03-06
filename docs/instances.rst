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

Instance Values
===============

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
====================

.. class:: Instance(value: Value, crumb: Crumb)

   .. method:: goto(ii: InstanceIdentifier) -> Instance

   .. method:: peek(ii: InstanceIdentifier) -> Value

   .. method:: update(newval: Value) -> Instance

   .. method:: up() -> Instance

   .. method:: top() -> Instance

   .. method:: is_top() -> Instance

   .. method:: member(name: QName) -> Instance

   .. method:: new_member(name: QName, value: Value) -> Instance

   .. method:: () -> Instance

   .. method:: () -> Instance

   .. method:: () -> Instance

   .. method:: () -> Instance

   .. method:: () -> Instance

   .. method:: () -> Instance
