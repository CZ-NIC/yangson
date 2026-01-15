.. _sec-examples:

*********************************
Example Data Models and Instances
*********************************

Doctest__ snippets in this documentation use the following example data models and their JSON-encoded instances.

__ http://www.sphinx-doc.org/en/stable/ext/doctest.html

.. _sec-ex1:

Example 1
=========

Directory: `docs/examples/ex1`__

__ https://github.com/CZ-NIC/yangson/tree/master/docs/examples/ex1

This example is used in the documentation of the :mod:`.datamodel`
module.

.. rubric:: Schema Tree

.. shtest::
   :cwd: examples/ex1

   $ yangson -t yang-library-ex1.json
   +--rw example-1:greeting? <string>

.. rubric:: YANG Library

File: ``yang-library-ex1.json``

.. literalinclude:: examples/ex1/yang-library-ex1.json
   :language: json

.. rubric:: YANG Module *example-1*

File: ``example-1.yang``

.. literalinclude:: examples/ex1/example-1.yang
   :language: none

.. rubric:: Instance document

File: ``example-data.json``

.. literalinclude:: examples/ex1/example-data.json
   :language: json

.. _sec-ex2:

Example 2
=========

Directory: `docs/examples/ex2`__

__ https://github.com/CZ-NIC/yangson/tree/master/docs/examples/ex2

This example is used in the documentation of the :mod:`.instance` and
:mod:`.instroute` modules, and also in :ref:`quick-start`.

.. rubric:: Schema Tree

.. shtest::
   :cwd: examples/ex2

   $ yangson -p .:../../../yang-modules/ietf -t yang-library-ex2.json
   +--rw example-2:bag
      +--ro bar <boolean>
      +--rw baz? <decimal64>
      +--rw foo# [number]
         +--rw in-words? <string>
         +--rw number <uint64>
         +--rw prime? <boolean>

.. rubric:: YANG Library

File: ``yang-library-ex2.json``

.. literalinclude:: examples/ex2/yang-library-ex2.json
   :language: json

.. rubric:: YANG Module *example-2*

File: ``example-2.yang``

.. literalinclude:: examples/ex2/example-2.yang
   :language: none

.. _mod-ex2-dev:

.. rubric:: YANG Module *example-2-dev* (deviations)

File: ``example-2-dev.yang``

.. literalinclude:: examples/ex2/example-2-dev.yang
   :language: none

.. rubric:: Instance document

File: ``example-data.json``

.. literalinclude:: examples/ex2/example-data.json
   :language: json

The same instance document in YAML representation is used in :ref:`quick-start`:

File: ``example-data.yaml``

.. literalinclude:: examples/ex2/example-data.yaml
   :language: yaml

.. _sec-ex3:

Example 3
=========

Directory: `docs/examples/ex3`__

__ https://github.com/CZ-NIC/yangson/tree/master/docs/examples/ex3

This example is used in the documentation of the :mod:`.schemadata`
module.

.. rubric:: Schema Tree

.. shtest::
   :cwd: examples/ex3

   $ yangson -p .:../../../yang-modules/ietf -t yang-library-ex3.json
   +--rw example-3-a:top
      +--rw bar? <string>
      +--rw example-3-b:bar? <string>
      +--rw baz? <ipv4-address-no-zone(string)>
      +--rw example-3-b:baz? <port-number(uint16)>
      +--rw foo? <empty>
      +--rw quux? <uint8>

.. rubric:: YANG Library

File: ``yang-library-ex3.json``

.. literalinclude:: examples/ex3/yang-library-ex3.json
   :language: json

.. rubric:: YANG Module *example-3-a*

File: ``example-3-a@2017-08-01.yang``

.. literalinclude:: examples/ex3/example-3-a@2017-08-01.yang
   :language: none

.. rubric:: YANG Submodule *example-3-suba*

File: ``example-3-suba@2017-08-01.yang``

.. literalinclude:: examples/ex3/example-3-suba@2017-08-01.yang
   :language: none

.. rubric:: YANG Module *example-3-b*

File: ``example-3-b@2016-08-22.yang``

.. literalinclude:: examples/ex3/example-3-b@2016-08-22.yang
   :language: none

.. _sec-ex4:

Example 4
=========

Directory: `docs/examples/ex4`__

__ https://github.com/CZ-NIC/yangson/tree/master/docs/examples/ex4

This example is used in the documentation of
the :mod:`.schemanode`, :mod:`.xpathast` and :mod:`.xpathparser` modules.

.. rubric:: Schema Tree

.. shtest::
   :cwd: examples/ex4

   $ yangson -p .:../../../yang-modules/ietf -t yang-library-ex4.json
   +--rw example-4-a:bag!
   |  +--ro bar <boolean>
   |  x--rw foo <uint8>
   |  +--rw (opts)?
   |     +--:(a)
   |     |  +--rw baz? <empty>
   |     +--:(example-4-b:fooref)
   |        +--rw fooref? <leafref>
   +--rw example-4-b:quux# <decimal64>

.. rubric:: YANG Library

File: ``yang-library-ex4.json``

.. literalinclude:: examples/ex4/yang-library-ex4.json
   :language: json

.. rubric:: YANG Module *example-4-a*

File: ``example-4-a.yang``

.. literalinclude::  examples/ex4/example-4-a.yang
   :language: none

.. rubric:: YANG Module *example-4-b*

File: ``example-4-b.yang``

.. literalinclude::  examples/ex4/example-4-b.yang
   :language: none

.. rubric:: Instance document

File: ``example-data.json``

.. literalinclude:: examples/ex4/example-data.json
   :language: json

.. _sec-ex5:

Example 5
=========

Directory: `docs/examples/ex5`__

__ https://github.com/CZ-NIC/yangson/tree/master/docs/examples/ex5

This example is used in the documentation of the :mod:`.datatype` and
:mod:`.statement` modules.

.. rubric:: Schema Tree

.. shtest::
   :cwd: examples/ex5

   $ yangson -t yang-library-ex5.json

   +--rw example-5-a:binary-leaf? <binary>
   +--rw example-5-a:bits-leaf? <bits>
   +--rw example-5-a:boolean-leaf? <boolean>
   +--rw example-5-a:decimal64-leaf? <decimal64>
   +--rw example-5-a:empty-leaf? <empty>
   +--rw example-5-a:enumeration-leaf? <enumeration>
   +--rw example-5-a:identityref-leaf? <identityref>
   +--rw example-5-a:instance-identifier-leaf? <instance-identifier>
   +--rw example-5-a:leafref-leaf? <leafref>
   +--rw example-5-a:string-leaf? <my-string(string)>
   +--rw example-5-a:union-leaf? <union>

.. rubric:: YANG Library

File: ``yang-library-ex5.json``

.. literalinclude:: examples/ex5/yang-library-ex5.json
   :language: json

.. rubric:: YANG Module *example-5-a*

File: ``example-5-a.yang``

.. literalinclude::  examples/ex5/example-5-a.yang
   :language: none

.. rubric:: YANG Module *example-5-b*

File: ``example-5-b.yang``

.. literalinclude::  examples/ex5/example-5-b.yang
   :language: none
