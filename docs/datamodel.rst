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

The *datamodel* module implements the following class:

* :class:`DataModel`: basic user-level entry point to YANG data model
  information.

Doctest__ snippets for this module use the data model and instance
document from :ref:`sec-ex1`.

__ http://www.sphinx-doc.org/en/stable/ext/doctest.html

.. class:: DataModel(yltxt: str, mod_path: List[str], \
	   description: str = None)

   This class provides a basic user-level entry point to the *Yangson*
   library.

   The constructor argument *yltxt* is a string with JSON-encoded YANG
   library data [RFC7895]_, and *mod_path* is a list of filesystem
   directories in which *Yangson* searches for YANG modules (by
   default it is only the current directory).

   The *description* argument allows for adding a description text to
   the entire data model. If it is ``None``, then a default
   description is added which contains the ``module-set-id`` value
   from the YANG library data.

   The class constructor may raise the following exceptions:

   * :exc:`~.BadYangLibraryData` – if YANG library data is invalid.
   * :exc:`~.FeaturePrerequisiteError` – If a pre-requisite feature
     isn't supported.
   * :exc:`~.MultipleImplementedRevisions` – If multiple revisions of the
     same module are listed in YANG library with conformance type
     ``implement``.
   * :exc:`~.ModuleNotFound` – If a YANG module specified in YANG
     library cannot be found in any of the directories specified in
     *mod_path*.

   :class:`DataModel` is re-exported by the main package, so it can
   also be imported directly from there.

   .. doctest::

      >>> from yangson import DataModel

   .. rubric:: Public Methods

   .. classmethod:: from_file(name: str, mod_path: List[str] = ["."], \
		    description: str = None) -> DataModel

      Initialize the data model from a file containing JSON-encoded
      YANG library data and return the :class:`DataModel`
      instance. The *name* argument is the name of that file. The
      remaining two arguments are passed unchanged to the
      :class:`DataModel` class constructor.

      This method may raise the same exceptions as the class
      constructor.

      .. doctest::

	 >>> dm = DataModel.from_file("yang-library-ex1.json")

   .. method:: module_set_id() -> str

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

   .. method:: from_raw(robj: RawObject) -> RootNode

      Create a root instance node from a raw data tree contained in
      the *robj* argument. The latter will typically be a Python
      dictionary directly parsed from JSON text with the library
      function :func:`json.load` or :func:`json.loads`. We call this
      data tree “raw” because it needs to be processed into the
      “cooked” form before it can be used in *Yangson*. For example,
      64-bit numbers have to be encoded as strings in JSON text (see
      sec. `6.1`_ of [RFC7951]_), whereas the cooked form is a Python
      number.

      See the documentation of :mod:`instvalue` module for more
      details, and see also :term:`raw value`.

      .. doctest::

	 >>> with open("example-data.json") as infile:
	 ...   ri = json.load(infile)
	 >>> inst = dm.from_raw(ri)
	 >>> inst.value
	 {'example-1:greeting': 'Hi!'}

   .. method:: get_schema_node(path: SchemaPath) -> Optional[SchemaNode]

      Return the schema node addressed by *path*, or ``None`` if no
      such schema node exists. The *path* argument is a :term:`schema
      path`.

      .. doctest::

	 >>> root = dm.get_schema_node("/")
	 >>> root.parent is None
	 True

   .. method:: get_data_node(path: DataPath) -> Optional[DataNode]

      Return the data node addressed by *path*, or ``None`` if such a
      data node doesn't exist. As opposed to the
      :meth:`get_schema_node` method, the *path* argument is a
      :term:`data path`, i.e. it contains only names of *data nodes*.

      .. doctest::

	 >>> leaf = dm.get_data_node("/example-1:greeting")
	 >>> leaf.parent is root
	 True

    .. method:: ascii_tree() -> str

      Generate ASCII art representation of the schema tree.
      
      Note that this method returns a single tree for the entire data
      model. Other tools, such as pyang_, often produce one tree per
      module. Other differences are:

      - Types of *leaf* and *leaf-list* nodes are not shown because
	they often result in very long lines.

      - Nodes depending on unsupported features are not shown in the
	tree.

      .. doctest::

	 >>> print(dm.ascii_tree(), end='')
	 +--rw example-1:greeting? <string>

    .. method:: parse_instance_id(text: str) -> InstanceRoute

       Parse :term:`instance identifier` into an internal object of
       the :class:`~.instance.InstanceRoute` class that can be used as
       a parameter to the the :meth:`~.instance.InstanceNode.goto` and
       :meth:`~.instance.InstanceNode.peek` methods of the
       :class:`~.instance.InstanceNode` class.

    .. method:: parse_resource_id(text: str) -> InstanceRoute

       Parse :term:`resource identifier` into an
       :class:`~.instance.InstanceRoute` object. Yanson extends the
       syntax of resource identifiers defined in sec. `3.5.3`_ of
       [RFC8040]_ so as to support entire lists and leaf-lists as
       resources: the last component of a resource identifier can be
       the name of a list or leaf-list, with no keys or value
       specified.

    .. method:: schema_digest() -> str

       Generate digest of the data model schema. This information is
       primarily intended to aid client applications.

       The returned string contains a structure of JSON objects that
       follows the data model hierarchy. Every JSON object also
       contains members with information about the corresponding data
       node (including the anonymous root node), namely:

       * The following members are available for all nodes:

	 - ``class`` – class of the node, with these possible values:
	   ``root``, ``container``, ``leaf``, ``list``, ``leaf-list``,
	   ``anydata`` and ``anyxml``.

	 - ``description`` – description string as defined in the data
	   model, or empty string if the node has no description.

       * Internal nodes (the root node, containers, and lists) have the
         ``children`` member. Its value is an object with a name/value
	 pair for every child data node that is defined in the data
	 model. The name is the identifier of the child identical to
	 the name of the node's instance – for example, it is
	 ``foomod:bar`` for the ``bar`` data node defined in the
	 ``foomod`` module. The value of each member of the
	 ``children`` object is then another object containing the
	 child's schema digest.

       * The following members are added for terminal nodes (leafs and
	 leaf-lists):

	 - ``base-type`` – base type of the terminal node such as
	   ``uint8``, ``string`` etc.

	 - ``derived`` – this member is present only if the node's type
	   is derived, and contains the name of the derived type.

       * Container nodes also have the ``presence`` member that is
         ``true`` for containers with presence (see sec. `7.5.1`_ of
	 [RFC7950]_), and ``false`` otherwise.

       * List nodes also have the ``keys`` member whose value is an
         array with names of the list's keys.

       .. doctest::

	  >>> len(dm.schema_digest())
	  222

.. _3.5.3: https://tools.ietf.org/html/rfc8040#section-3.5.3
.. _6.1: https://tools.ietf.org/html/rfc7951#section-6.1
.. _7.5.1: https://tools.ietf.org/html/rfc7950#section-7.5.1
.. _pyang: https://github.com/mbj4668/pyang
