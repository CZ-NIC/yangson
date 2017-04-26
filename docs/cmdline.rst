.. _man-page:

********************
Command-Line Utility
********************

Synopsis
========

**yangson** [*options*] [<*operation*>] <*yang_library*>

**yangson** -h

Description
===========

:program:`yangson` is a tool for performing selected high-level
operations with a YANG data model and JSON-encoded instance objects
from the command line.

*yang-library* is the name of a file containing JSON-encoded data
model specification in the YANG library format [RFC7895]_. If
no *operation* is specified, the program just parses the data model
and exits.

Operations
==========

.. option:: -h, --help

   Show an overview of the command syntax and exit.

.. option:: -i, --id

   Print the unique module set identifier that can be used, for
   example, as the value of the *module-set-id*
   leaf  in YANG library data. See also :meth:`.DataModel.module_set_id`.

.. option:: -t, --tree

   Print the schema tree of the complete data model as ASCII art. See
   also :meth:`.DataModel.ascii_tree`.

.. option:: -d, --digest

   Print the schema digest of the data model in JSON format. See
   also :meth:`.DataModel.schema_digest`.

.. option:: -v <instance>, --validate <instance>

   Validate an instance object against the data model. The *instance*
   argument is the name of a file containing a JSON-encoded instance
   object.

   Validation can be controlled by means of :option:`--scope`
   and :option:`--ctype` options.

   See also :meth:`.InstanceNode.validate`.

Options
=======

.. option:: -p <module_path>, --path <module_path>

   This option specifies directories to search for YANG modules.
   The *module_path* argument is a colon separated list of directory
   names. By default, the value of the ``YANG_MODPATH`` environment
   variable is used if this variable exists, otherwise the module path
   contains only the current directory.

   All YANG modules specified in YANG library need to be located in
   one of these directories, and their file names have to be in the
   following form:

   .. code-block:: none

      module-or-submodule-name ['@' revision-date] '.yang'

   The part with revision date has to be present if the revision is
   specified for the (sub)module in YANG library.

.. option:: -s <validation_scope>, --scope <validation_scope>

   This option specifies validation scope, and is only relevant when
   used with the :option:`--validate` operation. The choices for
   the *validation_scope* argument are as follows:

   * ``syntax`` – schema constraints (including **when**
     and **if-feature** conditions) and data types;

   * ``semantics`` – **must** constraints, uniqueness of list
     keys, **unique** constraints in lists, integrity of **leafref**
     and **instance-identifier** references;

   * ``all`` – all of the above.

   The default value is ``all``. See also :meth:`.InstanceNode.validate`.

.. option:: -c <content_type>, --ctype <content_type>

   This option specifies the content type of the instance object, and
   is only relevant when used with the :option:`--validate` operation.
   The *content_type* arguments can be one of ``config``
   (configuration data, default), ``nonconfig`` (non-configuration
   data) and ``all`` (all data).  See
   also :meth:`.InstanceNode.validate`.

Environment Variables
=====================

``YANG_MODPATH``
   The default module path, see :option:`--path` option.

Exit Status
===========

+-------+---------------------------------------------+
| Value | Meaning                                     |
+=======+=============================================+
|   0   | No errors                                   |
+-------+---------------------------------------------+
|   1   | Problem with reading or decoding JSON files |
+-------+---------------------------------------------+
|   2   | YANG library or data model problem          |
+-------+---------------------------------------------+
|   3   | Validation of the instance object failed    |
+-------+---------------------------------------------+

Author
======

Ladislav Lhotka <lhotka@nic.cz>
