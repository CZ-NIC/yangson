******************
Essential Concepts
******************

Data modelling and schema languages is a complex business – that's why
JSON folks often try to avoid it like plague. We believe, however,
that data modelling greatly helps interoperability and unification of
management interfaces. From a programmer's perspective, data models
not only document the data that our programs process, but they can be
also be used for automating many difficult and/or laborious tasks such
as validating data or building user interfaces.

YANG tries to be easy to read and understandable. Very often, people
are able to understand what YANG data models mean without having read
the YANG language specification. Nevertheless, some concepts and rules
in YANG are less than intuitive, and some are perhaps even slightly
peculiar. This section gives an overview of fundamental YANG concepts
and terms the are needed for understanding the documentation of the
*Yangson* library. However, it is no substitute for studying YANG
documentation, especially [RFC7950]_, [RFC7951]_ and [RFC8407]_.

Another factor that may confuse users of the *Yangson* library is
conflicting terminology: some terms, such as *module*, *instance* or,
for that matter, *library* itself, are used with different meanings
in both Python and YANG. Therefore, when reading the following
sections, it is important to distinguish whether a given text
discusses programming language or data modelling stuff.

Data Models
===========

Data models define and describe some data.  A complete YANG data model
usually corresponds to configuration and management data of a
particular device or service.

YANG distinguishes four different sorts of data:

* configuration
* state data and statistics
* input parameters and output values of RPC (remote procedure call)
  operations
* asynchronous event notifications.

YANG assumes that data of all the sorts listed above are
hierarchically organised, i.e. they form a tree. For example, data
encoded in JSON can be modelled nicely with YANG.

For the specification of a data model, YANG uses both formal means and
textual descriptions that may specify additional rules and
constraints. Such textual descriptions are considered an integral part
of the data model and cannot be ignored!

The formal means include:

* The hierarchical structure of data is described via containment of
  YANG data-defining statements. For example, a container node is
  defined through the **container** statement, and child nodes of this
  container are defined through its substatements.

* YANG also allows for defining which nodes are mandatory and which
  are optional. For lists (sequences of entries of the same type), it
  is possible to specify the minimum and maximum number of entries.

* All scalar parameters have a type. YANG offers a wide variety of
  built-in types, such as *string*, *boolean* and *int32*. It is also
  possible to define *derived* types by taking an existing type
  (built-in or derived), giving it a new name, and optionally
  specifying some restrictions. For example, a restriction that may be
  applied to the *string* type is the *pattern* statement that
  specifies a regular expression that strings belonging to that type
  must match.

* For scalar parameters, it is also possible to define a default value.

For the *Yangson* library, a fully specified data model is the
baseline from which any further processing starts. That's why
operations with isolated YANG modules are not “officially” supported,
i.e. not available through the public API.

Trees and Nodes
===============

In most practical applications of the *Yangson* library, a programmer
needs to work with two fundamental types of trees:

* *data tree* contains real data such as configuration, state data,
  RPC input/output parameters, or notifications. For our purposes, a
  data tree is a JSON document, or a parsed in-memory representation
  thereof.

* *schema tree* allows us to determine which data trees are valid and
  which are not.

An ASCII art diagram of the schema tree can be generated using the
:meth:`.DataModel.ascii_tree` method or :option:`--tree <yangson --tree>`
option of the :ref:`yangson-tool` command-line tool.

Each node in the data tree corresponds to a *data node* in the schema
tree. This looks confusing but in fact it is quite logical: data nodes
are special schema nodes that have counterparts in the data tree.
There are other schema nodes, namely *choice* and *case*, that don't
have this property – they are used in the schema for specifying
possible alternatives of which only one can appear in the data tree.

For every node in the schema tree YANG defines its status, see section `7.21.2`_ in [RFC7950]_. The default status is *current* which means that the node is up to date and valid. The exact meaning of the other two statuses, *deprecated* and *obsolete*, is somewhat unclear. In accordance with the general consensus of the YANG community, *Yangson* adopts the following semantics:

* *deprecated* status is interpreted as a warning to data model
  implementors that the node definition may become obsolete in the
  future. Apart from indicating the status by the ``x`` label in a
  tree diagram as per [RFC8340]_, sec. `2.6`_, *Yangson* makes no
  distinction between the *current* and *deprecated* statuses.

* *obsolete* status means that the node and all its descendants (if
  any) have been removed from the schema. It only appears in tree
  diagrams labelled with ``o``. However, software applications have
  the option to instruct the *Yangson* library to un-obsolete nodes
  appearing in a YANG module. Such nodes are then treated as being
  current except that they carry the status label ``O`` (uppercase oh)
  in tree diagrams. See :ref:`yang-library` below for details.

YANG Modules
============

YANG data models consist of *modules*. Each module defines the schema
for some (usually related) parts of the data trees. Typically, a YANG
module covers a certain subsystem or function. Every module defines a
namespace that needs to be locally unique in a given data model. In
*Yangson*, the namespace is identified by the YANG module name.

YANG modules may also offload parts of their contents
into *submodules*. One can then have one (main) module and any number
of submodules that are included from the main module. The main module
and all its submodules share the same namespace identified by the main
module name.

.. _yang-library:

YANG Library
============

In order to specify a particular data model, one has to decide which
YANG modules will become part of it. For *Yangson*, the selection is
recorded in the form of *YANG library* data according to
[RFC7895]_. And since YANG modules may exist in multiple revisions, a
revision also needs to be specified for each module.

.. note::
   [RFC7895]_ was obsoleted by [RFC8525]_ that introduced a new format
   of YANG library supporting the Network Management Datastore
   Architecture [RFC8342]_. As Yangson currently cannot use multiple
   data model schemas simultaneously, upgrading to the new YANG
   library format would just add complexity with no clear benefits. In
   order to aid users who already work with the new YANG library
   format, the :ref:`convert8525-tool` tool can be used for converting
   it to the old format compatible with Yangson.

YANG also offers two mechanisms that allow for finer-grain control of
data model content:

* *features* are essentially boolean flags that indicate whether an
  optional subsystem or function is supported or not. Parts of the
  schema tree can be labelled as being dependent on a feature: such a
  part exists only if the feature is supported.

* *deviations* allow for specifying that a given implementation
  doesn't exactly follow what's written in a YANG module. In effect, a
  deviation can be understood as a “patch” of the original YANG
  module.

Support for individual features and/or deviations are also indicated
in YANG library data.

*Yangson* introduces a non-standard augmentation to the ``module``
 entries of the YANG library schema: the boolean parameter
 ``yangson-yl:keep-obsolete`` determines whether schema nodes with
 *obsolete* status defined in the given module and its submodules are
 kept in the schema. The entry for a module whose obsolete schema
 nodes are to be retained then may look like this::

    {
      "name": "foo",
      "namespace": "http://example.com/foo",
      "revision": "2022-12-12",
      "conformance-type": "implement",
      "yangson-yl:keep-obsolete": true
    }

If the value of ``yangson-yl:keep-obsolete``is false (which is the default), obsolete nodes are removed from the schema.

YANG module `yangson-yl`__ defining this augmentation is included in the *Yangson* distribution.

__ https://github.com/CZ-NIC/yangson/blob/master/yang-modules/yangson/yangson-yl%402026-03-20.yang

Content Types
=============

YANG distinguishes configuration from state data (see sec. `4.2.3`_ in
[RFC7950]_), and the **config** statement can be used to specify to
which of the two categories a given schema node belongs. A schema node
whose definition doesn't contain the **config** statement inherits
this property from its parent schema node. State data may be embedded
inside configuration, but not vice versa. Finally, for schemas of RPC
operations, actions and notifications, the distinction between
configuration and state data makes no sense at all, and **config**
statements, if present, are ignored there.

The approach adopted by the *Yangson* library is to assign a content
type to every :class:`~.schemadata.SchemaNode`. The values are members of
the enumeration :class:`~.enumerations.ContentType`:

* :attr:`~.ContentType.config`
* :attr:`~.ContentType.nonconfig`
* :attr:`~.ContentType.all`

All non-terminal schema nodes (**container**, **list**, **choice**
and **case**) that represent configuration have the content type
:attr:`~ContentType.all` because they may have both configuration and
state data nodes as descendants.

Content type of terminal data nodes (**leaf**, **leaf-list**, **anydata** and
**anyxml**) reflects their **config**, i.e. it is either
:attr:`~ContentType.config` or :attr:`~ContentType.nonconfig`.

Other nodes always have content type :attr:`~ContentType.nonconfig`.

The method :meth:`.SchemaNode.content_type` returns the content type
of the receiver.

The above rules allow for a straightforward implementation of content
filtering in RESTCONF based on the ``content`` query parameter, see
sec. `4.8.1`_ in [RFC8040]_.

.. _2.6: https://rfc-editor.org/rfc/rfc8340.html#section-2.6
.. _4.2.3: https://rfc-editor.org/rfc/rfc7950.html#section-4.2.3
.. _4.8.1: https://rfc-editor.org/rfc/rfc8040.html#section-4.8.1
.. _7.21.2: https://rfc-editor.org/rfc/rfc7950.html#section-7.21.2
