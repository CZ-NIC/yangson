**********
Exceptions
**********

.. automodule:: yangson.exceptions
   :members:
   :show-inheritance:

Error Tags
==========

Exceptions related to validity of instance documents, i.e. instances
of the :class:`SchemaError` and :class:`SemanticError` classes, have
the :attr:`tag` attribute containing a semi-formal string identifying
the specific error condition.

Below is the list of error tags used by the *Yangson* library. Some of
them are defined in sec. `15`_ of [RFC7950]_ but *Yangson* also
introduces a number of error tags on its own. Furthermore, error tags
specific to a concrete data model can be defined using the
**error-app-tag** statement in YANG, see sec. `7.5.4.2`_ of [RFC7950]_.
If they are present in the data model, *Yangson* also uses them.

``data-not-unique``
    A **unique** constraint is violated, see sec. `7.8.3`_ of [RFC7950]_.

``instance-required``
    An required instance referred to by a *leafref* or
    *instance-identifier* leaf is missing.

``invalid-type``
    A leaf or leaf-list value has invalid type.

``list-key-missing``
    A key instance is missing in a list entry.

``member-not-allowed``
    An object member is not permitted by the schema.

``missing-data``
    Data required by the schema are missing.

``must-violation``
    A **must** constraint is violated, see sec. `7.5.3`_ of [RFC7950]_.

``non-unique-key``
    Key values of a list instance are not unique.

``repeated-leaf-list-values``
    Values of a leaf-list instance representing configuration are not unique.

``too-few-elements``
    A **min-elements** constraint is violated, see sec. `7.7.5`_ of [RFC7950]_.

``too-many-elements``
    A **max-elements** constraint is violated, see sec. `7.7.6`_ of [RFC7950]_.

.. _15: https://tools.ietf.org/html/rfc7950#section-15
.. _7.5.4.2: https://tools.ietf.org/html/rfc7950#section-7.5.4.2
.. _7.5.3: https://tools.ietf.org/html/rfc7950#section-7.5.3
.. _7.7.5: https://tools.ietf.org/html/rfc7950#section-7.7.5
.. _7.7.6: https://tools.ietf.org/html/rfc7950#section-7.7.6
.. _7.8.3: https://tools.ietf.org/html/rfc7950#section-7.8.3
