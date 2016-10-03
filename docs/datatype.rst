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
   >>> bits_t = dm.get_data_node('/example-5-a:bits-leaf').type
   >>> boolean_t = dm.get_data_node('/example-5-a:boolean-leaf').type
   >>> decimal64_t = dm.get_data_node('/example-5-a:decimal64-leaf').type
   >>> empty_t = dm.get_data_node('/example-5-a:empty-leaf').type
   >>> enumeration_t = dm.get_data_node('/example-5-a:enumeration-leaf').type
   >>> identityref_t = dm.get_data_node('/example-5-a:identityref-leaf').type
   >>> string_t = dm.get_data_node('/example-5-a:string-leaf').type


.. class:: DataType(mid: ModuleId)

   This is the abstract superclass for all classes representing YANG
   data types. The methods described in this class comprise common API
   for all type, some subclasses then introduce type-specific methods.

   The constructor argument *mid* is the value for the
   :attr:`module_id` instance attribute.

   .. rubric:: Instance Attributes

   .. attribute:: module_id

      Identifier of the module in the context of which the type
      definition and restrictions are to be interpreted.

      .. doctest::

	 >>> string_t.module_id
	 ('example-5-a', '')

   .. attribute:: default

      Default value of the type that may be defined by using
      the **default** statement inside a **typedef**.

      .. doctest::

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

   .. method:: to_raw(val: ScalarValue) -> RawScalar

      Convert a :term:`cooked value` *val* to a :term:`raw value`
      according to the rules of the receiver data type.. This method
      is inverse to :meth:`from_raw`, and the result can be encoded
      into JSON text by using the standard library functions
      :func:`json.dump` and :func:`json.dumps`.

      This method raises :exc:`YangTypeError` if the value in *val*
      cannot be converted.

      .. doctest::

	 >>> from test import *
	 >>> bits_t.to_raw(('dos', 'tres'))
	 'dos tres'
	 >>> bits_t.to_raw((2,3))
	 Traceback (most recent call last):
	 ...
	 yangson.datatype.YangTypeError: value (2, 3)

   .. method:: parse_value(text: str) -> ScalarValue

      Return a value of receiver's type parsed from the string *text*.

      This method raises :exc:`YangTypeError` if the string in *text*
      cannot be parsed into a valid value of receiver's type.

      .. doctest::

	 >>> boolean_t.parse_value("true")
	 True
	 >>> boolean_t.parse_value(1)
	 Traceback (most recent call last):
	 ...
	 yangson.datatype.YangTypeError: value 1

   .. method:: canonical_string(val: ScalarValue) -> str

      Return canonical string representations of *val* as defined for
      the receiver type. See sec. `9.1`_ in [RFC7950]_ for more
      information about canonical forms.

      This method raises :exc:`YangTypeError` if *val* is not a valid
      value of receiver's type.

      This method is a partial inverse of :meth:`parse_value`, the
      latter method is however able to parse non-canonical string
      forms, as shown in the next example.

      .. doctest::

	 >>> e = decimal64_t.parse_value("002.718281")
	 >>> e
	 Decimal('2.7183')
	 >>> decimal64_t.canonical_string(e)
	 '2.7183'

   .. method:: from_yang(text: str, mid: ModuleId) -> ScalarValue

      Return a value of receiver's type parsed from a string that may
      appear in the module specified by :term:`module identifier`
      *mid*.

      This method raises :exc:`YangTypeError` if the string in *text*
      cannot be parsed into a valid value of receiver's type in the
      context of module *mid*.

      This method is useful, e.g., for parsing arguments of the **default**
      statement.

      .. doctest::

	 >>> identityref_t.from_yang('ex5b:derived-identity', ('example-5-a', ''))
	 ('derived-identity', 'example-5-b')

   .. method:: contains(val: ScalarValue) -> bool

      Return ``True`` if the argument *val* contains a valid value of
      the receiver type, otherwise return ``False``.

      .. doctest::

	 >>> enumeration_t.contains("Dopey")
	 True
	 >>> enumeration_t.contains("SnowWhite")
	 False

.. class:: EmptyType

   This class is a subclass of :class:`DataType`, and represents YANG
   **empty** type. It is implemented as a singleton class because the
   **empty** type cannot be restricted.

.. class:: BitsType

   This class is a subclass of :class:`DataType`, and represents YANG
   **bits** type.

   A :term:`cooked value` of this type is a tuple of strings – names
   of the bits that are set.

   See documentation of :meth:`DataType.from_raw` for an example.

.. class:: BooleanType

   This class is a subclass of :class:`DataType`, and represents YANG
   **boolean** type.

   Both :term:`raw value` and :term:`cooked value` of this type is a
   Python :class:`bool` value.

   See documentation of :meth:`DataType.parse_value` for an example.

.. class:: StringType

   This class is a subclass of :class:`DataType`, and represents YANG
   **string** type.

   .. rubric:: Instance Attributes

   .. attribute:: length

      Specification of restrictions on the string length. It is a list
      of two-element lists specifying the lower and upper bounds for
      the string length. This attribute is compiled from the
      **length** type restriction.

      .. doctest::

	 >>> string_t.length
	 [[2, 4]]
	 >>> string_t.contains('xxxxy')  # too long
	 False

   .. attribute:: patterns

      List of regular expression patterns with which the type is
      restricted (those that do not have the **invert-match**
      modifier). Each entry is a compiled Python regular expression
      pattern.

      .. doctest::

	 >>> string_t.patterns
	 [re.compile('^x*y$')]
	 >>> string_t.contains('xxxy')
	 True
	 >>> string_t.contains('xxyy')  # pattern doesn't match
	 False
	 
   .. attribute:: invert_patterns

      List of regular expression patterns that have the
      **invert-match** modifier, with which the type is
      restricted. Each entry is a compiled Python regular expression
      pattern.

.. class:: BinaryType

   This class is a subclass of :class:`StrindType`, and represents YANG
   **binary** type.

   The :term:`cooked value` is a Python :class:`bytes` object, whereas
   the :term:`raw value` is the same bytestring encoded in Base64 (see
   sec. `4`_ in [RFC4648]_).

.. _4: https://tools.ietf.org/html/rfc4648#section-4
.. _7.3: https://tools.ietf.org/html/rfc7950#section-7.3
.. _9.1: https://tools.ietf.org/html/rfc7950#section-9.1
