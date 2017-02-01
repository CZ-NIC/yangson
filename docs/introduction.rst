************
Introduction
************

*Yangson* is a Python 3 library that offers programmers tools for
working with configuration and other data modelled with the YANG data
modelling language. *Yangson* supports only the JSON data encoding as
defined in [RFC7951]_.

The *Yangson* package also provides a simple :ref:`man-page`.

Main Features
=============

* Support for YANG version 1.1 [RFC7950]_ and YANG library [RFC7895]_.

* Instance data are internally represented as a `persistent data
  structure`__. This makes the code thread-safe, and also allows for
  copying and updating data trees in a space-efficient way.

* Parser and evaluator for XPath 1.0 expressions [XPath]_ and
  extensions defined for YANG 1.1 (new XPath functions, default
  namespace, and others).

* Complete validation of instance data against the data model.

* Support for RESTCONF data resources [RFC8040]_ (timestamps and
  entity-tags) and resource identifiers.

* Support for NETCONF Access Control Module (NACM) [RFC6536]_.

__ https://en.wikipedia.org/wiki/Persistent_data_structure

Installation
============

The *Yangson* package is available from PyPI_ and can be installed
using the *pip* package manager as follows::

  python -m pip install yangson

Naming of YANG Modules
======================

In order be able to find and read the correct revision of each YANG
module, *Yangson* requires that the names of disk files containing
modules are of the form specified in [RFC7950]_, sec. `5.2`_:

.. code-block:: none

   module-or-submodule-name ['@' revision-date] '.yang'

For a (sub)module without a **revision** statement, the ``'@'
revision-date`` part must be omitted, otherwise it has to be present.

*Yangson* is currently able to parse only the compact syntax of YANG
files. Modules written in the alternative XML format (YIN) can be
converted to the compact syntax by using the XSLT stylesheet
*yin2yang.xsl* that is also included in *Yangson* distribution
(directory *tools/xslt*).

Doctest Examples
================

This documentation uses doctest__ snippets rather heavily. For this
purpose, each Python module uses a specific example data model and/or
JSON instance document that have to be loaded first. Python statements that
do so are also included as doctest snippets. Other obvious steps, such
as necessary Python module imports, are not shown.

__ http://www.sphinx-doc.org/en/stable/ext/doctest.html

The example YANG modules, YANG library specifications and instance
documents are included with *Yangson* documentation, in subdirectories
of the ``examples`` directory. All the examples are also listed in
:ref:`sec-examples`.

Doctest snippets embedded in the documentation can also be used as a
test suite. To run all Python code contained in those snippets and
obtain a summary of the results per Python module, use the following
command from the ``docs`` directory::

  $ make doctest

.. _persistent structures: https://en.wikipedia.org/wiki/Persistent_data_structure
.. _5.2: https://tools.ietf.org/html/rfc7950#section-5.2
.. _PyPI: https://pypi.python.org
