.. _yangson-man:

-------------------
yangson manual page
-------------------

.. program:: yangson

Synopsis
========

:program:`yangson` [<options>] [<operation>] <in_file>

:program:`yangson` -h

Description
===========

:program:`yangson` is a tool for performing selected high-level
operations with a YANG data model and JSON-encoded instance objects
from the command line.

*<in_file>* is the name of a file containing either

* a data model specification in JSON representation conforming to the
  original YANG library format of [RFC7895]_, or
* (with the :option:`--pickled` option) a serialized data model object
  generated using the Python `pickle
  <https://docs.python.org/3/library/pickle.html>`_ module. See also
  :option:`--dump` option below.

If no *operation* is specified, the program just parses the data model
and exits.

Operations
==========

.. option:: -d, --digest

   Print the schema digest of the data model in JSON format. See
   also :meth:`.DataModel.schema_digest`.

.. option:: -D <out_file>, --dump <out_file>

   Dump the serialized (pickled) data model object to *<out_file>*.

.. option:: -h, --help

   Show an overview of the command syntax and exit.

.. option:: -i, --id

   Print the unique module set identifier that can be used, for
   example, as the value of the *module-set-id*
   leaf in YANG library data. See also :meth:`.DataModel.module_set_id`.

.. option:: -t, --tree

   Print the schema tree of the complete data model as ASCII art. See
   also :meth:`.DataModel.ascii_tree`.

.. option:: -v <instance>, --validate <instance>

   Validate an instance object against the data model. The *instance*
   argument is the name of a file containing an instance
   object in JSON representation.

   Validation can be controlled by means of :option:`--scope`
   and :option:`--ctype` options.

   See also :meth:`.InstanceNode.validate`.

Options
=======

.. option:: -c <content_type>, --ctype <content_type>

   This option specifies the content type of the instance object, and
   is only relevant when used with the :option:`--validate` operation.
   The *content_type* arguments can be one of ``config``
   (configuration data), ``nonconfig`` (non-configuration
   data) and ``all`` (all data, which is the default).  See
   also :meth:`.InstanceNode.validate`.

.. option:: -n, --no_types

   This option is used to suppress data type information in ASCII tree output.
   It is relevant only for the :option:`--tree` operation.

.. option:: -p <module_path>, --path <module_path>

   This option specifies a list of directories to search for YANG
   modules. It is only applicable if the :option:`--pickled` option is
   **not** used.  The *<module_path>* argument is a colon-separated list
   of directory names. By default, the value of the YANG_MODPATH
   environment variable is used if it is set, otherwise the
   module path contains only the current directory.

   All YANG modules specified in YANG library need to be located in
   one of these directories, and their file names have to be in the
   following form:

   .. code-block:: none

      module-or-submodule-name ['@' revision-date] '.yang'

.. option:: -P, --pickled

   This option indicates that *<in_file>* contents is to be interpreted
   as a serialized (pickled) data model object. See also :option:`--dump`
   option.

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

.. option:: -S <subschema>, --subschema <subschema>

   Parse and validate the instance object against a subschema (RPC or
   notification). The *subschema* argument is a :term:`prefixed name`
   of the selected RPC or notification.

   In this case, the instance object has to be input and/or output
   payload of the selected RPC enclosed in ``<modulename>:input``
   or ``<modulename>:output``, or the notification payload.

   Note that validation may fail if the RPC input/output or notification
   payload contains XPath of leafref references to configuration or state
   data outside the selected RPC or notification.

Environment Variables
=====================

YANG_MODPATH
   A colon-separated list of directories that is used as the default module path,
   see the :option:`--path` option.

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

Ladislav Lhotka <ladislav@lhotka.name>
