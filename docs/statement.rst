***************
YANG Statements
***************

.. module:: yangson.statement
   :synopsis: YANG statements and a parser for YANG modules

.. testsetup::

   import os
   os.chdir("examples/ex5")
   from yangson import DataModel
   from yangson.statement import ModuleParser

.. testcleanup::

   os.chdir("../..")

This module implements the following classes:

* :class:`ModuleParser`: Recursive-descent parser for YANG modules.
* :class:`Statement`: YANG statements.

Doctest__ snippets for this module use the YANG module *example-5-a*,
see :ref:`sec-ex5`.

__ http://www.sphinx-doc.org/en/stable/ext/doctest.html

.. doctest::

   >>> dm = DataModel.from_file("yang-library-ex5.json")
   >>> mex5a = dm.schema_data.modules[('example-5-a', '')].statement

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

      .. doctest::

	 >>> mex5a.keyword
	 'module'

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

      .. doctest::

	 >>> mex5a.argument
	 'example-5-a'

   .. attribute:: superstmt

      Parent statement, or ``None`` if there is no parent.

   .. attribute:: substatements

      List of substatements.

      >>> len(mex5a.substatements)
      16

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
      :exc:`~.StatementNotFound` is raised, otherwise ``None`` is
      returned. If *arg* is ``None``, then the arguments of
      substatements are not taken into account.

      .. doctest::

	 >>> lfs = mex5a.find1('leaf', 'string-leaf')
	 >>> str(lfs)
	 'leaf "string-leaf" { ... }'
	 >>> lfs.superstmt.keyword
	 'module'
	 >>> mex5a.find1('rpc') is None
	 True
	 >>> mex5a.find1('rpc', required=True)
	 Traceback (most recent call last):
	 ...
	 yangson.statement.StatementNotFound: `rpc' in `module "example-5-a" { ... }'

   .. method:: find_all(kw: YangIdentifier, pref: YangIdentifier = \
	       None) -> List[Statement]

      Return the list of all substatements with a matching
      keyword. The conditions on keyword matching are the same as for
      :meth:`find1`.

      .. doctest::

	 >>> len(mex5a.find_all('leaf'))
	 11
	 >>> mex5a.find_all('rpc')
	 []

   .. method:: get_definition(name: YangIdentifier, kw:
	       YangIdentifier) -> Statement:

      Search the receiver's parent statement and then all ancestor
      statements from inside out for the definition whose name is
      *name*. The second argument, *kw*, has to be ``grouping`` or
      ``typedef``, and controls whtehr the method looks for the
      definition of a grouping or typedef, respectively.

      This method raises :exc:`~.DefinitionNotFound` if the search
      is not successful.

      .. doctest::

	 >>> str(lfs.get_definition('my-string', 'typedef'))
	 'typedef "my-string" { ... }'
	 >>> lfs.get_definition('my-string', 'grouping')
	 Traceback (most recent call last):
	 ...
	 yangson.statement.DefinitionNotFound: grouping my-string

.. class:: ModuleParser(text: str)

   This class is a subclass of :class:`.Parser`, and implements a
   recursive-descent parser for YANG modules. Source text of the YANG
   module is passed to the constructor in the *text* argument (see
   also the :attr:`.Parser.input` attribute).

   .. rubric:: Public Methods

   .. automethod:: parse

      This method raises :exc:`~.WrongArgument` if a statement argument
      is invalid. It may also raise parsing exceptions defined in the
      :mod:`.parser` module.

      .. doctest::

	 >>> with open('example-5-a.yang') as infile:
	 ...     m5atxt = infile.read()
	 >>> str(ModuleParser(m5atxt).parse())
	 'module "example-5-a" { ... }'
