***********
Quick Start
***********
.. testcleanup::

   os.chdir("../..")

This section contains a series of hands-on examples that illustrate
basic ways of using the *Yangson* library. The snippets below should
be enough to get a moderately experienced Python programmer going. The
examples use the YANG data model and instance document
from :ref:`sec-ex2`. Of course, the reader is encouraged to continue
experimenting on his or her own.

Prerequisites
=============

First, let's import the necessary Python modules and symbols, and go
to the appropriate directory:

.. doctest::

   >>> import os
   >>> import json
   >>> from yangson import DataModel
   >>> os.chdir("examples/ex2")

Initializing the Data Model
===========================

Next, we need to initialize the YANG data model. It can be done easily
by reading YANG library data [RFC7895]_ from a file:

.. doctest::

   >>> dm = DataModel.from_file('yang-library-ex2.json')
   >>> dm.schema.description
   'Data model ID: 9a9b7d2d28d4d78fa42e12348346990e3fb1c1b9'

Here is an ASCII art depicting the schema tree:

.. doctest::

   >>> print(dm.ascii_tree(), end='')
   +--rw example-2:bag
      +--rw bar <boolean>
      +--rw baz? <decimal64>
      +--rw foo* [number]
         +--rw in-words? <string>
         +--rw number <uint8>

Loading and Validating Instance Data
====================================

Now, we can load a JSON-encoded instance document

.. doctest::

   >>> with open('example-data.json') as infile:
   ...   ri = json.load(infile)
   >>> inst = dm.from_raw(ri)

and validate it against the data model:

.. doctest::

   >>> inst.validate()

No output means that the validation was successful.

Moving Around and Editing the Data Tree
=======================================

We can move around the instance data tree, either step by step or
directly to any location by using
an :class:`~.instance.InstanceRoute`. One way to obtain the latter is
to parse it from a RESTCONF :term:`resource identifier`:

.. doctest::

   >>> irt = dm.parse_resource_id('/example-2:bag/foo=3/in-words')
   >>> type(irt)
   <class 'yangson.instance.InstanceRoute'>

No we can go straight to the desired spot, see that we are really
there, and inspect the value of that instance:

.. doctest::

   >>> inw = inst.goto(irt)
   >>> inw.json_pointer()
   '/example-2:bag/foo/1/in-words'
   >>> inw.value
   'three'

We can also change the value:

.. doctest::

   >>> inw2 = inw.update('forty-two')
   >>> inw2.value
   'forty-two'

Instance data is represented as a data structure
called *zipper* [Hue97]_. This structure is *persistent*, which means
that invoking the :meth:`~.InstanceNode.update` method on the *inw*
instance results in a **new** instance, and *inw* hasn't changed at
all – it contains the value of ``three`` as before:

.. doctest::

   >>> inw.value
   'three'

We can move from the new instance *inw2* back to the top, thus
obtaining an edited version of the original data tree:

.. doctest::

   >>> inst2 = inw2.top()

We expect the two data trees to differ in the value of *in-words* leaf
that we modified. To verify it, we can once again use
the :class:`~.instance.InstanceRoute` *irt* that we compiled
previously, this time with the :meth:`~.InstanceNode.peek` method:

.. doctest::

   >>> inst.peek(irt)
   'three'
   >>> inst2.peek(irt)
   'forty-two'

Another nice property of the *zipper* structure is that the two data
trees share their contents to the maximum possible extent – it's kind
of *copy on write*.

So, the new data tree differs from the original but it is nevertheless
still valid:

.. doctest::

   >>> inst2.validate()

Adding Default Values
=====================

We can also add default values as specified in the data model to both
data trees:

.. doctest::

   >>> iwd = inst.add_defaults()
   >>> i2wd = inst2.add_defaults()

Again, it is worth noting that we get new instances whilst the
original ones (*inst* and *inst2*) haven't been touched.

The YANG module *example-2* defines a default value of ``0`` for
the *baz* leaf:

.. code-block:: none

   leaf baz {
     when "not(../foo/in-words = 'forty-two')";
     type decimal64 {
       fraction-digits "7";
     }
     default "0";
   }

So let's see if that default value is in place:

.. doctest::

   >>> iwd['example-2:bag']['baz'].value
   Decimal('0E-7')

Indeed it is – ``Decimal('0E-7')`` is just a fancy way of writing
decimal zero.

However, if we try the same for the other data tree, we don't find the
*baz* instance:

.. doctest::

   >>> i2wd['example-2:bag']['baz'].value
   Traceback (most recent call last):
   ...
   yangson.instance.NonexistentInstance: [/example-2:bag] member 'baz'

Why is that? The reason is also hidden in the above definition of
the *baz* leaf: due to the edit that we made, the **when** expression
becomes ``False``, the *baz* leaf isn't therefore valid, and so the
default value doesn't apply.

Breaking the Schema
===================

Let's also try to violate the data model schema in various ways.
First, we modify the *name* sibling of our *inw* instance, which
happens to be the key of the *foo* list:

.. doctest::

   >>> broken1 = inw.sibling('number').update(6).top()
   >>> broken1.validate()
   Traceback (most recent call last):
   ...
   yangson.schemanode.SemanticError: [/example-2:bag/foo] non-unique-key: 6

Correct! Both entries of the *foo* list now have the same key, namely ``6``.

Other thing that YANG doesn't permit is to install a leaf value that
doesn't conform to the leaf's type, as in the following example:

.. doctest::

   >>> inw.update('INFINITY').validate()
   Traceback (most recent call last):
   ...
   yangson.schemanode.SchemaError: [/example-2:bag/foo/1/in-words] invalid-type: must be number in words

This is again correct because the new value ``INFINITY`` doesn't match
the regular expression pattern in the definition of the *in-words*
leaf. Note that the traceback displays the custom error message that
is defined for the pattern.

And note also that validation needn't be performed only on entire data
trees, it can start from any instance node (``inw`` in this case) and
check just its subtree.

And finally, we delete a leaf that's defined as mandatory in the data model:

.. doctest::

   >>> broken2 = inw.up().up().up().delete_item('bar').top()
   >>> broken2.validate()
   Traceback (most recent call last):
   ...
   yangson.schemanode.SchemaError: [/example-2:bag] missing-data: member 'bar'
