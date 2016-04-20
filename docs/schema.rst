===========
YANG Schema
===========

.. module:: yangson.schema
   :synopsis: Classes and methods for working with YANG schema nodes
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

This module offers classes representing YANG schema nodes.

This module defines several type aliases representing “raw” values produced by the JSON parser :func:`json.loads`.

+--------------------+------------------------------+
|Alias               |Type                          |
+====================+==============================+
|:const:`RawObject`  |``Dict[InstanceName,          |
|                    |RawValue]``                   |
+--------------------+------------------------------+
|:const:`RawList`    |``List[RawObject]``           |
+--------------------+------------------------------+
|:const:`RawLeafList`|``List[RawScalar]``           |
+--------------------+------------------------------+
|:const:`RawValue`   |``Union[RawScalar, RawObject, |
|                    |RawList, RawLeafList]``       |
+--------------------+------------------------------+


.. class:: SchemaNode

   This class serves as the top-level abstract superclass for all schema node classes.

   .. attribute:: name

      Name of the schema node.

   .. attribute:: ns

      Namespace of the schema node (= YANG module name).

   .. attribute:: parent

      Parent schema node.

    .. property:: config

       This property
