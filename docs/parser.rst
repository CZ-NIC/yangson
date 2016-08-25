******
Parser
******

.. module:: yangson.parser
   :synopsis: Recursive-descent parser.

Simple recursive descent-parser with support for common YANG syntactic elements.

This module implements the following class:

* :class:`Parser`: Recursive-descent parser.

This module defines the following exceptions:

* :exc:`ParserException`: Base class for parser exceptions.

* :exc:`EndOfInput`: Unexpected end of input.

* :exc:`UnexpectedInput`: Unexpected input.

.. rubric:: Type alias

.. data:: TransitionTable

.. class:: Parser(text: str)

   This class implements a recursive-descent parser for input text
   that is passed in the *text* argument.

   .. rubric:: Instance Variables

   .. attribute:: input

      Input text for the parser, initialized from the *text*
      constructor argument.

   .. attribute:: offset

      Current position in the input text.

   .. rubric:: Methods

   .. automethod:: remaining

   .. automethod:: at_end

   .. method:: peek() -> str

      Return the next input character without advancing
      :attr:`offset`. If the parser is past the end of input,
      :exc:`EndOfInput` is raised.

   .. method:: char(c: str) -> None

      Parse the character specified in the *c* argument that should
      be a single-character string.

      This method may raise these exceptions:

      * :exc:`EndOfInput` – if the parser is past the end of input.
      * :exc:`UnexpectedInput` – if the next character is different
	from *c*.

   .. method:: test_string(string: str) -> bool

      Test whether *string* comes next in the input string. If it
      does, :attr:`offset` is advanced past that string, and ``True``
      is returned. Otherwise, ``False`` is returned and :attr:`offset`
      is unchanged (even if *string* partly coincides with the input
      text). No exception is raised if the parser is at the end of
      input.

   .. method:: one_of(chset: str) -> str

      Parse one character from the set of alternatives specified in
      the *chset* argument. If a match is found, :attr:`offset` is
      advanced by one position, and the matching character is
      returned. Otherwise, :exc:`UnexpectedInput` is raised.

   .. method:: dfa(ptab: TransitionTable, init: int = 0) -> int
