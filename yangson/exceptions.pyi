from .instance import InstanceNode
from .parser import Parser
from .typealiases import InstanceName, JSONPointer, ModuleId, PrefName, QualName, ScalarValue, YangIdentifier
from typing import Optional

class YangsonException(Exception): ...

class AnnotationException(YangsonException):
    path: JSONPointer
    def __init__(self, path: JSONPointer) -> None: ...

class MissingAnnotationTarget(AnnotationException):
    iname: InstanceName
    def __init__(self, path: JSONPointer, iname: InstanceName) -> None: ...

class UndefinedAnnotation(AnnotationException):
    aname: InstanceName
    def __init__(self, path: JSONPointer, aname: InstanceName) -> None: ...

class AnnotationTypeError(AnnotationException):
    aname: InstanceName
    msg: str
    def __init__(self, path: JSONPointer, aname: InstanceName, msg: str) -> None: ...

class InvalidArgument(YangsonException):
    argument: str
    def __init__(self, arg: str) -> None: ...

class InvalidStatement(YangsonException): ...

class InvalidKeyValue(YangsonException):
    value: ScalarValue
    def __init__(self, value: ScalarValue) -> None: ...

class InstanceException(YangsonException):
    instance: InstanceNode
    message: str
    def __init__(self, instance: InstanceNode, message: str) -> None: ...

class InstanceValueError(InstanceException): ...
class NonexistentInstance(InstanceException): ...
class NonDataNode(InstanceException): ...

class ParserException(YangsonException):
    parser: Parser
    def __init__(self, parser: Parser) -> None: ...

class EndOfInput(ParserException): ...

class UnexpectedInput(ParserException):
    expected: Optional[str]
    def __init__(self, parser: Parser, expected: Optional[str] = None) -> None: ...

class InvalidFeatureExpression(ParserException): ...
class InvalidXPath(ParserException): ...

class NotSupported(ParserException):
    feature: str
    def __init__(self, parser: Parser, feature: str) -> None: ...

class MissingModule(YangsonException):
    name: YangIdentifier
    rev: str
    def __init__(self, name: YangIdentifier, rev: str = '') -> None: ...

class MissingModuleNamespace(YangsonException):
    ns: str
    def __init__(self, ns: str) -> None: ...

class ModuleContentMismatch(YangsonException):
    found: YangIdentifier
    expected: YangIdentifier
    def __init__(self, found: YangIdentifier, expected: YangIdentifier) -> None: ...

class ModuleNameMismatch(ModuleContentMismatch): ...
class ModuleRevisionMismatch(ModuleContentMismatch): ...
class ModuleNotFound(MissingModule): ...
class ModuleNotRegistered(MissingModule): ...
class ModuleNotImplemented(MissingModule): ...

class BadYangLibraryData(YangsonException):
    message: str
    def __init__(self, message: str) -> None: ...

class InvalidSchemaPath(YangsonException):
    path: str
    def __init__(self, path: str) -> None: ...

class UnknownPrefix(YangsonException):
    prefix: YangIdentifier
    mid: ModuleId
    def __init__(self, prefix: YangIdentifier, mid: ModuleId) -> None: ...

class ModuleNotImported(YangsonException):
    mod: YangIdentifier
    mid: ModuleId
    def __init__(self, mod: YangIdentifier, mid: ModuleId) -> None: ...

class FeaturePrerequisiteError(YangsonException):
    name: YangIdentifier
    ns: YangIdentifier
    def __init__(self, name: YangIdentifier, ns: YangIdentifier) -> None: ...

class MultipleImplementedRevisions(YangsonException):
    module: YangIdentifier
    def __init__(self, module: YangIdentifier) -> None: ...

class CyclicImports(YangsonException): ...

class SchemaNodeException(YangsonException):
    qn: QualName
    def __init__(self, qn: QualName) -> None: ...

class NonexistentSchemaNode(SchemaNodeException):
    name: YangIdentifier
    ns: Optional[YangIdentifier]
    def __init__(self, qn: QualName, name: YangIdentifier, ns: Optional[YangIdentifier] = None) -> None: ...

class BadSchemaNodeType(SchemaNodeException):
    expected: str
    def __init__(self, qn: QualName, expected: str) -> None: ...

class InvalidLeafrefPath(SchemaNodeException): ...

class RawDataError(YangsonException):
    path: JSONPointer
    def __init__(self, path: JSONPointer) -> None: ...

class RawMemberError(RawDataError): ...

class RawTypeError(RawDataError):
    message: str
    def __init__(self, path: JSONPointer, expected: str) -> None: ...

class ValidationError(YangsonException):
    instance:InstanceName
    tag: str
    message: str
    def __init__(self, instance: InstanceNode, tag: str, message: Optional[str] = None) -> None: ...

class SchemaError(ValidationError): ...
class SemanticError(ValidationError): ...
class YangTypeError(ValidationError): ...

class StatementNotFound(YangsonException):
    parent: PrefName
    keyword: YangIdentifier
    def __init__(self, parent: PrefName, kw: YangIdentifier) -> None: ...

class DefinitionNotFound(YangsonException):
    keyword: YangIdentifier
    name: YangIdentifier
    def __init__(self, kw: YangIdentifier, name: YangIdentifier) -> None: ...

class XPathTypeError(YangsonException):
    value: str
    def __init__(self, value: str) -> None: ...
