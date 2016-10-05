=================
XPath Expressions
=================

The *Yangson* library includes a fairly complete implementation of
XPath parser and evaluator. It supports XPath 1.0 [XPath]_ with
extensions defined for YANG 1.1 [RFC7950]_, such as new XPath
functions, default namespace, and other features.

.. testsetup::

   import json
   import os
   from yangson import DataModel
   from yangson.xpathparser import XPathParser
   os.chdir("examples/ex4")

.. testcleanup::

   os.chdir("../..")
   del DataModel._instances[DataModel]

XPath Abstract Syntax Tree
==========================

.. module:: yangson.xpathast
   :synopsis: Abstract syntax tree for XPath expressions

The :mod:`.xpathast` module defines classes that allow for building
`abstract syntax trees` (AST) for XPath 1.0 expressions with
extensions introduced by YANG 1.1. Only the following class is
intended to be public:

* :class:`Expr`: XPath 1.0 expression with YANG 1.0 extensions.

The module also defines the following exception:

* :exc:`XPathTypeError`: A subexpression is of a wrong type.

.. class:: Expr

   An abstract superclass for nodes of the XPath abstract syntax
   tree. The methods of this class described below comprise the public
   API for compiled XPath expressions.

   .. rubric:: Public Methods

   .. automethod:: __str__

   .. method:: evaluate(node: InstanceNode) -> XPathValue

      Evaluate the receiver and return the result, which can be a
      node-set, string, number or boolean. The *node* argument is an
      :class:`~.instance.InstanceNode` that is used as the context
      node for XPath evaluation.

      This method raises :exc:`XPathTypeError` if a subexpression
      evaluates to a value whose type is not allowed at a given
      place.

.. autoexception:: XPathTypeError(value: XPathValue)

   The *value* argument contains the XPath value that causes the
   problem.

Parser of XPath Expressions
===========================

.. module:: yangson.xpathparser
   :synopsis: Parser for XPath expressions

The :mod:`.xpathparser` module implements a parser for XPath 1.0
expressions with YANG 1.1 extensions.

The module defines the following classes:

* :class:`XPathParser`: Recursive-descent parser for XPath expressions.

The module also defines the following exceptions:

* :exc:`InvalidXPath`: An XPath expression is invalid.
* :exc:`NotSupported`: An XPath 1.0 feature isn't supported.

.. class:: XPathParser(text: str, mid: ModuleId) -> Expr

   This class is a subclass of :class:~.parser.Parser`, and implements
   a recursive-descent parser for XPath expressions. Constructor
   argument *text* contains the textual form of an XPath expression
   (see the :attr:`.Parser.input` attribute), and *mid* initializes
   the value of the :attr:`mid` instance attribute.

   .. rubric:: Instance Attributes

   .. attribute:: mid

      :term:`Module identifier` that specifies the YANG module in the
      context of which namespace prefixes contained in the parsed
      XPath expression are resolved.

   .. rubric:: Public Methods

   .. method:: parse() -> Expr

      Parse the input XPath expression and return a node of an XPath
      AST that can be evaluated.

      This method may raise the following exceptions:

      * :exc:`InvalidXPath` – if the input XPath expression is
	invalid.
      * :exc:`NotSupported` – if the input XPath expression contains a
	feature that isn't supported by the implementation, such as
	the ``preceding::`` axis.
      * other exceptions that are defined in the :mod:`.parser`
	module.

.. doctest::

   >>> dm = DataModel.from_file("yang-library-ex4.json",
   ... [".", "../../../examples/ietf"])
   >>> with open("example-data.json") as infile:
   ...     ri = json.load(infile)
   >>> inst = dm.from_raw(ri)
   >>> fref = inst.member("example-4-a:bag").member("example-4-b:fooref")
   >>> xp = 'deref(.)/../../quux[2]/preceding-sibling::quux = 3.1415'
   >>> cxp = XPathParser(xp, ('example-4-b', '')).parse()
   >>> print(cxp, end='')
   EqualityExpr (=)
     PathExpr
       FilterExpr
         FuncDeref
           Step (self None)
       LocationPath
         LocationPath
           LocationPath
             Step (parent None)
             Step (parent None)
           Step (child ('quux', 'example-4-b'))
             -- Predicates:
                Number (2.0)
         Step (preceding_sibling ('quux', 'example-4-b'))
     Number (3.1415)
   >>> cxp.evaluate(fref)
   True
