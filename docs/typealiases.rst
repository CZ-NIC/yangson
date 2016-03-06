============
Type Aliases
============

.. module:: yangson.typealiases
   :synopsis: Type aliases
.. moduleauthor:: Ladislav Lhotka <lhotka@nic.cz>

We define several type aliases shown in the following table to give more meaning to type hints [PEP484].

+----------------+--------------------------------------------------------------+--------+
| Alias          | Type                                                         | Remark |
+================+==============================================================+========+
| Uri            | :class:`str`                                                 | (1)    |
+----------------+--------------------------------------------------------------+--------+
| YangIdentifier | :class:`str`                                                 | (2)    |
+----------------+--------------------------------------------------------------+--------+
| RevisionDate   | ``Optional[``:class:`str```]``                               | (3)    |
+----------------+--------------------------------------------------------------+--------+
| Value          | Union[:class:`int`, :class:`str`, :class:`decimal.Decimal`,	|        |
|                | List["Value"], Dict[QName, "Value"]]				|        |
+----------------+--------------------------------------------------------------+--------+
