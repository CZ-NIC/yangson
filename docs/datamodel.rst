**********
Data Model
**********

.. module:: yangson.datamodel
   :synopsis: Data model representation.

.. testsetup::

   import json
   import os
   os.chdir("examples/ex1")

.. testcleanup::

   os.chdir("../..")
   del DataModel._instances[DataModel]

The *datamodel* module implements the following class:

* :class:`DataModel`: basic user-level entry point to YANG data model
  information.

Doctest__ snippets for this module use the data model and instance
document from :ref:`sec-ex1`.

__ http://www.sphinx-doc.org/en/stable/ext/doctest.html

.. class:: DataModel(yltxt: str, mod_path: List[str])

   This class provides a basic user-level entry point to the *Yangson*
   library.

   The constructor argument *yltxt* is a string with JSON-encoded YANG
   library data [RFC7895]_, and *mod_path* is a list of filesystem
   directories in which *Yangson* searches for YANG modules.

   :class:`DataModel` is a *singleton* class which means that only one
   instance can be created. This limitation corresponds to the fact
   that it is not possible to work with multiple data models at the
   same time.

   The class constructor may raise the following exceptions:

   * :exc:`BadYangLibraryData` – if YANG library data is invalid.
   * :exc:`FeaturePrerequisiteError` – If a pre-requisite feature
     isn't supported.
   * :exc:`MultipleImplementedRevisions` – If multiple revisions of the
     same module are listed in YANG library with conformance type
     ``implement``.
   * :exc:`ModuleNotFound` – If a YANG module specified in YANG
     library cannot be found in any of the directories specified in
     *mod_path*.

   :class:`DataModel` is re-exported by the main package, so it can
   also be imported directly from there.

   .. doctest::

      >>> from yangson import DataModel

   .. rubric:: Public Methods

   .. classmethod:: from_file(name: str, mod_path: List[str] = ["."] ) \
		    -> DataModel

      Initialize the data model from a file containing JSON-encoded
      YANG library data and return the :class:`DataModel`
      instance. The *name* argument is the name of that file, and
      *mod_path* has the same meaning as in the class constructor. By
      default, *mod_path* includes only the current directory.

      This method may raise the same exceptions as the class
      constructor.

      .. doctest::

	 >>> dm = DataModel.from_file("yang-library-ex1.json")

   .. staticmethod:: module_set_id() -> str

      Return a unique identifier of the set of modules comprising the
      data model. This string, which consists of hexadecimal digits,
      is intended to be stored in the ``module-set-id`` leaf of YANG
      library data.
      
      The method computes the identifier as follows:

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

   .. staticmethod:: from_raw(robj: RawObject) -> RootNode

      Create a root instance node from a raw data tree contained in
      the *robj* argument. The latter will typically be a Python
      dictionary directly parsed from JSON text with the library
      function :func:`json.load` or :func:`json.loads`. We call this
      data tree “raw” because it needs to be processed into the
      “cooked” form before it can be used in *Yangson*. For example,
      64-bit numbers have to be encoded as strings in JSON text (see
      `sec. 6.1`_ of [RFC7951]_), whereas the cooked form is a Python
      number.

      See the documentation of :mod:`instvalue` module for more
      details, and see also :term:`raw value`.

      .. doctest::

	 >>> with open("example-data.json") as infile:
	 ...   ri = json.load(infile)
	 >>> inst = dm.from_raw(ri)
	 >>> inst.value
	 {'example-1:greeting': 'Hi!'}

   .. staticmethod:: get_schema_node(path: SchemaPath) -> Optional[SchemaNode]

      Return the schema node addressed by *path* argument, or ``None``
      if no such schema node exists.

      .. doctest::

	 >>> root = dm.get_schema_node("/")
	 >>> root.parent is None
	 True

   .. staticmethod:: get_data_node(path: DataPath) -> Optional[DataNode]

      Return the data node addressed by *path*, or ``None`` if such a
      data node doesn't exist. As opposed to the
      :meth:`get_schema_node` method, the *path* argument is a
      :term:`data path`, i.e. it contains only names of *data nodes*.

      .. doctest::

	 >>> leaf = dm.get_data_node("/example-1:greeting")
	 >>> leaf.parent is root
	 True

    .. staticmethod:: ascii_tree() -> str

      Generate ASCII art representation of the schema tree.
      
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

.. _sec. 6.1: https://tools.ietf.org/html/rfc7951#section-6.1
.. _pyang: https://github.com/mbj4668/pyang
