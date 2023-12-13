.. _cmdline-tools:

==================
Command-line tools
==================

.. toctree::
   :hidden:

   yangson-man
   convert8525-man

Yangson package contains the following command-line tools:

yangson
   implements essential functions such as printing an ASCII tree of the YANG schema or
   validating an instance document.

   :ref:`manual page <yangson-man>`

convert8525
   translates  NMDA-enabled YANG library data [RFC8525]_ (in JSON representation) to
   the old format of [RFC7895]_ that can be used as input to *Yangson* library
   functions and the *yangson* tool.

   :ref:`manual page <convert8525-man>`

A few more specialized Python scripts are available in the project repository, directory `tools/python`__

__ https://github.com/CZ-NIC/yangson/tree/master/tools/python
