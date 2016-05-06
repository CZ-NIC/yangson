==========
Data Model
==========

.. module:: yangson.datamodel
   :synopsis: Data model representation.
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

This module provides the :class:`DataModel` class that is one of the
two main entry points to the *Yangson* library (class
:class:`Instance` is the other).

.. class:: DataModel(yltxt: str, mod_path: List[str])

   This class represents a high-level view of the YANG data model. Its
   constructor has two arguments:

   - *yltxt* (str): JSON text with YANG library data,
   - *mod_path* (List[str]): list of filesystem paths from which the
     YANG modules that are listed in YANG library data can be
     retrieved.

   .. automethod:: from_raw

      See also :term:`raw value`.

   .. automethod:: get_schema_node

      See also :term:`schema path`.

   .. automethod:: get_data_node

      See also :term:`schema path`.

   .. automethod:: parse_instance_id

      The syntax of an instance identifier is given by the production
      rule “instance-identifier” in `sec. 14`_ of [Bjo16]_.

   .. automethod:: parse_resource_id

      The syntax of a resource identifier is given by the production
      rule “api-path” in `sec. 3.5.1.1`_ of [BBW16a]_.

   .. automethod:: ascii_tree

.. _sec. 14: https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis-12#section-14
.. _sec. 3.5.1.1: https://tools.ietf.org/html/draft-ietf-netconf-restconf-13#section-3.5.1.1
