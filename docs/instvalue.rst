***********************************
Structured Values of Instance Nodes
***********************************

.. module:: yangson.instvalue
   :synopsis: Structured instance node values.

.. testsetup::

   import time
   from yangson.instvalue import ArrayValue, ObjectValue

The *instvalue* module implements the following classes:

* :class:`StructuredValue`: Abstract class for “cooked” structured
  values of an instance node.
* :class:`ArrayValue`: Cooked array value of an instance node.
* :class:`ObjectValue`: Cooked object value of an instance node.

The standard Python library function :func:`json.load` parses JSON
arrays and objects into native data structures – lists and
dictionaries, respectively. In order to use them effectively in the
*Yangson* library, we need to “cook” them first, i.e. extend these
data structures with additional attributs and methods:

* In order to be able to generate entity tags for HTTP ``ETag``
  headers, we need to be able to compute a hash value for arrays and
  objects. Standard Python lists and dictionaries do not implement the
  :meth:`__hash__` method.

* For each array and object, we also need to record the time stamp of
  its last modification (to be used in HTTP ``Last-Modified``
  headers).

.. rubric:: Type Aliases

.. data:: Value

   This type alias covers all possible types of cooked values of an
   instance node, both scalar and structured.

.. data:: EntryValue

   This type alias covers possible types of values of a list of
   leaf-list entry.

.. class:: StructuredValue(ts: datetime.datetime = None)

   This class is an abstract superclass for structured values of
   instance nodes. The constructor argument *ts* contains the initial
   value of the *timestamp* attribute. If it is ``None``, then
   current time is used.

   .. rubric:: Instance Attributes

   .. attribute:: timestamp

      This attribute contains a :class:`datetime.datetime` that
      records the date and time of the last modification.

   .. rubric:: Public Methods

   .. method:: copy() -> StructuredValue

      Return a shallow copy of the receiver with :attr:`last_modified`
      set to current time.

   .. method:: __setitem__(self, key: InstanceKey, value: Value) -> None

      Set an array entry or object member *key* to *value* and update
      receiver's timestamp to the current time.

   .. method:: __eq__(val: StructuredValue) -> bool

      Return ``True`` if the receiver is equal to *val*. The equality
      test is based on their hash values.

   .. automethod:: __hash__

      .. CAUTION:: The hash values are guaranteed to be stable only
         within the same Python interpreter process. This is because hash
         values of Python strings change from one invocation to another.

.. autoclass:: ArrayValue(val: List[EntryValue] = [], ts: datetime.datetime = None)
   :show-inheritance:

   The additional constructor argument *val* contains a list that the
   :class:`ArrayValue` instance will hold.

   .. doctest::

      >>> ary = ArrayValue([1, 2, 3])
      >>> time.sleep(0.1)
      >>> ac = ary.copy()
      >>> ary.timestamp < ac.timestamp
      True
      >>> ary == ac
      True
      >>> ac[2] = 4
      >>> ary == ac
      False

.. autoclass:: ObjectValue(val: Dict[InstanceName, Value] = {}, ts: datetime.datetime = None)
   :show-inheritance:

   The additional constructor argument *val* contains a dictionary
   that the :class:`ObjectValue` instance will hold.

   .. doctest::

      >>> obj = ObjectValue({'one': 1, 'two': 2})
      >>> time.sleep(0.1)
      >>> oc = obj.copy()
      >>> obj.timestamp < oc.timestamp
      True
      >>> obj == oc
      True
      >>> oc['three'] = 3
      >>> obj == oc
      False
