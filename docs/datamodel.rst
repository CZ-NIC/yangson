==========
Data Model
==========

.. module:: yangson.datamodel
   :synopsis: Data model representation.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

This module provides the :class:`DataModel` class that is one of the two main entry points to the *Yangson* library (class :class:`Instance` is the other).

.. class:: DataModel(yltxt: str, mod_path: List[str])

This class represents a high-level view of the YANG data model. The *yltxt* parameter is JSON text with YANG library dataq
