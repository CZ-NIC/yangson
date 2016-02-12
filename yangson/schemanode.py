from typing import Dict, List, Optional
from .typealiases import *
from yangson import module

# Type aliases
ModuleDict = Dict[YangIdentifier, List[module.MainModule]]

class SchemaNode(object):
    """Abstract superclass for schema nodes."""

    def __init__(self) -> None:
        """Initialize the instance:"""

        self.parent = None

class Internal(SchemaNode):
    """Abstract superclass for schema nodes that have children."""

    def __init__(self) -> None:
        """Initialize the instance."""
        super().__init__()
        self.children = {}

    def add_child(self, name: NodeName,
                  node: "SchemaNode") -> None:
        """Add `sn` as a child of the receiver.

        :param name: name of the child
        :param node: schema node
        """
        self.children[name] = node
        node.parent = self

class SchemaRoot(Internal):
    """Class for the global schema root."""

    def __init__(self, modules: ModuleDict) -> None:
        """Initialize the instance.

        :param modules: dictionary of modules comprising the schema
        """
        self.modules = modules

    def get_module_revision(
            self, name: YangIdentifier,
            rev: Optional[RevisionDate] = None) -> module.MainModule:
        """Return module with the given parameters.

        :param name: module name
        :param rev: optional revision
        """
        rlist = self.modules[name]
        for m in rlist:
            if rev == m.revision: return m
        if rev is None: return rlist[0]
        
class Terminal(SchemaNode):
    """Abstract superclass for leaves in the schema tree."""
    pass

class Container(Internal):
    """Container node."""
    pass

class Leaf(Terminal):
    """Leaf node."""
    pass

class Augment(Internal):
    """Augment node."""
    pass
