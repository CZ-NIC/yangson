==========
Data Model
==========

.. module:: yangson.datamodel
   :synopsis: Data model representation.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

.. testsetup::

   import json
   import os
   os.chdir("examples/ex1")

This module provides the :class:`DataModel` class that provides the basic
user-level API to the *Yangson* library.

.. class:: DataModel(yltxt: str, mod_path: List[str] )

   This class represents a high-level view of the YANG data model. Its
   constructor has two arguments:

   - **yltxt** – JSON text with YANG library data;
   - **mod_path** – list of filesystem paths from which the YANG modules
     that are listed in the YANG library data can be retrieved.

   It is a *singleton* class which means that only one instance can be
   created.

   :class:`DataModel` is also re-exported by the main package, so it
   can also be imported directly from there:

   .. doctest::

      >>> from yangson import DataModel

   .. automethod:: from_file

      By default, the **mod_path** list contains only the current directory.

      .. doctest::

	 >>> dm = DataModel.from_file("yang-library-ex1.json")

   .. automethod:: module_set_id

      The algorithm for computing the result is as follows:

      - The list of module and sumodule names with revisions in the
	format ``name@revision`` is created. For (sub)modules that
	don't specify any revision, the empty string is used in place
	of ``revision``.
      - The list is alphabetically sorted, its entries joined
	back-to-back, and the result converted to a bytestring using
	the ASCII encoding.
      - The SHA-1 hash of the bytestring is computed, and its
	hexadecimal digest is the result.

      .. doctest::

	 >>> dm.module_set_id()
	 'ae4bf1ddf85a67ab94a9ab71593cd1c78b7f231d'

   .. automethod:: from_raw

      The **robj** parameter will typically contain a Python
      dictionary parsed from JSON text with the library function
      :func:`json.load` or :func:`json.loads`. We call this value
      “raw” because it needs to be processed into the internal or
      “cooked” form. For example, 64-bit numbers have to be encoded as
      strings in JSON text (see `sec. 6.1`_ of [Lho16]_), whereas the
      cooked form is a Python number.

      See the documentation of :mod:`datatype` module for details
      about the cooked form of each data type, and see also
      :term:`raw value`.

      .. doctest::

	 >>> with open("example-data.json", encoding="utf-8") as infile:
	 ...   rdata = json.load(infile)
	 >>> inst = dm.from_raw(rdata)
	 >>> inst.value
	 {'example-1:greeting': 'Hi!'}

   .. automethod:: get_schema_node

      See also :term:`schema path`.

      .. doctest::

	 >>> dm.get_schema_node("/").parent is None
	 True

   .. automethod:: get_data_node

      See also :term:`schema path`.

      .. doctest::

	 >>> dm.get_data_node("/example-1:greeting").name
	 'greeting'

   .. automethod:: ascii_tree

      Note that this method returns a single tree for the entire data
      model. Other tools, such as pyang_, often produce one tree per
      module. Other differences are:

      - Types of *leaf* and *leaf-list* nodes are not shown because
	they often result in very long lines.

      - Nodes depending on unsupported features are not shown in the
	tree.

      .. doctest::

	 >>> dm.ascii_tree()
	 '+--rw example-1:greeting?\n'

.. _sec. 6.1: https://tools.ietf.org/html/draft-ietf-netmod-yang-json-10#section-6.1
.. _pyang: https://github.com/mbj4668/pyang
