*********************
Annotated Constraints
*********************

.. module:: yangson.constraint
   :synopsis: Classes representing annotated YANG constraints.

.. testsetup::

   from yangson.constraint import Intervals, Pattern

The *constraint* module implements the following classes:

* :class:`Constraint`: Abstract class representing annotated YANG constraints.
* :class:`Intervals`: Class representing a sequence of numeric intervals.
* :class:`Pattern`: Class representing regular expression pattern.
* :class:`Must`: Class representing the constraint specified by a "must" statement.

.. rubric:: Type Aliases

.. data:: Number

   Union of numeric classes appearing in interval constraints.

.. data:: Interval

   Numeric interval implemented as a list containing either a single
   number or a pair of numbers (lower and upper bound).

.. class:: Constraint(error_tag: Optional[str], error_message: Optional[str])

   Abstract class for annotated YANG constraints, i.e. those for
   which a custom error tag and error message can be defined.

   The constructor arguments initialize the instance attributes.

   .. rubric:: Instance Attributes

   .. attribute:: error_tag

      String tag indicating violation of the constraint. A custom
      error tag can be defined by the **error-app-tag** statement, see
      sec. `7.5.4.2`_ in [RFC7950]_. If the value is ``None``, then
      some predefined error tag is used in an exception trigerred by
      violating the constraint.

   .. attribute:: error_message

      Text describing the error condition connected to violation of
      the constraint.  A custom error message can be defined by the
      **error-message** statement, see sec. `7.5.4.1`_ in
      [RFC7950]_. If the value is ``None``, then some predefined error
      message, which may be empty, is used in an exception trigerred
      by violating the constraint.

.. class:: Intervals(intervals: List[Interval], \
	   parser: Callable[[str], Optional[Number]] = None, \
	   error_tag: str = None, error_message: str = None)

   This class is a subclass of :class:`Constraint`. It represents a
   sequence of intervals that restrict a numeric leaf value or length
   of a string, usually specified by the statements **range** and
   **length**, respectively (see sections `9.2.4`_ and `9.4.4`_ in
   [RFC7950]_).

   The constructor arguments initialize the instance attributes. If
   *parser* is ``None`` (default value), then a parser for dekadic
   integers is used.

   .. doctest::

      >>> iints = Intervals([[0, 10]], error_tag="out-of-range")

   .. rubric:: Instance Attributes

   .. attribute:: intervals

      A list of numeric intervals.

   .. attribute:: parser

      A function that receives a string as the only argument and
      returns the corresponding numeric value of the appropriate type,
      or ``None`` if parsing fails.

   .. rubric:: Public Methods

   .. method:: __contains__(value: Number) -> bool

      Return ``True`` if *value* is contained in one of the receiver's
      intervals, otherwise return ``False``.

      This method enables the Python operators ``in`` and ``not in``
      for use with instances of this class.

      .. doctest::

         >>> 5 in iints
	 True

   .. automethod:: __str__

      .. doctest::

	 >>> str(iints)
	 '0..10'

   .. method:: restrict_with(expr: str, error_tag: str = None, \
	       error_message: str = None) -> None

      Restrict the receiver with range expression *expr*. Each of the
      other two arguments, if specified and not equal to ``None``,
      replaces the value of the corresponding instance attribute.

      This method raises :exc:`~.InvalidArgument` if *expr* is not a
      valid range expression.

      .. doctest::

	 >>> iints.restrict_with('2..4|6|8..max')
	 >>> str(iints)
	 '2..4 | 6 | 8..10'

.. class:: Pattern(pattern: str, invert_match: bool = False, \
	   error_tag: str = None, error_message: str = None)

   This class is a subclass of :class:`Constraint`. It represents a
   constraint defined by the regular expression *pattern*, usually
   specified by the **pattern** statement (sec. `9.4.5`_ in
   [RFC7950]_).

   The remaining constructor arguments initialize the instance
   attributes.

   The constructor raises :exc:`~.InvalidArgument` if *pattern* is not
   a valid YANG regular expression pattern.

   .. rubric:: Instance Attributes

   .. attribute:: regex

      This attribute contains the *Python* regular expression (see
      module :mod:`re`) translated from the constructor argument
      *pattern*.

   .. attribute:: invert_match

      This is a modifier that reverses the meaning of the pattern
      matching constraint: it is satisfied if a given string does
      *not* match the pattern. This modifier is usually specified by
      the statement

      ::

	 modifier invert-match;

   .. doctest::

      >>> pat = Pattern('[A-Z][a-z]*')
      >>> pat.regex.search('Yangson').group()
      'Yangson'
      >>> pat.regex.search('iPhone') is None
      True

   Note that the string in the last example doesn't match *pat*
   because YANG patterns are implicitly “anchored” – in most other
   flavours of regular expressions the anchoring has to be specified
   explicitly with special symbols ``^`` and ``$``.

.. class:: Must(expression: Expr, error_tag: str = None, error_message: str = None)

   This class is a subclass of :class:`Constraint`. It represents a
   constraint defined by the **must** statement (sec. `7.5.3`_ in [RFC7950]_).

   The constructor arguments initialize the instance attributes.

   .. rubric:: Instance Attributes

   .. attribute:: expression

      A compiled XPath expression, i.e. an instance of the
      :class:`.xpathast.Expr` class.

.. _7.5.3: https://tools.ietf.org/html/rfc7950#section-7.5.3
.. _7.5.4.1: https://tools.ietf.org/html/rfc7950#section-7.5.4.1
.. _7.5.4.2: https://tools.ietf.org/html/rfc7950#section-7.5.4.2
.. _9.2.4: https://tools.ietf.org/html/rfc7950#section-9.2.4
.. _9.4.4: https://tools.ietf.org/html/rfc7950#section-9.4.4
.. _9.4.5: https://tools.ietf.org/html/rfc7950#section-9.4.5
