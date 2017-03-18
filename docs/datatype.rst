**********
Data Types
**********


.. module:: yangson.datatype
   :synopsis: Classes representing YANG data types

.. testsetup::

   import os
   from yangson import DataModel
   from yangson.schemadata import SchemaContext
   os.chdir("examples/ex5")

.. testcleanup::

   os.chdir("../..")

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

Doctest__ snippets for this module use the data model from :ref:`sec-ex5`.

__ http://www.sphinx-doc.org/en/stable/ext/doctest.html

.. doctest::

   >>> dm = DataModel.from_file('yang-library-ex5.json',
   ... mod_path=[".", "../../../yang-modules/ietf"])
   >>> binary_t = dm.get_data_node('/example-5-a:binary-leaf').type
   >>> bits_t = dm.get_data_node('/example-5-a:bits-leaf').type
   >>> boolean_t = dm.get_data_node('/example-5-a:boolean-leaf').type
   >>> decimal64_t = dm.get_data_node('/example-5-a:decimal64-leaf').type
   >>> empty_t = dm.get_data_node('/example-5-a:empty-leaf').type
   >>> enumeration_t = dm.get_data_node('/example-5-a:enumeration-leaf').type
   >>> identityref_t = dm.get_data_node('/example-5-a:identityref-leaf').type
   >>> ii_t = dm.get_data_node('/example-5-a:instance-identifier-leaf').type
   >>> leafref_t = dm.get_data_node('/example-5-a:leafref-leaf').type
   >>> string_t = dm.get_data_node('/example-5-a:string-leaf').type
   >>> union_t = dm.get_data_node('/example-5-a:union-leaf').type

YANG provides a selection of built-in data types, and also supports
defining new types that are derived from existing types (built-in or
derived) by specifying the base type and zero or more restrictions.
See sec. `7.3`_ of [RFC7950]_ for details.

*Yangson* library resolves all derived types so that the base type
corresponds to a Python class and restrictions are represented as
values of appropriate instance attributes. Instances of subclasses
of :class:`DataType` typically appear as values
of :attr:`~.TerminalNode.type` attribute that is common to
all :class:`~.schemanode.TerminalNode` instances.

.. class:: DataType(sctx: SchemaContext, name: YangIdentifier)

   This is the abstract superclass for all classes representing YANG
   data types. The methods described in this class comprise common API
   for all type, some subclasses then introduce type-specific methods.

   The constructor arguments *sctx* and *name* initialize values of the
   instance attributes :attr:`sctx` and :attr:`name`, respectively.

   .. rubric:: Instance Attributes

   .. attribute:: sctx

      :class:`~.schemadata.SchemaContext` in which the type definition
      and restrictions are to be interpreted.

      .. doctest::

	 >>> string_t.sctx.text_mid
	 ('example-5-a', '')

   .. attribute:: default

      Default value of the type that may be defined by using
      the **default** statement inside a **typedef**.

      .. doctest::

	 >>> string_t.default
	 'xxy'

   .. attribute:: name

      Name of the type if it is derived, otherwise ``None``.

      .. doctest::

	 >>> string_t.name
	 'my-string'
	 >>> boolean_t.name is None
	 True

   .. attribute:: error_tag

      This attribute records the error tag of the most recent type
      validation that failed.

   .. attribute:: error_message

      This attribute records the error message specified for the most
      recent type validation that failed.

      .. doctest::

	 >>> 'abc' in string_t
	 False
	 >>> string_t.error_tag
	 'invalid-type'
	 >>> string_t.error_message
	 'xes and y'

   .. rubric:: Public Methods

   .. method:: __contains__(val: ScalarValue) -> bool

      Return ``True`` if the argument *val* contains a valid value of
      the receiver type, otherwise return ``False``.

      This method enables the Python operators ``in`` and ``not in``
      for use with types.

      .. doctest::

	 >>> "Dopey" in enumeration_t
	 True
	 >>> "SnowWhite" not in enumeration_t
	 True

   .. automethod:: __str__

   .. method:: from_raw(raw: RawScalar) -> Optional[ScalarValue]

      Return :term:`cooked value` converted from a :term:`raw value`
      *raw* according to the rules of the receiver data type, or
      ``None`` if the value in *raw* cannot be converted.

      .. doctest::

	 >>> bits_t.from_raw('dos tres')
	 ('dos', 'tres')
	 >>> bits_t.from_raw(0) is None
	 True

   .. method:: to_raw(val: ScalarValue) -> Optional[RawScalar]

      Return a :term:`raw value` converted from a :term:`cooked value`
      *val* according to the rules of the receiver data type, or
      ``None`` if the conversion fails. This method is essentially
      inverse to :meth:`from_raw`. The returned value can be encoded
      into JSON text by using the standard library functions
      :func:`json.dump` and :func:`json.dumps`.

      .. doctest::

	 >>> from test import *
	 >>> bits_t.to_raw(('dos', 'tres'))
	 'dos tres'
	 >>> bits_t.to_raw((2,3)) is None
	 True

   .. method:: parse_value(text: str) -> Optional[ScalarValue]

      Return a value of receiver's type parsed from the argument
      *text*, or ``None`` if parsing fails.

      .. doctest::

	 >>> boolean_t.parse_value('true')
	 True
	 >>> boolean_t.parse_value('foo') is None
	 True

   .. method:: canonical_string(val: ScalarValue) -> Optional[str]

      Return canonical string representation of *val* as defined for
      the receiver type, or ``None`` if *val* is not a valid value of
      the receiver type. See sec. `9.1`_ in [RFC7950]_ for more
      information about canonical forms.

      This method is a partial inverse of :meth:`parse_value`, the
      latter method is however able to parse non-canonical string
      forms, as shown in the next example.

      .. doctest::

	 >>> e = decimal64_t.parse_value("002.718281")
	 >>> e
	 Decimal('2.7183')
	 >>> decimal64_t.canonical_string(e)
	 '2.7183'

   .. method:: from_yang(text: str, sctx: SchemaContext) -> Optional[ScalarValue]

      Return a value of receiver's type parsed from a string appearing
      in a YANG module, or ``None`` if parsing fails. The *sctx*
      argument is the :class:`~.schemadata.SchemaContext` in which
      *text* is interpreted as a scalar value.

      This method is mainly useful for parsing arguments of the
      **default** statement.

      .. doctest::

	 >>> sctx = SchemaContext(dm.schema_data, 'example-5-a', ('example-5-a', ''))
	 >>> identityref_t.from_yang('ex5b:derived-identity', sctx)
	 ('derived-identity', 'example-5-b')

   .. method:: yang_type() -> YangIdentifier

      Return YANG name of the receiver.

      .. doctest::

	 >>> ii_t.yang_type()
	 'instance-identifier'

.. class:: EmptyType

   This class is a subclass of :class:`DataType`, and represents YANG
   **empty** type. It is implemented as a singleton class because the
   **empty** type cannot be restricted.

.. class:: BitsType

   This class is a subclass of :class:`DataType`, and represents YANG
   **bits** type.

   A :term:`cooked value` of this type is a tuple of strings – names
   of the bits that are set.

   See documentation of :meth:`~DataType.from_raw` for an example.

   .. rubric:: Instance Attributes

   .. attribute:: bit

      A dictionary that maps bit labels as defined by **bit**
      statements to bit positions. The position are either defined
      explicitly via the **position** statement, or assigned
      automatically – see sec. `9.7.4.2`_ in [RFC7950]_ for details.

      .. doctest::

	 >>> bits_t.bit['un']
	 1

.. class:: BooleanType

   This class is a subclass of :class:`DataType`, and represents YANG
   **boolean** type.

   Both :term:`raw value` and :term:`cooked value` of this type is a
   Python :class:`bool` value.

   See documentation of :meth:`~DataType.parse_value` for an example.

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

	 >>> string_t.length.intervals
	 [[2, 4]]
	 >>> 'xxxxy' in string_t  # too long
	 False

   .. attribute:: patterns

      List of regular expression patterns with which the type is
      restricted (those that do not have the **invert-match**
      modifier). Each entry is a compiled Python regular expression
      pattern.

      .. doctest::

	 >>> string_t.patterns[0].regex
	 re.compile('^x*y$')
	 >>> 'xxxy' in string_t
	 True
	 >>> 'xxyy' not in string_t  # pattern doesn't match
	 True
	 
   .. attribute:: invert_patterns

      List of regular expression patterns that have the
      **invert-match** modifier, with which the type is
      restricted. Each entry is a compiled Python regular expression
      pattern.

.. class:: BinaryType

   This class is a subclass of :class:`StringType`, and represents YANG
   **binary** type.

   The :term:`cooked value` is a Python :class:`bytes` object.

   .. doctest::

      >>> binary_t.to_raw(b'\xFF\xFE')
      '//4='

.. class:: EnumerationType

   This class is a subclass of :class:`DataType`, and represents YANG
   **enumeration** type.

   Both :term:`raw value` and :term:`cooked value` of this type is a
   string, and it must must be one of the names specified in the type's
   definition via the **enum** statement.

   See documentation of :meth:`~DataType.contains` for an example.

   .. rubric:: Instance Attributes

   .. attribute:: enum

      A dictionary that maps assigned enum names to their values as
      defined via the **value** statement or assigned automatically.

      .. doctest::

	 >>> enumeration_t.enum['Happy']
	 4

.. class:: LinkType

   This is an abstract superclass for types that refer to other
   instance nodes (**leafref** and **instance-identifier**). It is a
   subclass of :class:`DataType`.

   .. rubric:: Instance Attributes

   .. attribute:: require_instance

      Boolean flag that indicates whether an instance node being
      referred to is required to exist. This property is set by the
      **require-instance** statement in type's definition, see
      sec. `9.9.3`_ in [RFC7950]_.

      .. doctest::

	 >>> leafref_t.require_instance
	 True

.. class:: LeafrefType

   This class is a subclass of :class:`LinkType`, and represents YANG
   **leafref** type.

   The type of a :term:`cooked value` of this type is dictated by the
   type of the leaf node that is being referred to via the **path**
   statement.

   .. rubric:: Instance Attributes

   .. attribute:: path

      An :class:`~.xpathast.Expr` object (XPath abstract syntax tree)
      parsed from the argument of the **path** statement.

      .. doctest::

	 >>> print(leafref_t.path, end='')
	 LocationPath
	   Root
	   Step (child ('string-leaf', None))

   .. attribute:: ref_type

      Type of the leaf being referred to.

      .. doctest::

	 >>> type(leafref_t.ref_type)
	 <class 'yangson.datatype.StringType'>
	 >>> 'abc' in leafref_t
	 False

.. class:: InstanceIdentifierType

   This class is a subclass of :class:`LinkType`, and represents YANG
   **instance-identifier** type.

   A :term:`cooked value` of this type is an
   :class:`~.instance.InstanceRoute` object parsed from a :term:`raw
   value` as defined in sec. `9.13`_ of [RFC7950]_.

   .. doctest::

      >>> type(ii_t.from_raw('/example-5-a:boolean-leaf'))
      <class 'yangson.instance.InstanceRoute'>
      >>> str(ii_t.from_raw('/example-5-a:boolean-leaf'))
      '/example-5-a:boolean-leaf'

.. class:: IdentityrefType

   This class is a subclass of :class:`DataType`, and represents YANG
   **identityref** type.

   A :term:`cooked value` of this type is a :term:`qualified name` of
   an identity defined by the data model.

   See documentation of :meth:`~DataType.from_yang` for an example.

   .. rubric:: Instance Attributes

   .. attribute:: bases

      List of :term:`qualified name`\ s of identities that are defined
      as bases for this type via the **base** statement.

      .. doctest::

	 >>> identityref_t.bases
	 [('base-identity', 'example-5-b')]

.. class:: NumericType

   This class is an abstract superclass for all classes representing
   numeric types. It is subclass of :class:`DataType`.

.. class:: Decimal64Type

   This class is a subclass of :class:`NumericType`, and represents
   YANG **decimal64** type.

   A :term:`cooked value` of this type is a :class:`decimal.Decimal` number.

   See documentation of :meth:`~DataType.canonical_string` for an example.

.. class:: IntegralType

   This class is an abstract superclass for all classes representing
   integral numbers. It is subclass of :class:`NumericType`, and represents
   YANG **integral** type.

   Python unlimited precision integers (:class:`int`) are use for
   :term:`cooked value`\ s of all integral types, and restrictions on
   ranges are enforced explicitly for specific types such as
   **uint32**.

.. class:: Int8Type

   This class is a subclass of :class:`IntegralType`, and represents
   YANG **int8** type.

.. class:: Int16Type

   This class is a subclass of :class:`IntegralType`, and represents
   YANG **int16** type.

.. class:: Int32Type

   This class is a subclass of :class:`IntegralType`, and represents
   YANG **int32** type.

.. class:: Int64Type

   This class is a subclass of :class:`IntegralType`, and represents
   YANG **int64** type.

.. class:: Uint8Type

   This class is a subclass of :class:`IntegralType`, and represents
   YANG **uint8** type.

.. class:: Uint16Type

   This class is a subclass of :class:`IntegralType`, and represents
   YANG **uint16** type.

.. class:: Uint32Type

   This class is a subclass of :class:`IntegralType`, and represents
   YANG **uint32** type.

.. class:: Uint64Type

   This class is a subclass of :class:`IntegralType`, and represents
   YANG **uint64** type.

.. class:: UnionType

   This class is a subclass of :class:`DataType`, and represents YANG
   **union** type.

   A :term:`cooked value` of this type must be a valid cooked value of
   a union's member type. Methods in this class are implemented so
   that they iterate through the member types in the order in which
   they are specified in the union type definition, and try the same
   method from their classes. If the method fails, next member class
   is tried in turn. The result of the first method implementation
   that succeeds is used as the result of the implementation in the
   :class:`UnionType`. If the method does not succeed for any of the
   member classes, then the :class:`UnionType` method fails, too.

   .. doctest::

      >>> union_t.parse_value('true')  # result is bool, not string
      True

   .. rubric:: Instance Attributes

   .. attribute:: types

      List of member types.

      .. doctest::

	 >>> len(union_t.types)
	 2
	 >>> type(union_t.types[0])
	 <class 'yangson.datatype.StringType'>

.. _7.3: https://tools.ietf.org/html/rfc7950#section-7.3
.. _9.1: https://tools.ietf.org/html/rfc7950#section-9.1
.. _9.7.4.2: https://tools.ietf.org/html/rfc7950#section-9.7.4.2
.. _9.9.3: https://tools.ietf.org/html/rfc7950#section-9.9.3
.. _9.13: https://tools.ietf.org/html/rfc7950#section-9.13
