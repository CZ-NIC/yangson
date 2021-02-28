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
   >>> mex5a = dm.schema_data.modules[('example-5-a', '2018-10-25')].statement

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

      .. doctest::

         >>> len(mex5a.substatements)
         17

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
         yangson.exceptions.StatementNotFound: `rpc' in `module "example-5-a" { ... }'

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

.. class:: ModuleParser(text: str, name: YangIdentifier = None, rev: str = None)

   This class is a subclass of :class:`.Parser`, and implements a
   recursive-descent parser for YANG modules. Source text of the YANG
   module is passed to the constructor in the *text* argument (see
   also the :attr:`.Parser.input` attribute). The other two arguments,
   *name* and *rev*, are optional and may be used for initializing
   the instance attributes below.

   .. rubric:: Instance Attributes

   .. attribute:: name

      Module or submodule name that is expected to be found in the
      module text.

   .. attribute:: rev

      Module or submodule revision date that is expected to be found
      in the module text as the most recent revision.

   .. rubric:: Public Methods

   .. method:: parse() -> Statement

      Parse the YANG module text.

      Apart from parsing exceptions raised in the methods of the
      :mod:`.parser` module, this method may raise the following
      exceptions:

      * :exc:`~.ModuleNameMismatch` – if the module name doesn't match
        the :attr:`name` attribute
      * :exc:`~.ModuleRevisionMismatch` – if the most recent revision date
        doesn't match the :attr:`rev` attribute.

      .. doctest::

         >>> with open('example-5-a.yang') as infile:
         ...     m5atxt = infile.read()
         >>> str(ModuleParser(m5atxt).parse())
         'module "example-5-a" { ... }'
         >>> str(ModuleParser(m5atxt, rev='2018-04-01').parse())
         Traceback (most recent call last):
         ...
         yangson.exceptions.ModuleRevisionMismatch: '2018-10-25', expected '2018-04-01'
