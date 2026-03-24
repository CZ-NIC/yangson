************
Introduction
************

*Yangson* is a Python 3 library that offers programmers tools for
working with configuration and other data modelled with the YANG data
modelling language. *Yangson* supports only the JSON data encoding as
defined in [RFC7951]_.

This documentation starts with a :ref:`tutorial <quick-start>` and then covers the entire public API of the library. :ref:`cmdline-tools` that are included in the *yangson* `package`_ or in the project `repository`_ can also serve as examples of how the library is typically used.

Main Features
=============

* Support for YANG version 1.1 [RFC7950]_ and YANG library [RFC7895]_.

* Instance data are internally represented as a `persistent data
  structure`_. This makes the code thread-safe, and also allows for
  copying and updating data trees in a space-efficient way.

* Parser and evaluator for XPath 1.0 expressions [XPath]_ and
  XPath extensions defined for YANG 1.1 (new XPath functions, default
  namespace, and others).

* Complete validation of instance data against the data model.

* Support for RESTCONF data resources [RFC8040]_ (with timestamps and
  entity-tags) and resource identifiers.

* Support for NETCONF Access Control Module (NACM) [RFC6536]_.

Installation
============

The *yangson* `package`_ is available from PyPI_ and can be installed
using the *pip* package manager as follows::

  python -m pip install yangson

Naming of YANG Modules
======================

*Yangson* requires that the names of disk files containing
modules be of the form specified in [RFC7950]_, sec. `5.2`_:

.. code-block:: none

   module-or-submodule-name ['@' revision-date] '.yang'

The revision date, if specified in the file name, must match the argument of the (sub)module's first (most recent) **revision** statement.
For a (sub)module without a **revision** statement, the ``'@' revision-date`` part must be omitted.

*Yangson* is currently able to parse only the compact syntax of YANG
files. Modules written in the alternative XML format (YIN) can be
converted to the compact syntax by using the XSLT stylesheet
*yin2yang.xsl* that can be obtained from the `YIN Tools`_ project.

Doctest Examples
================

This documentation uses doctest__ snippets rather heavily. For this
purpose, each Python module is associated with a specific example data
model and JSON instance document(s). Python statements that
initialize these examples are also included as doctest snippets. Other
obvious steps, such as necessary Python module imports, are not shown.

__ http://www.sphinx-doc.org/en/stable/ext/doctest.html

The example YANG modules, YANG library specifications and instance
documents are included with *Yangson* documentation, in subdirectories
of the ``examples`` directory. All the examples are also listed in
:ref:`sec-examples`.

Doctest snippets embedded in the documentation are also used as an
alternative test suite. To run all Python code contained in those
snippets and obtain a summary of the results per Python module, use
the following command from the ``docs`` directory::

  $ make doctest

.. _persistent data structure: https://en.wikipedia.org/wiki/Persistent_data_structure
.. _package: https://pypi.org/project/yangson
.. _repository: https://github.com/CZ-NIC/yangson
.. _5.2: https://rfc-editor.org/rfc/rfc7950.html#section-5.2
.. _PyPI: https://pypi.python.org
.. _YIN Tools: https://github.com/llhotka/yin-tools
