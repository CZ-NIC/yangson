==========
Data Types
==========

.. module:: yangson.datatype
   :synopsis: Classes representing YANG data types

.. testsetup::

   import os
   from yangson import DataModel
   os.chdir("examples/ex5")

.. testcleanup::

   os.chdir("../..")
   del DataModel._instances[DataModel]

The *datatype* module defines the following classes:

* :class:`BitsType`: YANG **bits** type.
* :class:`BinaryType`: YANG **binary** type.
* :class:`BooleanType`: YANG **boolean** type.
* :class:`DataType`: Abstract class for data types.
* :class:`Decimal64Type`: YANG **decimal64** type.
* :class:`EmptyType`: YANG **empty** type.
* :class:`EnumerationType`: YANG **enumeration** type.
* :class:`LeafrefType`: YANG **leafref** type.
* :class:`LinkType`: Abstract class for data types representing links.
* :class:`InstanceIdentifierType`: YANG **instance-identifier** type.
* :class:`IdentityrefType`: YANG **identityref** type.
* :class:`IntegralType`: Abstract class for integral types.
* :class:`Int8Type`: YANG **int8** type.
* :class:`Int16Type`: YANG **int16** type.
* :class:`Int32Type`: YANG **int32** type.
* :class:`Int64Type`: YANG **int64** type.
* :class:`NumericType`: Abstract class for numeric types.
* :class:`StringType`: YANG **string** type.
* :class:`Uint8Type`: YANG **uint8** type.
* :class:`Uint16Type`: YANG **uint16** type.
* :class:`Uint32Type`: YANG **uint32** type.
* :class:`Uint64Type`: YANG **uint64** type.
* :class:`UnionType`: YANG **union** type.

The module also defines the following exceptions:

* :exc:`YangTypeError`: A scalar value is of incorrect type.

YANG provides a selection of built-in data types, and also supports
defining new types that are derived from existing types (built-in or
derived) by specifying the base type and zero or more restrictions.
See sec. `7.3`_ of [RFC7950]_ for details.

*Yangson* library resolves all derived types so that the base type
corresponds to a Python class and restrictions are represented as
values of appropriate instance attributes. Instances of subclasses
of :class:`DataType` typically appear as values
of :attr:`~.TerminalNode.type` attribute that is common to
all :class:`~.schema.TerminalNode` instances.

.. doctest::

   >>> dm = DataModel.from_file('yang-library-ex5.json',
   ... mod_path=[".", "../../../examples/ietf"])
   >>> bits_t = dm.get_data_node('/example-5:bits-leaf').type
   >>> empty_t = dm.get_data_node('/example-5:empty-leaf').type
   >>> enumeration_t = dm.get_data_node('/example-5:enumeration-leaf').type
   >>> string_t = dm.get_data_node('/example-5:string-leaf').type


.. class:: DataType(mid: ModuleId)

   This is the abstract superclass for all classes representing YANG
   data types. The constructor argument *mid* is the value for
   the :attr:`module_id` instance attribute.

   .. rubric:: Instance Attributes

   .. attribute:: module_id

      Identifier of the module in the context of which the type
      definition and restrictions are to be interpreted.

      .. doctest::

	 >>> string_t.module_id
	 ('example-5', '')

   .. attribute:: default

      Default value of the type that may be defined by using
      the **default** statement inside a **typedef**.

      ..doctest::

      >>> string_t.default
      'xxy'

   .. rubric:: Public Methods

   .. method:: from_raw(raw: RawScalar) -> ScalarValue

      Convert a :term:`raw value` *raw* to a :term:`cooked value`
      according to the rules of the receiver data type.

      This method raises :exc:`YangTypeError` if the value in *raw*
      cannot be converted.

      .. doctest::

	 >>> bits_t.from_raw('dos tres')
	 ('dos', 'tres')
	 >>> bits_t.from_raw('tres cuatro')
	 Traceback (most recent call last):
	 ...
	 yangson.datatype.YangTypeError: value 'tres cuatro'

.. _7.3: https://tools.ietf.org/html/rfc7950#section-7.3
