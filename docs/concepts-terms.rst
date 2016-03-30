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

YANG Modules
************

Paths
*****
