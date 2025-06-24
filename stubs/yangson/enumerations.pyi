from enum import Enum

class ContentType(Enum):
    config = 1
    nonconfig = 2
    all = 3

class NodeStatus(Enum):
    current = '+'
    deprecated = 'x'
    obsolete = 'o'

class ValidationScope(Enum):
    syntax = 1
    semantics = 2
    all = 3

class DefaultDeny(Enum):
    none = 1
    write = 2
    all = 3

class Axis(Enum):
    ancestor = 1
    ancestor_or_self = 2
    attribute = 3
    child = 4
    descendant = 5
    descendant_or_self = 6
    following_sibling = 7
    parent = 8
    preceding_sibling = 9
    self = 10

class MultiplicativeOp(Enum):
    multiply = '*'
    divide = 'div'
    modulo = 'mod'
