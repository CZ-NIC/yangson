************************
Concepts and Terminology
************************

Data modelling and schema languages is a complex business – that's why JSON folks try to avoid it like plague. We believe, however, that data modelling greatly helps interoperability and unification of management interfaces. From a programmer's perspective, data models not only document the data that our programs process, but they can be also be used for automating many difficult and/or laborious tasks such as validating data or building user interfaces.

YANG tries to be easy to read and understandable. Very often, people are able to understand what YANG data models mean without having read YANG language specification. Nevertheless, some concepts and rules in YANG are less than intuitive, and some are perhaps even slightly peculiar. This section gives an overview of fundamental YANG concepts and terms the are needed for understanding the documentation of the Yangson library. However, it is no substitute for studying YANG documentation especially [Bjo16]_ and [Bie16]_.

Another factor that may cause confusion is conflicting terminology: some terms, such as *module* or *instance*, are used, with different meanings, in both Python and YANG.
Therefore, when reading the following sections, it is important to distinuish whether a given text discusses programming language or data modelling stuff.

Data Models
***********

Data models define and describe some data. In the case of YANG, the data are of four different sorts:

* configuration,
* state data and statistics,
* parameters of RPC (remote procedure call) operations,
* asynchronous event notifications.

YANG assumes that data of all the sorts listed above are hierarchically organised, i.e. they form a tree. For example, data encoded in JSON can be modelled nicely with YANG.

For the specification of a data model, YANG uses both formal means and textual descriptions that may specify additional rules and constraints. Such textual descriptions are considered an integral part of the data model and cannot be ignored!

The formal means include:

* The hierarchical structure of data is described via containment of YANG. For   example, a container node is defined through the **container** statement, and child nodes of this container are defined through its substatements.

* YANG also allows for defining which nodes are mandatory and which are optional. For lists (sequences of entries of the same type), it is possible to specify the minimum and maximum number of entries.

* All scalar parameters have a type. YANG offers a wide variety of built-in types, such as *string*, *boolean* and *int32*. It is also possible to define *derived* types by taking an existing type (built-in or derived), giving it a new name, and optionally specifying some restrictions. For example, a restriction that may be applied to the *string* type is the *pattern* statement that specifies a regular expression that strings belonging to that type must match.

* For scalar parameters, it is also possible to define a default value.

A complete data model usually corresponds to a particular device or network service.

Trees and Nodes
***************

In most practical applications of the Yangson library, a programmer needs to work with two types of trees:

* *data tree* contains real data such as configuration, state data, RPC input/output parameters, or notifications. For our purposes, a data tree is a JSON document, or a parsed in-memory representation thereof.

* *schema tree* allows us to decide which data trees are valid and which are not.

Each node in the data tree corresponds to a *data node* in the schema tree. This looks confusing but in fact it is quite logical: data nodes are special schema nodes that have counterparts in the data tree. There are other schema nodes, namely *choice* and *case*, that don't have this property – they are used in the schema for specifying possible alternatives of which only one can appear in the data tree.

YANG Modules
************

YANG data models consist of *modules*. Each module defines the schema for some (usually related) parts of the data trees. Typically, a YANG module covers a certain subsystem or function. Every module defines a namespace that needs to be locally unique in a given data model. In Yangson, the namespace is identified by the YANG module name.

YANG modules may also offload parts of their contents into *submodules*. One can then have one (main) module and any number of submodules that are included from the main module. The main module and all its submodules share the same namespace identified by the main module name.

In order to create a particular data model, one has to decide which YANG modules will become part of it. The selection is recorded in *YANG library* data [BBW16]. And since YANG modules may exist in multiple revisions, a revision also needs to be specified for each module.

YANG also offers two mechanisms that allow for finer-grain control of data model content:

* *features* are essentially boolean flags that indicate whether an optional subsystem or function is supported or not. Parts of the schema tree can be labelled as being dependent on a feature: such a part exists only if the feature is supported.

* *deviations* allow for specifying that a given implementation doesn't exactly follow what's written in a YANG module. In effect, a deviation can be understood as a “patch” of the original YANG module.

Support for individual features and/or deviations are also indicated in YANG library data.

Names of Things
***************

YANG modules defines entities of different types, most of them are named. In order to avoid conflicts between names defined in different modules, every such name belongs to the namespace of the module in which it is defined. In Yangson, we represent such qualified names as a tuple ``(name, modname)`` where ``modname`` is the name of the module in which ``name`` is defined. The module :mod:`typealiases` defines an alias for qualified names, namely :const:`QualName`.

For example, the :ref:`turing-machine` module contains (at line 123) the following definition of a *leaf* data node::

  leaf label {
    type string;
    description
      "An arbitrary label of the transition rule.";
   }

In Yangson functions, such a node would be identified with a qualified name ``(label, turing-machine)``.

In YANG modules, however, references to named entities use a prefix form, namely ::

  prefix:name

where ``prefix`` is the prefix with which the module that defines ``name`` is imported. For example, the :ref:`second-tape` module imports the :ref:`turing-machine` module with the prefix ``tm``, and then (at line 15)
uses the prefix form for referring to the derived type ``cell-index`` defined in the latter module::

  type tm:cell-index;

If the reference appears in the same module as the definition of ``name``, then the prefix (and colon) may be omitted.

Class method :meth:`translate_name` in the :class:`Context` class is available for translating a qualified name in prefix form to the tuple form of Yangson.

Finally, JSON-encoded instance documents use yet another set of naming rules that are defined in [Lho16]_. Examples can be found in :ref:`app-b`.

Navigating in Schema and Data Trees
***********************************

The concept of paths in tree structures is familiar from other application domains, such as filesystems or XML. Yangson uses this concept in a number of different ways and variants. Apart from the variability in node naming, as described above, another major reason for the plenitude of path types has to do with the fact that we have to deal with two trees simultaneously: the schema tree and the data tree.

In order to reduce the entropy somewhat, we introduce the following terminology convention:

* Python structures (typically lists) representing tree paths are called *routes*.

* Strings describing tree paths bear other names (path, identifier).

Here is a complete list of various tree path types that are used in Yangson and/or YANG:

*schema route* (type alias :const:`SchemaRoute`)
  List of qualified schema nodes in the tuple form. It is always interpreted relative to a given starting node and identifies its descendant schema node.

  For example, ``[("tape", "turing-machine"), ("cell", "turing-machine")]`` is a valid schema route if the starting node is the ``("turing-machine", "turing-machine")`` container.

*schema node identifier* (see [Bjo16]_, `sec. 6.5`_)
  Sequence of qualified names of schema nodes in the prefix form, separated with slashes. A schema node identifier that starts with a slash is absolute, otherwise it is relative. For example, ``tm:tape/tm:cell`` is a schema node identifier corresponding to the schema route example above.

*data route*
  This is similar to schema route, except that the list contains only names of *data nodes*. This means that other schema nodes (**choice** and **case**) are omitted. A data route also identifes a unique descendant schema node because names of data nodes belonging to the cases of the same choice are requires to be unique (see `sec. 6.2.1`_ in [Bjo16]_).

*XPath 1.0*

*instance route* (class :class:`InstanceRoute`)

*instance identifier*

.. _sec. 6.2.1: https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis-11#section-6.2.1
.. _sec. 6.5: https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis-11#section-6.5
