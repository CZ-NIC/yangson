# Copyright © 2016, 2017 CZ.NIC, z. s. p. o.
#
# This file is part of Yangson.
#
# Yangson is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Yangson is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with Yangson.  If not, see <http://www.gnu.org/licenses/>.

"""Enumeration classes."""

from enum import Enum

class ContentType(Enum):
    """Enumeration of instance data content types."""

    config = 1
    """Configuration data."""
    nonconfig = 2
    """Data that does not represent configuration."""
    all = 3
    """All data."""

class ValidationScope(Enum):
    """Enumeration of validation scopes."""
    syntax = 1
    """Validation of syntax - schema (including "when"), data types."""
    semantics = 2
    """Validation of semantics ("must" constraints, uniqueness, cardinality,
    referential integrity."""
    all = 3
    """Both syntax and semantics."""

class DefaultDeny(Enum):
    """Enumeration of NACM default deny values."""

    none = 1
    """Data node with no default access restrictions."""
    write = 2
    """Sensitive security system parameter."""
    all = 3
    """Very sensitive security system parameter."""

class Axis(Enum):
    """Enumeration of implemented XPath axes."""

    ancestor = 1
    """Ancestors of the context node."""
    ancestor_or_self = 2
    """Context node and its ancestors."""
    attribute = 3
    """Attributes of the context node."""
    child = 4
    """Children of the context node."""
    descendant = 5
    """Descendants of the context node."""
    descendant_or_self = 6
    """Context node and its descendants."""
    following_sibling = 7
    """Following siblings of the context node."""
    parent = 8
    """Parent of the context node."""
    preceding_sibling = 9
    """Preceding siblings of the context node."""
    self = 10
    """Just the context node."""

class MultiplicativeOp(Enum):
    """Enumeration of XPath multiplicative operators."""

    multiply = 1
    """Multiplication operator (``*``)."""
    divide = 2
    """Division operator (``div``)."""
    modulo = 3
    """Modulo operator (``mod``)."""
