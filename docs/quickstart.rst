.. _quick-start:

***********
Quick Start
***********
.. testcleanup::

   os.chdir("../..")

This section contains a series of hands-on examples that illustrate
basic ways of using the Yangson library. The snippets below should
be enough to get a moderately experienced Python programmer going. The
examples use the YANG data model and instance document
from :ref:`sec-ex2`. Of course, the reader is encouraged to continue
experimenting on his or her own.

.. note::
   Basic operations with YANG data models and instance data, such as
   validation, can be performed easily from the command line using the
   :ref:`yangson-tool` tool that is a part of Yangson distribution.

Prerequisites
=============

First, let's import the necessary Python modules and symbols, and go
to the appropriate directory:

.. doctest::

   >>> import os
   >>> import json
   >>> import yaml
   >>> from yangson import DataModel
   >>> from yangson.enumerations import ContentType
   >>> os.chdir("examples/ex2")

Initializing the Data Model
===========================

Next, we need to initialize the YANG data model. It can be done easily
by reading YANG library data [RFC7895]_ from a file:

.. doctest::

   >>> dm = DataModel.from_file('yang-library-ex2.json',
   ... [".", "../../../yang-modules/ietf"])
   >>> dm.schema.description
   'Data model ID: 9a9b7d2d28d4d78fa42e12348346990e3fb1c1b9'

.. note::

   Distribution directory *tools/python* contains the script
   *mkylib.py* that can help with preparing YANG library data.

This example also uses *deviations* (see sec. `5.6.3`_ in [RFC7950]_) specified in YANG module :ref:`example-2-dev <mod-ex2-dev>`:

* leaf ``unlucky`` is removed from the schema
* a default value is added for the leaf ``prime``.

With the deviations applied, the resulting schema tree looks like this:

.. doctest::

   >>> print(dm.ascii_tree(), end='')
   +--rw example-2:bag
      +--ro bar <boolean>
      +--rw baz? <decimal64>
      +--rw foo# [number]
         +--rw in-words? <string>
         +--rw number <uint64>
         +--rw prime? <boolean>

For the most part, Yangson uses the ASCII tree representation described in [RFC8340]_, the differences are described in the documentation for :meth:`.DataModel.ascii_tree` method.

As we can see in the ASCII tree, the data model contains both configuration data nodes (``rw``) and a single leaf ``bar`` representing state data (``ro``).

Loading and Validating Instance Data
====================================

Now, we can load a JSON-encoded instance document

.. doctest::

   >>> with open('example-data.json') as infile:
   ...   ri = json.load(infile)
   >>> inst = dm.from_raw(ri)

and validate it against the data model:

.. doctest::

   >>> inst.validate(ctype=ContentType.all)

No output means that the validation was successful. Note that we had to use validation for content type ``all`` because the instance document contains both configuration and state data. The default content type for the :meth:`.InstanceNode.validate` method is configuration (``ContentType.config``).

Speaking about content type, it is also worth pointing out that the empty instance is valid as configuration:

.. doctest::

   >>> empty = dm.from_raw({})
   >>> empty.validate()

However, it is *not* valid as content type ``all``, i.e. combined configuration and state data, because the state data leaf ``bar`` is mandatory, which in turn makes the top-level container ``example-2:bag`` mandatory (see sec. `3`_ in [RFC7950]_):

.. doctest::

   >>> empty.validate(ctype=ContentType.all)
   Traceback (most recent call last):
   ...
   yangson.exceptions.SchemaError: {/} missing-data: expected 'example-2:bag'

It is also possible to validate a subtree of instance data against the corresponding schema node. For example:

.. doctest::

   >>> foo2 = inst['example-2:bag']['foo'][2]
   >>> foo2.validate()

We can now print the ASCII tree again, this time without showing the
types but instead displaying *validation counters* that indicate how
many times each schema node has been used for validating instances
during the previous two validation runs on `inst`. This is useful for assessing
the coverage of instance data with respect to the schema.

.. doctest::

   >>> print(dm.ascii_tree(no_types=True, val_count=True), end='')
   +--rw example-2:bag {1}
      +--ro bar {1}
      +--rw baz? {0}
      +--rw foo# [number] {5}
         +--rw in-words? {5}
         +--rw number {5}
         +--rw prime? {3}

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

   >>> inst2.validate(ctype=ContentType.all)

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
   yangson.exceptions.NonexistentInstance: {/example-2:bag} member 'baz'

Why is that? The reason is also hidden in the above definition of
the *baz* leaf: due to the edit that we made, the **when** expression
becomes ``False``, the *baz* leaf isn't therefore valid, and so the
default value doesn't apply.

Breaking the Schema
===================

In order to see validation in action, we will try to violate the data model schema in various ways. First, let's modify the *inw* instance as follows:

.. doctest::

   >>> broken1 = inw.update("six").top()
   >>> broken1.validate(ctype=ContentType.all)
   Traceback (most recent call last):
   ...
   yangson.exceptions.SemanticError: {/example-2:bag/foo} data-not-unique: entry 1

This is correct because the values of the *in-words* leaf are required to be unique among all entries of the *foo* list, but entry #1 now has the same value as the previous entry, namely ``six``.

Next we modify the *name* sibling of our *inw* instance, which
happens to be the key of the *foo* list:

.. doctest::

   >>> broken2 = inw.sibling('number').update(6).top()
   >>> broken2.validate(ctype=ContentType.all)
   Traceback (most recent call last):
   ...
   yangson.exceptions.SemanticError: {/example-2:bag/foo} non-unique-key: 6

In this case, two entries of the *foo* list have the same key, namely ``6``, which illegal.

Another thing that YANG doesn't permit is to install a leaf value that
doesn't conform to the leaf's type, as in the following example:

.. doctest::

   >>> inw.update('INFINITY').validate()
   Traceback (most recent call last):
   ...
   yangson.exceptions.YangTypeError: {/example-2:bag/foo[number="3"]/in-words} invalid-type: must be number in words: INFINITY

This is again correct because the new value ``INFINITY`` doesn't match
the regular expression pattern in the definition of the *in-words*
leaf. Note that the traceback displays the custom error message that
is defined for the pattern.

And note also that validation needn't be performed only on entire data
trees, it can start from any instance node (``inw`` in this case) and
check just its subtree.

And finally, we delete a leaf that's defined as mandatory in the data model:

.. doctest::

   >>> broken3 = inw.up().up().up().delete_item('bar').top()
   >>> broken3.validate(ctype=ContentType.all)
   Traceback (most recent call last):
   ...
   yangson.exceptions.SchemaError: {/example-2:bag} missing-data: expected 'bar'

Instances in YAML Representation
================================

Instance data may alternatively be read from a YAML document:

.. doctest::

   >>> with open('example-data.yaml') as infile:
   ...   ri = yaml.load(infile, Loader=yaml.SafeLoader)
   >>> inst = dm.from_raw(ri)
   >>> inst.validate(ctype=ContentType.all)
   >>> inst.peek(irt)
   'three'

This approach parses YAML data into a :term:`raw value` using the
Python module `PyYAML`_, and relies on the close relationship between
JSON and YAML. However, it hasn't been heavily tested and may fail for
some corner cases. For example, the PyYAML parser interprets
*unquoted* strings ``yes`` and ``no`` as :py:class:`bool` values
``True`` and ``False``.

.. _3: https://www.rfc-editor.org/rfc/rfc7950.html#section-3
.. _5.6.3: https://www.rfc-editor.org/rfc/rfc7950.html#section-5.6.3
.. _PyYAML: https://pypi.org/project/PyYAML/
