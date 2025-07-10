import yangson
import json

#model = yangson.DataModel.from_file("yang-library.json", [".", "../../ietf"])

with open("yang-library.json", mode="r") as file:
    yang_lib = json.load(file)

all_mods = yang_lib["ietf-yang-library:modules-state"]["module"]
yang_lib["ietf-yang-library:modules-state"]["module"] = [all_mods[0], all_mods[3]]
yang_lib_txt = json.dumps(yang_lib)

model = yangson.DataModel(yang_lib_txt, [".", "../../ietf"])

print("message")
