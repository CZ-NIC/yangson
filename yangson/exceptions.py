"""Common exception classes."""

from .typealiases import YangIdentifier

class YangsonException(Exception):
    """Base class for all Yangson exceptions."""
    pass

class NonexistentSchemaNode(YangsonException):
    """Exception to be raised when a schema node doesn't exist."""

    def __init__(self, name: YangIdentifier,
                 ns: YangIdentifier = None) -> None:
        self.name = name
        self.ns = ns

    def __str__(self) -> str:
        return "{} in module {}".format(self.name, self.ns)
