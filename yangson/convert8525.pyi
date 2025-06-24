from yangson import DataModel
from yangson.enumerations import ContentType
from yangson.exceptions import NonexistentInstance,  RawDataError, ValidationError
from yangson.instance import ArrayEntry
from yangson.typealiases import RawObject

YL7895: str
YL8525: str

class ModuleData:
    name: str
    revision: str
    location: set[str]
    def __init__(self, rfc8525_entry: ArrayEntry) -> None: ...
    def key(self) -> tuple[str, str]: ...
    def merge(self, other: ModuleData) -> None: ...
    def as_raw(self) -> RawObject: ...

class MainModuleData(ModuleData):
    namespace: str
    import_only: bool
    deviation: set[str]
    feature: set[str]
    submodule: dict[tuple[str, str], ModuleData]
    def __init__(self, rfc8525_entry: ArrayEntry, import_only: bool) -> None: ...
    def add_submodule(self, sub_entry: ArrayEntry) -> None: ...
    def merge(self, other: ModuleData) -> None: ...
    def as_raw(self) -> RawObject: ...

def main() -> int: ...
