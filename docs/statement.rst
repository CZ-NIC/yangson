***************
YANG Statements
***************

.. module:: yangson.statement
   :synopsis: YANG statements and a parser for YANG modules

This module implements the following classes:

* :class:`ModuleParser`: Recursive-descent parser for YANG modules.
* :class:`Statement`: YANG statements.

The module also defines the following exceptions:

* :exc:`DefinitionNotFound`: Requested definition does not exist.
* :exc:`StatementNotFound`: Required statement does not exist.
* :exc:`WrongArgument`: Statement argument is invalid.

.. class:: Statement(kw: YangIdentifier, arg: Optional[str], pref: \
	   YangIdentifier = None)

   An instance of this class represents a parsed YANG statement. The
   constructor arguments *kw*, *arg* and *pref* initialize instance
   attributes :attr:`keyword`, :attr:`argument` and :attr:`prefix`,
   respectively.

   .. rubric:: Instance Attributes

   .. attribute:: keyword

      The statement's keyword. For extension statements, this is the
      local part of the keyword.

   .. attribute:: prefix

      Optional prefix of the statement keyword. It is ``None`` for all
      built-in statements, and for an extension statement it is the
      prefix of the module where the extension is defined.

   .. attribute:: argument

      The statement's argument. It is the final value of the argument
      string in which all preliminary processing steps, i.e.
      substitution of escape sequences and concatenation of parts
      joined with ``+``, have already been performed. For statements
      that have no argument, such as **input**, the value of this
      attribute is ``None``.

   .. attribute:: superstmt

      Parent statement, or ``None`` if there is no parent.

   .. attribute:: substatements

      List of substatements.

   .. rubric:: Public Methods

   .. method:: find1(kw: YangIdentifier, arg: str = None, pref: \
	       YangIdentifier = None, required: bool = False) ->
	       Optional[Statement]

      Return the first substatement of the receiver with a matching
      keyword and, optionally, argument. In order to match, the local
      part of the keyword has to be *kw*, and prefix has to be *pref*.
      If *pref* is ``None``, only built-in statements match. The last
      argument, *required*, controls what happens if a matching
      substatement is not found: if *required* is ``True``, then
      :exc:`StatementNotFound` is raised, otherwise ``None`` is
      returned. If *arg* is ``None``, then the arguments of
      substatements are not taken into account.

   .. method:: find_all(kw: YangIdentifier, pref: YangIdentifier = \
	       None) -> List[Statement]

      Return the list of all substatements with a matching
      keyword. The conditions on keyword matching are the same as for
      :meth:`find1`.

   .. method:: get_definition(name: YangIdentifier, kw:
	       YangIdentifier) -> Statement:

      Search the receiver's parent statement and then all ancestor
      statements from inside out for the definition whose name is
      *name*. The second argument, *kw*, has to be ``grouping`` or
      ``typedef``, and controls whtehr the method looks for the
      definition of a grouping or typedef, respectively.

      This method raises :exc:`DefinitionNotFound` if the search
      is not successful.
