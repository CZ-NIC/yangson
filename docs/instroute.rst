***************
Instance Routes
***************

.. module:: yangson.instroute
   :synopsis: Routes into instance values

.. testsetup::

   import json
   import os
   from yangson import DataModel
   os.chdir("examples/ex2")

.. testcleanup::

   os.chdir("../..")

The *instroute* module implements the following classes:

* :class:`InstanceRoute`: Route into an instance value.
* :class:`InstanceRouteItem`: Protocol for elements of an instance route.

Doctest__ snippets for this module use the data model and instance
document from :ref:`sec-ex2`.

__ http://www.sphinx-doc.org/en/stable/ext/doctest.html

.. doctest::

   >>> dm = DataModel.from_file('yang-library-ex2.json',
   ... [".", "../../../yang-modules/ietf"])
   >>> with open('example-data.json') as infile:
   ...   ri = json.load(infile)
   >>> inst = dm.from_raw(ri)

.. autoclass:: InstanceRoute
   :show-inheritance:

   Instances of this class can be conveniently created by using one of
   the methods :meth:`~.DataModel.parse_resource_id` and
   :meth:`~.DataModel.parse_instance_id` in the :class:`~.datamodel.DataModel`
   class.

   Instances of this class are also used as the :term:`cooked value`
   of the *instance-identifier* type.

   .. doctest::

      >>> irt = dm.parse_resource_id('/example-2:bag/foo=3/in-words')
      >>> len(irt)
      4

   .. rubric:: Public Methods

   .. automethod:: __str__

      .. doctest::

         >>> str(irt)
         '/example-2:bag/foo[number="3"]/in-words'

   .. automethod:: __hash__


.. autoclass:: InstanceRouteItem
   :show-inheritance:

   Module :mod:`.instance` defines several private classes
   (**MemberName**, **ActionName**, **EntryIndex**, **EntryValue** and
   **EntryKeys**) conforming to the protocol that implement constituents
   of instance routes – selectors of instance nodes.

   .. doctest::

      >>> irt[0].__class__
      <class 'yangson.instance.MemberName'>
      >>> irt[2].__class__
      <class 'yangson.instance.EntryKeys'>

   .. rubric:: Public Methods

   .. automethod:: __eq__

   .. automethod:: __str__

      .. doctest::

         >>> str(irt[0])
         '/example-2:bag'
         >>> str(irt[2])
         '[number="3"]'

   .. method:: goto_step(inst: InstanceNode) -> InstanceNode:

      Return the child of *inst* (an :class:`~.instance.InstanceNode`)
      selected by the receiver.

      .. doctest::

         >>> irt[0].goto_step(inst).json_pointer()
         '/example-2:bag'
         >>> irt[2].goto_step(inst['example-2:bag']['foo']).json_pointer()
         '/example-2:bag/foo/1'

   .. method:: peek_step(val: StructuredValue, sn: DataNode) -> \
           tuple(Value | None, DataNode:

      Return a tuple consisting of:

      * the value selected by the receiver from *val*
      * schema node corresponding to that value.

      Unlike :meth:`goto_step`, this method just peeks into instance
      values and doesn't create a new instance node. In order to be
      able to apply a sequence of such peek steps prescribed by an
      :class:`InstanceRoute`, schema nodes have to be tracked
      separately.

      .. doctest::

         >>> irt[0].peek_step(inst.value, inst.schema_node)[0]['bar']
         True
         >>> irt[0].peek_step(inst.value, inst.schema_node)[1].__class__
         <class 'yangson.schemanode.ContainerNode'>

