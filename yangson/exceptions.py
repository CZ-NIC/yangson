# Copyright © 2016-2019 CZ.NIC, z. s. p. o.
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

"""Exceptions used by the Yangson library.

This module defines the following exceptions:

* :exc:`AnnotationException`: Base class for exceptions related to metadata annotations.
* :exc:`BadSchemaNodeType`: A schema node is of a wrong type.
* :exc:`BadYangLibraryData`: Invalid YANG library data.
* :exc:`CyclicImports`: Imports of YANG modules form a cycle.
* :exc:`DefinitionNotFound`: Requested definition does not exist.
* :exc:`EndOfInput`: Unexpected end of input.
* :exc:`FeaturePrerequisiteError`: Pre-requisite feature isn't supported.
* :exc:`InstanceException`: Base class for exceptions related to operations
  on instance nodes.
* :exc:`InstanceValueError`: The instance value is incompatible with the called method.
* :exc:`InvalidArgument`: Invalid argument of a statement.
* :exc:`InvalidFeatureExpression`: Invalid if-feature expression.
* :exc:`InvalidKeyValue`: Invalid list key or leaf-list value.
* :exc:`InvalidLeafrefPath`: A leafref path is incorrect.
* :exc:`InvalidSchemaPath`: Invalid schema path
* :exc:`InvalidXPath`: An XPath expression is invalid.
* :exc:`MissingAnnotationTarget`: Instance node that is being annotated doesn't exist.
* :exc:`MissingModule`: Abstract exception class – a module is missing.
* :exc:`ModuleContentMismatch`: Abstract exception class – unexpected module name or revision.
* :exc:`ModuleNameMismatch`: The module name doesn't match the expected name.
* :exc:`ModuleNotFound`: A module not found.
* :exc:`ModuleRevisionMismatch`: The module revision doesn't match the expected revision.
* :exc:`ModuleNotImplemented`: A module is not implemented in the data model.
* :exc:`ModuleNotImported`: A module is not imported.
* :exc:`ModuleNotRegistered`: An imported module is not registered in YANG library.
* :exc:`MultipleImplementedRevisions`: A module has multiple implemented revisions.
* :exc:`NonexistentInstance`: Attempt to access an instance node that doesn't
  exist.
* :exc:`NonDataNode`: Attempt to access an instance of non-data node
  (rpc/action/notification).
* :exc:`NonexistentSchemaNode`: A schema node doesn't exist.
* :exc:`NotSupported`: A given XPath 1.0 feature isn't (currently) supported.
* :exc:`ParserException`: Base class for parser exceptions.
* :exc:`RawDataError`: Abstract exception class for errors in raw data.
* :exc:`RawMemberError`: Object member in raw data doesn't exist in the schema.
* :exc:`RawTypeError`: Raw data value is of incorrect type.
* :exc:`SchemaError`: An instance violates a schema constraint.
* :exc:`SchemaNodeException`: Abstract exception class for schema node errors.
* :exc:`SemanticError`: An instance violates a semantic rule.
* :exc:`StatementNotFound`: Required statement does not exist.
* :exc:`UndefinedAnnotation`: Undefined annotation is used.
* :exc:`UnexpectedInput`: Unexpected input.
* :exc:`UnknownPrefix`: Unknown namespace prefix.
* :exc:`ValidationError`: Abstract exception class for instance validation errors.
* :exc:`XPathTypeError`: A subexpression is of a wrong type.
* :exc:`YangsonException`: Base class for all Yangson exceptions.
* :exc:`YangTypeError`: A scalar value is of incorrect type.
"""

from .typealiases import (InstanceName, JSONPointer, ModuleId, PrefName,
                          QualName, ScalarValue, YangIdentifier)


class YangsonException(Exception):
    """Base class for all Yangson exceptions."""
    pass


class AnnotationException(YangsonException):
    """Abstract class for exceptions related to metadata annotations."""

    def __init__(self, path: JSONPointer):
        self.path = path


class MissingAnnotationTarget(AnnotationException):
    """Instance node that is being annotated doesn't exist."""

    def __init__(self, path: JSONPointer, iname: InstanceName):
        super().__init__(path)
        self.iname = iname

    def __str__(self):
        return f"[{self.path}] no instance '{self.iname}'"


class UndefinedAnnotation(AnnotationException):
    """Undefined annotation is used."""

    def __init__(self, path: JSONPointer, aname: InstanceName):
        super().__init__(path)
        self.aname = aname

    def __str__(self):
        return f"[{self.path}] Undefined annotation '{self.aname}'"


class AnnotationTypeError(AnnotationException):
    """Type of annotation is incorrect."""

    def __init__(self, path: JSONPointer, aname: InstanceName, msg: str):
        super().__init__(path)
        self.aname = aname
        self.msg = msg

    def __str__(self):
        return f"[{self.path}] value of '{self.aname}' {self.msg}"


class InvalidArgument(YangsonException):
    """The argument of a statement is invalid."""

    def __init__(self, arg: str):
        self.argument = arg

    def __str__(self):
        return self.argument


class InvalidKeyValue(YangsonException):
    """List key or leaf-list value is invalid."""

    def __init__(self, value: ScalarValue):
        self.value = value

    def __str__(self):
        return str(self.value)


class InstanceException(YangsonException):
    """Abstract class for exceptions related to operations on instance nodes."""

    def __init__(self, path: JSONPointer, message: str):
        self.path = path
        self.message = message

    def __str__(self):
        return f"[{self.path}] {self.message}"


class InstanceValueError(InstanceException):
    """The instance value is incompatible with the called method."""
    pass


class NonexistentInstance(InstanceException):
    """Attempt to access an instance node that doesn't exist."""
    pass


class NonDataNode(InstanceException):
    """Attempt to access an instance of non-data node (rpc/action/notification)."""
    pass


class ParserException(YangsonException):
    """Base class for parser exceptions."""

    def __init__(self, parser: "Parser"):
        self.parser = parser

    def __str__(self) -> str:
        """Print parser state."""
        if "\n" in self.parser.input:
            (line, col) = self.parser.line_column()
            return f"line {line}, column {col}"
        return str(self.parser)


class EndOfInput(ParserException):
    """Unexpected end of input."""
    pass


class UnexpectedInput(ParserException):
    """Unexpected input."""

    def __init__(self, parser: "Parser", expected: str = None):
        super().__init__(parser)
        self.expected = expected

    def __str__(self) -> str:
        """Add info about expected input if available."""
        ex = "" if self.expected is None else ": expected " + self.expected
        return super().__str__() + ex


class InvalidFeatureExpression(ParserException):
    """Invalid **if-feature** expression."""
    pass


class InvalidXPath(ParserException):
    """Exception to be raised for an invalid XPath expression."""
    pass


class NotSupported(ParserException):
    """Exception to be raised for unimplemented XPath features."""

    def __init__(self, parser: "Parser", feature: str):
        super().__init__(parser)
        self.feature = feature

    def __str__(self) -> str:
        return super().str() + ": " + str(self.feature)


class MissingModule(YangsonException):
    """Abstract exception class – a module is missing."""

    def __init__(self, name: YangIdentifier, rev: str = ""):
        self.name = name
        self.rev = rev

    def __str__(self) -> str:
        if self.rev:
            return self.name + "@" + self.rev
        return self.name


class ModuleContentMismatch(YangsonException):
    """Abstract exception class – unexpected module name or revision."""

    def __init__(self, found: YangIdentifier, expected: YangIdentifier):
        self.found = found
        self.expected = expected

    def __str__(self) -> str:
        return f"'{self.found}', expected '{self.expected}'"


class ModuleNameMismatch(ModuleContentMismatch):
    """Parsed module revision doesn't match the expected revision."""
    pass


class ModuleRevisionMismatch(ModuleContentMismatch):
    """Parsed module revision doesn't match the expected revision."""
    pass


class ModuleNotFound(MissingModule):
    """A module or submodule registered in YANG library is not found."""
    pass


class ModuleNotRegistered(MissingModule):
    """A module is not registered in YANG library."""
    pass


class ModuleNotImplemented(MissingModule):
    """A module is not implemented in the data model."""
    pass


class BadYangLibraryData(YangsonException):
    """Broken YANG library data."""

    def __init__(self, message: str):
        self.message = message

    def __str__(self) -> str:
        return self.message


class InvalidSchemaPath(YangsonException):
    """Invalid schema or data path."""

    def __init__(self, path: str):
        self.path = path

    def __str__(self) -> str:
        return self.path


class UnknownPrefix(YangsonException):
    """Unknown namespace prefix."""

    def __init__(self, prefix: YangIdentifier, mid: ModuleId):
        self.prefix = prefix
        self.mid = mid

    def __str__(self) -> str:
        return f"prefix {self.prefix} is not defined in {self.mid}"


class ModuleNotImported(YangsonException):
    """Module is not imported."""

    def __init__(self, mod: YangIdentifier, mid: ModuleId):
        self.mod = mod
        self.mid = mid

    def __str__(self) -> str:
        return f"{self.mod} not imported in {self.mid}"


class FeaturePrerequisiteError(YangsonException):
    """Pre-requisite feature is not supported."""

    def __init__(self, name: YangIdentifier, ns: YangIdentifier):
        self.name = name
        self.ns = ns

    def __str__(self) -> str:
        return f"{self.ns}:{self.name}"


class MultipleImplementedRevisions(YangsonException):
    """A module has multiple implemented revisions."""

    def __init__(self, module: YangIdentifier):
        self.module = module

    def __str__(self) -> str:
        return self.module


class CyclicImports(YangsonException):
    """YANG modules are imported in a cyclic fashion."""
    pass


class SchemaNodeException(YangsonException):
    """Abstract exception class for schema node errors."""

    def __init__(self, qn: QualName):
        self.qn = qn

    def __str__(self) -> str:
        return "/" if self.qn[0] is None else f"{self.qn[1]}:{self.qn[0]}"


class NonexistentSchemaNode(SchemaNodeException):
    """A schema node doesn't exist."""

    def __init__(self, qn: QualName, name: YangIdentifier,
                 ns: YangIdentifier = None):
        super().__init__(qn)
        self.name = name
        self.ns = ns

    def __str__(self) -> str:
        prefix = "" if self.ns is None or self.ns == self.qn[1] else self.ns + ":"
        return f"{prefix}{self.name} under {super().__str__()}"


class BadSchemaNodeType(SchemaNodeException):
    """A schema node is of a wrong type."""

    def __init__(self, qn: QualName, expected: str):
        super().__init__(qn)
        self.expected = expected

    def __str__(self) -> str:
        return super().__str__() + " is not a " + self.expected


class InvalidLeafrefPath(SchemaNodeException):
    """A leafref path is incorrect."""
    pass


class RawDataError(YangsonException):
    """Abstract exception class for errors in raw data."""

    def __init__(self, path: JSONPointer):
        self.path = path

    def __str__(self) -> JSONPointer:
        return self.path


class RawMemberError(RawDataError):
    """Object member in the raw value doesn't exist in the schema."""
    pass


class RawTypeError(RawDataError):
    """Raw value is of an incorrect type."""

    def __init__(self, path: JSONPointer, expected: str):
        super().__init__(path)
        self.message = "expected " + expected

    def __str__(self):
        return f"[{self.path}] {self.message}"


class ValidationError(YangsonException):
    """Abstract exception class for instance validation errors."""

    def __init__(self, path: JSONPointer, tag: str, message: str = None):
        self.path = path
        self.tag = tag
        self.message = message

    def __str__(self) -> str:
        msg = ": " + self.message if self.message else ""
        return f"[{self.path}] {self.tag}{msg}"


class SchemaError(ValidationError):
    """An instance violates a schema constraint."""
    pass


class SemanticError(ValidationError):
    """An instance violates a semantic rule."""
    pass


class YangTypeError(ValidationError):
    """A scalar value doesn't match its expected type."""
    pass


class StatementNotFound(YangsonException):
    """Required statement does not exist."""

    def __init__(self, parent: PrefName, kw: YangIdentifier):
        self.parent = parent
        self.keyword = kw

    def __str__(self) -> str:
        """Print the statement's keyword."""
        return f"`{self.keyword}' in `{self.parent}'"


class DefinitionNotFound(YangsonException):
    """Requested definition does not exist."""

    def __init__(self, kw: YangIdentifier, name: YangIdentifier):
        self.keyword = kw
        self.name = name

    def __str__(self) -> str:
        return f"{self.keyword} {self.name}"


class XPathTypeError(YangsonException):
    """The value of an XPath (sub)expression is of a wrong type."""

    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        return self.value


from .parser import Parser      # NOQA
