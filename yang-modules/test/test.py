import json
from yangson import DataModel
from yangson.enumerations import ContentType
import xml.etree.ElementTree as ET

dm = DataModel.from_file(
    'yang-library.json', ['.', '../ietf'])
with open('test-data.json') as infile:
    ri = json.load(infile)
inst = dm.from_raw(ri)
root = inst.to_xml()

print(ET.tostring(root))
