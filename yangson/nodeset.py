# Copyright © 2016–2023 CZ.NIC, z. s. p. o.
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

"""XPath node-set"""
from typing import Callable, Union
from numbers import Number
from .instance import InstanceNode

# Type aliases

NodeExpr = Callable[[InstanceNode], "NodeSet"]
XPathValue = Union["NodeSet", str, float, bool]

def comparison(meth):
    def wrap(self, arg):
        if isinstance(arg, NodeSet):
            for n in arg:
                if n.is_internal():
                    continue
                if meth(self, str(n)):
                    return True
            return False
        return meth(self, arg)
    return wrap


class NodeSet(list):

    def union(self: "NodeSet", ns: "NodeSet") -> "NodeSet":
        paths = set([n.path for n in self])
        return self.__class__(self + [n for n in ns if n.path not in paths])

    def bind(self: "NodeSet", trans: NodeExpr) -> "NodeSet":
        return self.__class__({m.path: m for n in self
                                for m in trans(n)}.values())

    def __float__(self: "NodeSet") -> float:
        return (float(self[0].value) if self else float("nan"))

    def __str__(self: "NodeSet") -> str:
        return str(self[0]) if self else ""

    @comparison
    def __eq__(self: "NodeSet", val: XPathValue) -> bool:
        for n in self:
            if n.is_internal():
                continue
            if isinstance(val, str):
                if str(n) == val:
                    return True
            elif isinstance(n.value, Number):
                if float(n.value) == val:
                    return True
            elif n.value == val:
                return True
        return False

    @comparison
    def __ne__(self: "NodeSet", val: XPathValue) -> bool:
        for n in self:
            if n.is_internal():
                continue
            if isinstance(val, str):
                if str(n) != val:
                    return True
            elif isinstance(n.value, Number):
                if float(n.value) != val:
                    return True
            elif n.value != val:
                return True
        return False

    @comparison
    def __gt__(self: "NodeSet", val: XPathValue) -> bool:
        try:
            val = float(val)
        except (ValueError, TypeError):
            return False
        for n in self:
            try:
                if float(n.value) > val:
                    return True
            except (ValueError, TypeError):
                continue
        return False

    @comparison
    def __lt__(self: "NodeSet", val: XPathValue) -> bool:
        try:
            val = float(val)
        except (ValueError, TypeError):
            return False
        for n in self:
            try:
                if float(n.value) < val:
                    return True
            except (ValueError, TypeError):
                continue
        return False

    @comparison
    def __ge__(self: "NodeSet", val: XPathValue) -> bool:
        try:
            val = float(val)
        except (ValueError, TypeError):
            return False
        for n in self:
            try:
                if float(n.value) >= val:
                    return True
            except (ValueError, TypeError):
                continue
        return False

    @comparison
    def __le__(self: "NodeSet", val: XPathValue) -> bool:
        try:
            val = float(val)
        except (ValueError, TypeError):
            return False
        for n in self:
            try:
                if float(n.value) <= val:
                    return True
            except (ValueError, TypeError):
                continue
        return False
