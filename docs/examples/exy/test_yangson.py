import json
from yangson.datamodel import DataModel

MODULE_DIR = "yang-data"
YANG_LIBRARY = "yang-library-data.json"
DATA_FILE = "data.json"

with open(YANG_LIBRARY) as ylfile:
    yl = ylfile.read()
dm = DataModel(yl, [MODULE_DIR])

with open(DATA_FILE, "rt") as fp:
    json_data = dm.from_raw(json.load(fp))

json_data.validate()
print("end")
