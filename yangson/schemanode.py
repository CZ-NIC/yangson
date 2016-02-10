from typing import List, Optional
from .typealiases import YangIdentifier

class SchemaNode(object):
    """Abstract superclass for schema nodes."""

    def __init__(self, parent: Optional["Internal"]) -> None:
        """Initialize the instance.

        :param parent: parent node
        """
        self.parent = parent

class DataNode(object):
    """Abstract superclass for data nodes."""

    def __init__(self, name: YangIdentifier,
                 ns: Optional[YangIdentifier]) -> None:
        """Initialize the instance.

        :param name: local name of the node
        :param ns: namespace – the module in which it is defined
        """
        self.name = name
        self.ns = ns

    def namespace(self) -> YangIdentifier:
        """Return namespace (module name) of the receiver."""

        return (self.ns if self.ns else self.parent.namespace())
        
class Internal(SchemaNode):
    """Abstract superclass for schema nodes that have children."""

    def __init__(self, parent: Optional["Internal"],
                 children: List[SchemaNode]) -> None:
        """Initialize the instance.

        :param parent: parent node
        :param children: child nodes
        """
        super().__init__(parent)
        self.children = children

    def add_child(self, sn: "SchemaNode") -> None:
        """Add `sn` as a child of the receiver.

        :param sn: child node
        """
        self.children.append(sn)
        sn.parent = self

class Terminal(SchemaNode):
    """Abstract superclass for leaves in the schema tree."""

    def __init__(self, parent: Optional[Internal]) -> None:
        """Initialize the instance.

        :param parent: parent node
        """
        super().__init__(parent)

class Container(Internal, DataNode):
    """Container node."""

    def __init__(self, name: YangIdentifier,
                 ns: Optional[YangIdentifier] = None,
                 parent: Optional[Internal] = None,
                 children: List[SchemaNode] = []) -> None:
        """Initialize the instance.

        :param name: local name of the node
        :param ns: namespace – the module in which it is defined
        :param parent: parent node
        :param children: child nodes
        """
        DataNode.__init__(self, name, ns)
        Internal.__init__(self, parent, children)

class Leaf(Terminal, DataNode):
    """Leaf node."""

    def __init__(self, name: YangIdentifier,
                 ns: Optional[YangIdentifier] = None,
                 parent: Optional[Internal] = None) -> None:
        """Initialize the instance.

        :param name: local name of the node
        :param ns: namespace – the module in which it is defined
        :param parent: parent node
        """
        DataNode.__init__(self, name, ns)
        Terminal.__init__(self, parent)

class Augment(Internal):
    """Augment node."""

    pass
