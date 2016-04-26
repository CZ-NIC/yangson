import pytest
from yangson import DataModel
from yangson.schema import NonexistentSchemaNode
from yangson.datatype import YangTypeError
from yangson.context import Context, BadPath, BadPrefName

@pytest.fixture
def data_model():
    tpath = ["examples/test"]
    with open("examples/test/yang-library-data.json",
              encoding="utf-8") as ylfile:
        ylib = ylfile.read()
    return DataModel(ylib, tpath)
        
def test_context(data_model):
    assert len(Context.implement) == 3
    tid = Context._last_revision("test")
    stid = Context._last_revision("subtest")
    tbid = Context._last_revision("testb")
    assert Context.modules[tid].argument == "test"
    assert Context.translate_pname("t:foo", tbid) == ("foo", "test")
    assert Context.translate_pname("sd:foo", stid) == ("foo", "defs")
    with pytest.raises(BadPrefName):
        Context.translate_pname("d:foo", stid)

def test_schema(data_model):
    la = data_model.get_data_node("/test:contA/leafA")
    lb = data_model.get_data_node("/test:contA/leafB")
    lsa = data_model.get_data_node("/test:leafA")
    lab = data_model.get_data_node("/test:contA/testb:leafA")
    assert la.parent == lb.parent
    assert la.mandatory == False
    assert lb.mandatory == True
    assert la.config == True
    assert lb.config == False
    assert la.name == lsa.name and la.ns == lsa.ns
    assert lab.name == "leafA" and lab.ns == "testb"
    assert la.default is None
    assert la.type.default == 111
    assert lab.default == 1
    assert la.type.parse_value("99") == 99
    with pytest.raises(YangTypeError):
        lsa.type.parse_value("99")
