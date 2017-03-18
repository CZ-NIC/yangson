******
Parser
******

.. module:: yangson.parser
   :synopsis: Recursive-descent parser.

.. testsetup::

   import re
   from yangson.parser import Parser

The *parser* module implements the following class:

* :class:`Parser`: Recursive-descent parser.

.. rubric:: Type Alias

.. autodata:: TransitionTable

   This type represents the transition table for a deterministic
   finite automaton (DFA). See documentation for the method
   :meth:`Parser.dfa`.

.. class:: Parser(text: str)

   This abstract class provides a framework for implementing a
   recursive-descent parser. The *text* argument contains the input
   text to be parsed.

   Concrete parsers should be implemented as a subclass of
   :class:`Parser`. By convention, such a parser class should define
   the :meth:`parse` method.

   .. doctest::

      >>> p = Parser("x \t #quu0a,foo:bar< qwerty")

   .. rubric:: Instance Attributes

   .. attribute:: input

      Input text for the parser, initialized from the *text*
      constructor argument.

   .. attribute:: offset

      Current position in the input text.

   .. rubric:: Public Methods

   .. automethod:: __str__

      The returned value is the :attr:`input` string with the
      character ``§`` inserted at the position of :attr:`offset`. In
      the following example, the position is right at the start of the
      input text.

      .. doctest:

	 >>> str(p)
	 '§x \t #quu0a,foo:bar< qwerty'

   .. method:: adv_skip_ws() -> bool

      First advance :attr:`offset` by one and then skip optional
      whitespace. Return ``True`` if some whitespace was really
      skipped.

      .. doctest::

	 >>> p.adv_skip_ws()
	 True
	 >>> str(p)
	 'x \t §#quu0a,foo:bar< qwerty'

   .. automethod:: at_end

      .. doctest::

	 >>> p.at_end()
	 False

   .. method:: char(c: str) -> None

      Parse the character *c*.

      This method may raise these exceptions:

      * :exc:`~.EndOfInput` – if the parser is past the end of input.
      * :exc:`~.UnexpectedInput` – if the next character is different
	from *c*.

      .. doctest::

	 >>> p.char("#")
	 >>> str(p)
	 'x \t #§quu0a,foo:bar< qwerty'

   .. method:: dfa(ttab: TransitionTable, init: int = 0) -> int

      This method realizes a deterministic finite automaton (DFA) that
      is also capable of side effects. The states of the DFA are
      integers, and *init* specifies the initial state.  Negative
      integers correspond to final states, and the method returns the
      final state in which automaton reaches.

      The *ttab* argument is a transition table for the DFA. The
      :data:`TransitionTable` alias stands for a list whose *i*-th
      entry specifies the “row” corresponding to the state *i*. Each
      entry is a dictionary in which:

      * Keys are single-character strings or the empty string. The
	latter specifies the default transition that takes place
	whenever none of the other keys matches.
      * Values are *functions* with no argument that have to return a
	new state (integer), and may also have side effects.

      The method starts in the initial state *init*, reads the next
      input character and performs a lookup in the transition
      table. The retrieved transition function is then executed and
      its return value is the new state with which the whole process
      is repeated. However, if the new state is final, the computation
      stops and the final state is returned.

      DFA in the following example parses the input string up to the
      occurrence of the first ``0`` character.

      .. doctest::

	 >>> p.dfa([{"": lambda: 0, "0": lambda: -1}])
	 -1
	 >>> str(p)
	 'x \t #quu§0a,foo:bar< qwerty'

   .. method:: line_column() -> Tuple[int, int]

      Return line and column coordinates of the current
      :attr:`offset`.

      .. doctest::

	 >>> p.line_column()
	 (1, 8)

   .. method:: match_regex(regex: Pattern, required: bool = False, \
	       meaning: str = "") -> str

      Parse input text starting from the current :attr:`offset` by matching
      it against a regular expression. The argument *regex* is a
      regular expression object (result of :func:`re.compile`). If the
      regular expression matches, the matched string is returned and
      :attr:`offset` is advanced past that string in the input text.

      The *required* flag controls what happens if the regular
      expression doesn't match: if it is ``True``, then
      :exc:`~.UnexpectedInput` is raised, otherwise ``None`` is
      returned.

      The optional *meaning* argument can be used to describe what the
      regular expression means – it is used in error messages.

      .. doctest::

	 >>> p.match_regex(re.compile("[0-9a-f]+"), meaning="hexa")
	 '0a'

   .. method:: one_of(chset: str) -> str

      Parse one character from the set of alternatives specified in
      *chset*. If a match is found, :attr:`offset` is advanced by one
      position, and the matching character is returned. Otherwise,
      :exc:`~.UnexpectedInput` is raised.

      .. doctest::

	 >>> p.one_of(".?!,")
	 ','

   .. method:: peek() -> str

      Return the next input character without advancing
      :attr:`offset`. If the parser is past the end of input,
      :exc:`~.EndOfInput` is raised.

      .. doctest::

	 >>> p.peek()
	 'f'
	 >>> str(p)
	 'x \t #quu0a,§foo:bar< qwerty'

   .. method:: prefixed_name() -> Tuple[YangIdentifier, \
	       Optional[YangIdentifier]]

      Parse a :term:`prefixed name` and return a tuple containing the
      (local) name as the first component, and the prefix or ``None``
      as the second component.

      .. doctest::

	 >>> p.prefixed_name()
	 ('bar', 'foo')

   .. automethod:: remaining

      .. doctest::

	 >>> p.remaining()
	 '< qwerty'
	 >>> p.at_end()
	 True

   .. method:: skip_ws() -> bool

      Skip optional whitespace and return ``True`` if some was really skipped.

      .. doctest::

	 >>> q = Parser("\npi=3.14.159xyz!foo-bar")
	 >>> q.skip_ws()
	 True

   .. method:: test_string(string: str) -> bool

      Test whether *string* comes next in the input string. If it
      does, :attr:`offset` is advanced past that string, and ``True``
      is returned. Otherwise, ``False`` is returned and :attr:`offset`
      is unchanged (even if *string* partly coincides with the input
      text). No exception is raised if the parser is at the end of
      input.

      .. doctest::

	 >>> q.test_string("pi=")
	 True
	 >>> str(q)
	 '\npi=§3.14.159xyz!foo-bar'

   .. method:: unsigned_float() -> float

      Parse and return an unsigned floating point number. The
      exponential notation is not supported.

      .. doctest::

	 >>> q.unsigned_float()
	 3.14

   .. automethod:: unsigned_integer

      .. doctest::

	 >>> q.offset += 1    # skipping the dot
	 >>> q.unsigned_integer()
	 159

   .. method:: up_to(term: str) -> str

      Parse and return a segment of input text up to the terminating
      string *term*. Raise :exc:`~.EndOfInput` if *term* does not occur
      in the rest of the input string.

      .. doctest::

	 >>> q.up_to("!")
	 'xyz'

   .. automethod:: yang_identifier

      .. doctest::

	 >>> q.yang_identifier()
	 'foo-bar'
