.. _convert8525-man:

-----------------------
convert8525 manual page
-----------------------

.. program:: convert8525

Synopsis
========

:program:`convert8525` [<options>] <yang_library_8525>

:program:`convert8525` -h

Description
===========

:program:`convert8525` can be used for translating the JSON representation of YANG library data in the new NMDA-enabled format [RFC8525]_ to the original format of [RFC7895]_ that is accepted by *Yangson*.

*yang_library_8525* is the name of the input file with JSON data conforming to [RFC8525]_.

Options
=======

.. option:: -h, --help

   Show an overview of the command syntax and exit.

.. option:: -d <datastore>, --datastore <datastore>

   Build the output YANG library from the specified datastore. The
   *datastore* argument is the key of a ``datastore`` list entry in
   the input YANG library. Note that the namespace qualifier
   ``ietf-datastores:`` has to be removed from the *datastore*
   argument. The default is ``running`` but it does not apply if the
   option :option:`--schema` is used.

.. option:: -s <schema>, --schema <schema>

   Build the output YANG library from the specified schema. The
   *schema* argument is the key of a ``schema`` list entry in the
   input YANG library. This option has no default and is mutually
   exclusive with the :option:`--datastore` option.

.. option:: -p <module_path>, --path <module_path>

   This option specifies directories to search for revisions
   ``2016-06-21`` and ``2019-01-04`` of the YANG module
   ``ietf-yang-library`` as well as all modules imported by them.  The
   *module_path* argument is a colon-separated list of directory
   names. By default, the value of the YANG_MODPATH environment
   variable is used if this variable exists, otherwise the module path
   contains only the current directory.

.. option:: -o <output_file>, --output <output_file>

   Write the output YANG library to *output_file*. Standard output is
   used if this option isn't used.


Environment Variables
=====================

YANG_MODPATH
   A colon-separated list of directories that is used as the default module
   path, see the :option:`--path` option.

Exit Status
===========

+-------+---------------------------------------------+
| Value | Meaning                                     |
+=======+=============================================+
|   0   | No errors                                   |
+-------+---------------------------------------------+
|   1   | Input data unavailable or invalid           |
+-------+---------------------------------------------+
|   2   | Nonexistent datastore or schema             |
+-------+---------------------------------------------+
|   3   | Output file cannot be written               |
+-------+---------------------------------------------+

Author
======

Ladislav Lhotka <ladislav@lhotka.name>
