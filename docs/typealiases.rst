============
Type Aliases
============

.. module:: yangson.typealiases
   :synopsis: Type aliases.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

We define several type aliases shown in the following table to give
more meaning to type hints [PEP484]_. The types ``List``,
``Optional``, ``Tuple`` and ``Union`` are defined in the :mod:`typing`
module.

+-----------------------+----------------------------------------+------+
|Alias                  |Type                                    |Remark|
+=======================+========================================+======+
|:const:`RevisionDate`  |``Optional[str]``                       | \(1) |
+-----------------------+----------------------------------------+------+
|:const:`Uri`           |``str``                                 | \(2) |
+-----------------------+----------------------------------------+------+
|:const:`YangIdentifier`|``str``                                 | \(3) |
+-----------------------+----------------------------------------+------+
|:const:`InstanceName`  |``str``                                 | \(4) |
+-----------------------+----------------------------------------+------+
|:const:`InstanceRoute` |``List[InstanceName]``                  | \(5) |
+-----------------------+----------------------------------------+------+
|:const:`PrefName`      |``str``                                 | \(6) |
+-----------------------+----------------------------------------+------+
|:const:`ScalarValue`   |``Union[int,decimal.Decimal,str]``      | \(7) |
+-----------------------+----------------------------------------+------+
|:const:`QualName`      |``Tuple[YangIdentifier,YangIdentifier]``| \(8) |
+-----------------------+----------------------------------------+------+
|:const:`SchemaRoute`   |``List[QualName]``                      | \(9) |
+-----------------------+----------------------------------------+------+
|:const:`SchemaPath`    |``str``                                 | \(10)|
+-----------------------+----------------------------------------+------+
|:const:`ModuleId`      |``Tuple[YangIdentifier,RevisionDate]``  | \(11)|
+-----------------------+----------------------------------------+------+


**Remarks:**

#. Revision date, defined in [Bjo16]_, sec. `7.1.9`_.

#. Uniform resource identifier [RFC3986]_.

#. YANG identifier, defined in [Bjo16]_, sec. `6.2`_.

#. Qualified name of an instance object member in the form
   [*module_name*``:``]*local_name*.

#. Instance route, see :ref:`sec-paths`.

#. Prefixed name in the form [*prefix*``:``]*local_name*.

#. Scalar value of a **leaf** or **leaf-list** instance.

#. Qualified name of a schema entity (schema node, feature etc.) in
   the form of a tuple. The first component of the tuple is the node
   identifier, and the second component is the namespace (i.e. name of
   the module in which the entity is defined).

#. Schema route, see :ref:`sec-paths`.

#. Schema path, see :ref:`sec-paths`.

#. Module identifier: module name and optional revision date. If the
   revision date is ``None``, the revision is unspecified.

.. _7.1.9: https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis-11#section-7.1.9
.. _6.2: https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis-11#section-6.2
