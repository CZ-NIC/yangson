import xml.etree.ElementTree as ET
from typing import Optional

class XMLParser(ET.XMLPullParser):
    def __init__(self, source: Optional[str] = None) -> None: ...
    def parse(self): ... # type: ignore
    @property
    def root(self): ... # type: ignore
