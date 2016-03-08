============
Type Aliases
============

.. module:: yangson.typealiases
   :synopsis: Type aliases
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

We define several type aliases shown in the following table to give
more meaning to type hints [PEP484]_. The types ``List``,
``Optional``, ``Tuple`` and ``Union`` are defined in the :mod:`typing`
module.

+--------------+-------------------------+------+
|Alias         |Type                     |Remark|
+==============+=========================+======+
|RevisionDate  |Optional[:class:`str`]   | \(1) |
+--------------+-------------------------+------+
|Uri           |:class:`str`             | \(2) |
+--------------+-------------------------+------+
|YangIdentifier|:class:`str`             | \(3) |
+--------------+-------------------------+------+
|QName         |:class:`str`             | \(4) |
+--------------+-------------------------+------+
|ScalarValue   |Union[:class:`int`,      | \(5) |
|              |:class:`decimal.Decimal`,|      |
|              |:class:`str`]            |      |
+--------------+-------------------------+------+
|NodeName      |Tuple[YangIdentifier,    | \(6) |
|              |YangIdentifier]          |      |
+--------------+-------------------------+------+
|SchemaAddress |List[NodeName]           | \(7) |
+--------------+-------------------------+------+
|ModuleId      |Tuple[YangIdentifier,    | \(8) |
|              |Optional[RevisionDate]]  |      |
+--------------+-------------------------+------+


**Remarks:**

1. Revision date, defined in [Bjo16]_, sec. `7.1.9`_.

2. Uniform resource identifier [RFC3986]_.

3. YANG identifier, defined in [Bjo16]_, sec. `6.2`_.

4. Qualified name of an instance object member in the form
   [*module_name*``:``]*local_name*.

5. Scalar value of a **leaf** or **leaf-list** instance.

6. Node name identifying a *schema node*. The first component of the
   tuple is the namespace (i.e. name of the module in which the node
   is defined), and the second component is the node identifier.

7. Schema address in the form of a sequence of node names.

8. Module identifier: module name and optional revision date. If the
   revision date is ``None``, the revision is unspecified.

.. _7.1.9: https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis-11#section-7.1.9
.. _6.2: https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis-11#section-6.2
