from .enumerations import Axis as Axis, MultiplicativeOp as MultiplicativeOp
from .exceptions import EndOfInput as EndOfInput, InvalidXPath as InvalidXPath, NotSupported as NotSupported, UnexpectedInput as UnexpectedInput
from .parser import Parser as Parser
from .schemadata import SchemaContext as SchemaContext
from .typealiases import QualName as QualName
from .xpathast import AdditiveExpr as AdditiveExpr, AndExpr as AndExpr, EqualityExpr as EqualityExpr, Expr as Expr, FilterExpr as FilterExpr, FuncBitIsSet as FuncBitIsSet, FuncBoolean as FuncBoolean, FuncCeiling as FuncCeiling, FuncConcat as FuncConcat, FuncContains as FuncContains, FuncCount as FuncCount, FuncCurrent as FuncCurrent, FuncDeref as FuncDeref, FuncDerivedFrom as FuncDerivedFrom, FuncEnumValue as FuncEnumValue, FuncFalse as FuncFalse, FuncFloor as FuncFloor, FuncLast as FuncLast, FuncName as FuncName, FuncNormalizeSpace as FuncNormalizeSpace, FuncNot as FuncNot, FuncNumber as FuncNumber, FuncPosition as FuncPosition, FuncReMatch as FuncReMatch, FuncRound as FuncRound, FuncStartsWith as FuncStartsWith, FuncString as FuncString, FuncStringLength as FuncStringLength, FuncSubstring as FuncSubstring, FuncSubstringAfter as FuncSubstringAfter, FuncSubstringBefore as FuncSubstringBefore, FuncSum as FuncSum, FuncTranslate as FuncTranslate, FuncTrue as FuncTrue, Literal as Literal, LocationPath as LocationPath, MultiplicativeExpr as MultiplicativeExpr, Number as Number, OrExpr as OrExpr, PathExpr as PathExpr, RelationalExpr as RelationalExpr, Root as Root, Step as Step, UnaryMinusExpr as UnaryMinusExpr, UnionExpr as UnionExpr
from _typeshed import Incomplete

class XPathParser(Parser):
    sctx: Incomplete
    def __init__(self, text: str, sctx: SchemaContext) -> None: ...
    def parse(self) -> Expr: ...
