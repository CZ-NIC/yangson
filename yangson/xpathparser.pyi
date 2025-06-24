from .enumerations import Axis, MultiplicativeOp
from .exceptions import EndOfInput, InvalidXPath, NotSupported, UnexpectedInput
from .parser import Parser
from .schemadata import SchemaContext
from .typealiases import QualName
from .xpathast import AdditiveExpr, AndExpr, EqualityExpr, Expr, FilterExpr, FuncBitIsSet, FuncBoolean, FuncCeiling, FuncConcat, FuncContains, FuncCount, FuncCurrent, FuncDeref, FuncDerivedFrom, FuncEnumValue, FuncFalse, FuncFloor, FuncLast, FuncName, FuncNormalizeSpace, FuncNot, FuncNumber, FuncPosition, FuncReMatch, FuncRound, FuncStartsWith, FuncString, FuncStringLength, FuncSubstring, FuncSubstringAfter, FuncSubstringBefore, FuncSum, FuncTranslate, FuncTrue, Literal, LocationPath, MultiplicativeExpr, Number, OrExpr, PathExpr, RelationalExpr, Root, Step, UnaryMinusExpr, UnionExpr

class XPathParser(Parser):
    sctx: SchemaContext
    def __init__(self, text: str, sctx: SchemaContext) -> None: ...
    def parse(self) -> Expr: ...
