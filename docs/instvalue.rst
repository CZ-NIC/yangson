****************
 Instance Values
****************

.. module:: yangson.instvalue
   :synopsis: Cooked instance values.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

.. autodata:: Value

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

This module defines a type alias representing an union of possible
types of instance values.

.. class:: StructuredValue

   This class is an abstract superclass of both :class:`ArrayValue` and
   :class:`ObjectValue`. Its constructor method has one argument, *ts*
   (:class:`datetime.datetime`) that is used to set the
   *last_modified* attribute.

   .. attribute:: last_modified

      This attribute contains a :class:`datetime.datetime` that
      records the date and time when the :class:StructuredValue
      instance was last modified.

   .. automethod:: time_stamp

   .. automethod:: __eq__

.. class:: ArrayValue

   This class is a subclass of both :class:`StructuredValue` and
   :class:`list`, and corresponds to a JSON array.

   .. automethod:: __hash__

.. class:: ObjectValue

   This class is a subclass of both :class:`StructuredValue` and
   :class:`dict`, and corresponds to a JSON object.

   All member names must be identifiers of YANG data nodes. Such a
   name must be qualified with the YANG module module name in which
   the node is defined if and only if either

   * the data node is the root of a data tree, i.e. has no parent data
     nodes, or
   * the data node's parent is defined in the same module.

   .. automethod:: __hash__
