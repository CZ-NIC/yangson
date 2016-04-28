==================
Data Model Context
==================

.. module:: yangson.context
   :synopsis: Global repository of data model information and methods.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

The *Yangson* library requires two pieces of information in order to be able to construct the data model:

* *YANG library* data [BBW16]_ with a list of YANG modules that comprise the data  model, and a few other details;

* list of filesystem directories from which the YANG modules can be retrieved.

*Yangson* reads the YANG library data and processes all the modules. This results in the data model schema plus a number of other data structures that are needed in other Python modules. To make them globally available, *Yangson* stores these data structures in the :class:`Context` class.

.. class:: Context

   This class serves as a global repository of data model structures, and also  provides a number of generally useful class methods. No instances of this class are expected to be created.

   .. automethod:: from_yang_library

      This class method bootstraps the data model. The `yang_lib` dictionary is supposed to be parsed from JSON-encoded YANG library data (see the factory method of the :class:`~yangson.datamodel.DataModel` class.
