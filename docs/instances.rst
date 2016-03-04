**************
Data Instances
**************

In-memory representation of instance data is implemented using the :class:`Instance` class:

.. class:: Instance(value: Value, crumb: Crumb)

Each data instance has two slots:

* *value* is a JSON-like value containing the instance data (configuration, state data etc.)
* *crumb* makes each instance into a `persistent structure`__ that allows for editing the data while keeping the original version intact.

__ https://en.wikipedia.org/wiki/Persistent_data_structure

Instance Values
===============

.. class:: StructuredValue(ts:datetime.datetime=None) -> None:

   This class is an abstract superclass of both :class:ArrayValue and
   :class:ObjectValue. It implements an equality test based on the
   hash value.

   .. attribute::last_modified

      This attribute contains a :class:`datetime.datetime` that
      records the date and time when the :class:StructuredValue
      instance was last modified.

   .. method::time_stamp(ts:datetime.datetime=None)

      Update the receiver's *last_modified* time stamp with the value
      *ts*. If *ts* is ``None``, use the current date and time.

.. class:: ArrayValue(ts:datetime.datetime=None)

   This class is a subclass of both :class:StructuredValue and
   :class:list, and corresponds to a JSON array.

.. class:: ObjectValue(ts:datetime.datetime=None)

   This class is a subclass of both :class:StructuredValue and
   :class:dict, and corresponds to a JSON object.

Both :class:`ArrayValue` and :class:`ObjectValue` implement the
:meth:`__hash__` method, so their instances can be used as arguments of
the :func:hash function.

Instance values are essentially the same as values returned by
:func:`json.load` function, with the following exceptions.
