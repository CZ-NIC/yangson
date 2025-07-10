"""Several additional test for ietf-restconf:yang-data.

"""
import pytest
import json
from yangson import DataModel
from yangson.exceptions import (InvalidStatement, InvalidXPath, YangTypeError, SemanticError,
                                InvalidLeafrefPath)

def test_t1():
    model = DataModel.from_file(
            "yang-modules/test-yang-data/t1/yang-library.json",
            ["yang-modules/test-yang-data/t1", "yang-modules/ietf"]
            )

    _data_main_ok = {
            "t1:main": {
                # identity from same module
                "id-reference": "t1:type-t1",
                # also valid would be:
                #"id-reference": "type-t1",
                },
            }
    cooked = model.from_raw(_data_main_ok)
    cooked.validate()
    assert cooked["t1:main"]["id-reference"].value == ("type-t1", "t1")

    _data_main_ok2 = {
            "t1:main": {
                # identity from imported module
                "id-reference": "defs:type-a",
                },
            }
    cooked = model.from_raw(_data_main_ok2)
    cooked.validate()
    assert cooked["t1:main"]["id-reference"].value == ("type-a", "defs")

    _data_main_ok3 = {
            "t1:main": {
                # identity from imported module (transitive) referenced
                "id-reference": "a:a-tr-derived",
                },
            }
    cooked = model.from_raw(_data_main_ok3)
    cooked.validate()
    assert cooked["t1:main"]["id-reference"].value == ("a-tr-derived", "a")

    _data_main_ok4 = {
            "t1:main": {
                # identity from imported module (transitive) unreferenced
                "id-reference": "trans:tr-derived",
                },
            }
    cooked = model.from_raw(_data_main_ok4)
    cooked.validate()
    assert cooked["t1:main"]["id-reference"].value == ("tr-derived", "trans")

    _data_main_ok5 = {
            "t1:main": {
                # submodule defined identity
                "id-reference": "t1:ts-derived",
                },
            }
    cooked = model.from_raw(_data_main_ok5)
    cooked.validate()
    assert cooked["t1:main"]["id-reference"].value == ("ts-derived", "t1")

    _data_main_err = {
            "t1:main": {
                "id-reference": "c:c-derived",
                },
            }

    cooked = model.from_raw(_data_main_err)
    with pytest.raises(YangTypeError) as errinfo:
        cooked.validate()

    assert errinfo.value.tag == "invalid-type"

    _data_indirect_ok = {
            "t1:indirect": {
                "target": 42,
                #"referenced": "/t1:indirect/target",
                },
            }
    cooked = model.from_raw(_data_indirect_ok)
    cooked.validate()

    # TODO create a more detailed exception for errors connected
    # to usage of not accessible parts of schema tree
    _data_indirect_err = {
            "t1:indirect": {
                "target": 1,
                # referencing identifier from different yang-data schema node
                "referenced": "/t1:main/id-reference",
                },
            }
    cooked = model.from_raw(_data_indirect_err)
    with pytest.raises(YangTypeError):
        cooked.validate()

    _data_indirect_err2 = {
            "t1:indirect": {
                "target": 2,
                # referencing identifier from same module (outside the yang-data)
                "referenced": "/t1:state/state",
                },
            }
    cooked = model.from_raw(_data_indirect_err2)
    with pytest.raises(YangTypeError):
        cooked.validate()

    _data_indirect_err3 = {
            "t1:indirect": {
                "target": 3,
                # referencing identifier from different module
                "referenced": "/b:inaccessible",
                },
            }
    cooked = model.from_raw(_data_indirect_err3)
    with pytest.raises(YangTypeError):
        cooked.validate()

    _data_indirect_ok2 = {
            "t1:indirect": {
                # test that require-instance works well
                "referenced": "/t1:indirect/target",
                },
            }
    cooked = model.from_raw(_data_indirect_ok2)
    cooked.validate()

    _data_ydata_ok = {
            "t1:data": {
                "a": 2,
                },
            }
    cooked = model.from_raw(_data_ydata_ok)
    cooked.validate()

    _data_box_err = {
            "t1:box": {
                "ref": "/t1:box/value",
                },
            }
    cooked = model.from_raw(_data_box_err)
    with pytest.raises(SemanticError):
        cooked.validate()

def test_t2():
    with open("yang-modules/test-yang-data/t2/yang-library.json", mode="r") as file:
        yang_lib_data = json.load(file)

    all_mods = yang_lib_data["ietf-yang-library:modules-state"]["module"]
    # the first element is 'ietf-restconf'; add to make module set referentially complete
    yang_lib_data["ietf-yang-library:modules-state"]["module"] = [all_mods[0], None]

    breakpoint()
    errs = [InvalidStatement, InvalidXPath, InvalidXPath, InvalidXPath, InvalidLeafrefPath, InvalidLeafrefPath, InvalidLeafrefPath, InvalidLeafrefPath]

    # all modules t2-1 ... t2-7 should fail to load
    # because the YANG modules are loaded in the same order in which they appear
    # in the YANG Library "module" list we test that all modules fail by moving them around in the list
    for test in range(len(all_mods) - 1):
        yang_lib_data["ietf-yang-library:modules-state"]["module"][1] = all_mods[1 + test]
        with pytest.raises(errs[test]):
            yang_lib_txt = json.dumps(yang_lib_data)
            model = DataModel(yang_lib_txt, ["yang-modules/test-yang-data/t2", "yang-modules/ietf"])

def test_t3():
    with open("yang-modules/test-yang-data/t3/yang-library.json", mode="r") as file:
        yang_lib_data = json.load(file)

    all_mods = yang_lib_data["ietf-yang-library:modules-state"]["module"]
    # the first element is 'ietf-restconf'
    # the second element is 'ietf-inet-types'; both are added to make module set referentially complete
    yang_lib_data["ietf-yang-library:modules-state"]["module"] = [all_mods[0], all_mods[1], None]

    # all modules t3-01 to t3-11 should fail to load
    # because the YANG modules are loaded in the same order in which they appear
    # in the YANG Library "module" list we test that all modules fail by moving them aroung in the list
    for test in range(len(all_mods) - 2):
        yang_lib_data["ietf-yang-library:modules-state"]["module"][2] = all_mods[2 + test]
        with pytest.raises(InvalidStatement):
            yang_lib_txt = json.dumps(yang_lib_data)
            model = DataModel(yang_lib_txt, ["yang-modules/test-yang-data/t3", "yang-modules/ietf"])

