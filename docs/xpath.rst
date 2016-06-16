=================
XPath Expressions
=================

.. productionlist::
   LocationPath: `RelativeLocationPath` | `AbsoluteLocationPath`
   AbsoluteLocationPath: "/" `RelativeLocationPath`?
                       : | `AbbreviatedAbsoluteLocationPath`
   RelativeLocationPath: `Step`
                       : | `RelativeLocationPath` "/" `Step`
		       : | `AbbreviatedRelativeLocationPath`
   Step: `AxisSpecifier` `NodeTest` `Predicate`*
       : | `AbbreviatedStep`
   AxisSpecifier: `AxisName` "::"
                : | `AbbreviatedAxisSpecifier`
   AxisName: "ancestor"
           : | "ancestor-or-self"
	   : | "attribute"
	   : | "child"
	   : | "descendant"
	   : | "descendant-or-self"
	   : | "following"
	   : | "following-sibling"
	   : | "namespace"
	   : | "parent"
	   : | "preceding"
	   : | "preceding-sibling"
	   : | "self"
   NodeTest: `NameTest`
           : | `NodeType` "(" ")"
	   : | "processing-instruction" "(" `Literal` ")"
   Predicate: "[" `PredicateExpr` "]"
   PredicateExpr: `Expr`
   AbbreviatedAbsoluteLocationPath: "//" `RelativeLocationPath`
   AbbreviatedRelativeLocationPath: `RelativeLocationPath` "//" `Step`
   AbbreviatedStep: "." | ".."
   AbbreviatedAxisSpecifier: "@"?
   Expr: `OrExpr`
   PrimaryExpr: `VariableReference`
              : | "(" `Expr` ")"
	      : | `Literal`
	      : | `Number`
	      : | `FunctionCall`
   FunctionCall: `FunctionName` "(" (`Argument` ("," `Argument`)*)? ")"
   Argument: `Expr`
   UnionExpr: `PathExpr`
            : | `UnionExpr` "|" `PathExpr`
   PathExpr: `LocationPath`
           : | `FilterExpr`
	   : | `FilterExpr` "/" `RelativeLocationPath`
	   : | `FilterExpr` "//" `RelativeLocationPath`
   FilterExpr: `PrimaryExpr`
             : | `FilterExpr` `Predicate`
   OrExpr: `AndExpr`
         : | `OrExpr` "or" `AndExpr`
   AndExpr: `EqualityExpr`
          : | `AndExpr` "and" `EqualityExpr`
   EqualityExpr: `RelationalExpr`
               : | `EqualityExpr` "=" `RelationalExpr`
               : | `EqualityExpr` "!=" `RelationalExpr`
   RelationalExpr: `AdditiveExpr`
                 : | `RelationalExpr` "<" `AdditiveExpr`
                 : | `RelationalExpr` ">" `AdditiveExpr`
                 : | `RelationalExpr` "<=" `AdditiveExpr`
                 : | `RelationalExpr` ">=" `AdditiveExpr`
   AdditiveExpr: `MultiplicativeExpr`
               : | `AdditiveExpr` "+" `MultiplicativeExpr`
               : | `AdditiveExpr` "-" `MultiplicativeExpr`
   MultiplicativeExpr: `UnaryExpr`
                     : | `MultiplicativeExpr` `MultiplyOperator` `UnaryExpr`
                     : | `MultiplicativeExpr` "div" `UnaryExpr`
                     : | `MultiplicativeExpr` "mod" `UnaryExpr`
   UnaryExpr: `UnionExpr`
            : "-" `UnaryExpr`
   ExprToken: "(" | ")" | "[" | "]" | "." | ".."
            :| "@" | "," | "::"
            : | `NameTest`
	    : | `NodeType`
	    : | `Operator`
	    : | `FunctionName`
	    : | `AxisName`
	    : | `Literal`
	    : | `Number`
	    : | `VariableReference`
   Literal: '"' [^"]* '"'
          : | "'" [^']* "'"
   Number: `Digits` ("." `Digits`?)?
         : | "." `Digits`
   Digits: [0-9]+
   Operator: `OperatorName`
           : | `MultiplyOperator`
	   : | "/" | "//" | "|" | "+" | "-" | "="
	   : | "!=" | "<" | "<=" | ">" | ">="
   OperatorName: "and" | "or" | "mod" | "div"
   MultiplyOperator: "*"
   FunctionaName: `QName` - `NodeType`
   VariableReference: "$" `QName`
   NameTest: "*"
           : | `NCName` ":" "*"
	   : | `QName`
   NodeType: "comment"
           : | "text"
	   : | "processing-instruction"
	   : | "node"
   ExprWhitespace: `S`
   S: (#x20 | #x9 | #xD | #xA)+
   QName: `PrefixedName`
        : | `UnprefixedName`
   PrefixedName: `Prefix` ":" `LocalPart`
   UnprefixedName: `LocalPart`
   Prefix: `NCName`
   LocalPart: `NCName`
   NCName: `Name` - (`Char`* ":" `Char`*)
   Name: `NameStartChar` `NameChar`*
   NameStartChar: ":" | [A-Z] | "_" | [a-z] | [#xC0-#xD6]
                : | [#xD8-#xF6] | [#xF8-#x2FF] | [#x370-#x37D]
		: | [#x37F-#x1FFF] | [#x200C-#x200D]
		: | [#x2070-#x218F] | [#x2C00-#x2FEF]
		: | [#x3001-#xD7FF] | [#xF900-#xFDCF]
		: | [#xFDF0-#xFFFD] | [#x10000-#xEFFFF]
   NameChar: `NameStartChar` | "-" | "." | [0-9] | #xB7
           : | [#x0300-#x036F] | [#x203F-#x2040]
   Char: #x9 | #xA | #xD | [#x20-#xD7FF]
       : | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
