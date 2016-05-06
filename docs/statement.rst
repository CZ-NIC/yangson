===============
YANG Statements
===============

.. module:: yangson.statement
   :synopsis: Class representing YANG statements
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

.. class:: Statement

   Instances of this class represent parsed YANG statements. Its
   constructor arguments initialize the instance attributes according
   to the following table:

   ========  =============== ======== ===============
   Argument  Type            Default  Attribute
   ========  =============== ======== ===============
   *kw*      YangIdentifier           *keyword*
   *arg*     Optional[str]            *argument*
   *sup*     Statement       ``None`` *superstmt*
   *sub*     List[Statement] ``[]``   *substatements*
   *pref*    YangIdentifier  ``None`` *prefix*
   ========  =============== ======== ===============

   .. attribute:: keyword

      The statement's keyword. For extension statements, this is the
      local part of the keyword.

   .. attribute:: prefix

      Prefix of the statement keyword. It is ``None`` for all built-in
      statements, and for an extension statement it is the prefix of
      the module where the extension is defined.

   .. attribute:: argument

      The statement's argument. It is the “final” value of the
      argument string in which all preliminary processing steps, i.e.
      substitution of escape sequences and concatenation of parts
      joined with ``+``, have already been performed. For statements
      that have no argument, such as **input**, the value of this
      attribute is ``None``.

   .. attribute:: superstmt

      Parent statement, or ``None``.

   .. attribute:: substatements

      List of substatements.

   .. automethod:: find1

   .. automethod:: find_all

   .. automethod:: get_definition
