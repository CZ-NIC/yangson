import json
from yangson import DataModel

dm = DataModel.from_file('yang-library-ex2.json')
with open('example-data.json') as infile:
    ri = json.load(infile)
inst = dm.from_raw(ri)
iwd = inst.add_defaults()
baz = iwd["example-2:bag"]["baz"]
print(baz)
