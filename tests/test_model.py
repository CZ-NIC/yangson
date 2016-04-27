import pytest
from yangson import DataModel
from yangson.schema import NonexistentSchemaNode
from yangson.datatype import YangTypeError
from yangson.context import Context, BadPath, BadPrefName

@pytest.fixture
def data_model():
    tpath = ["examples/test", "examples/ietf"]
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
    ca = data_model.get_data_node("/test:contA")
    la = ca.get_child("leafA")
    lb = data_model.get_data_node("/test:contA/leafB")
    lsta = data_model.get_data_node("/test:contA/listA")
    cha = data_model.get_schema_node("/test:choiA")
    cc = cha.get_data_child("contC")
    ld = data_model.get_data_node("/test:contC/leafD")
    lla = cc.get_child("llistA")
    chb = data_model.get_schema_node("/test:contA/testb:choiB")
    cb = chb.get_data_child("contB")
    lc = cb.get_data_child("leafC")
    llb = data_model.get_schema_node("/test:choiA/llistB/llistB")
    assert la.parent == lb.parent == chb.parent == ca
    assert (la.mandatory == cb.mandatory == cc.mandatory ==
            ld.mandatory == cha.mandatory == False)
    assert (lb.mandatory == ca.mandatory == lc.mandatory ==
            chb.mandatory == True)
    assert la.config == ca.config == ld.config == lc.config == cha.config == True
    assert lb.config == False
    assert la.ns == ld.ns
    assert lc.ns == "testb"
    assert la.default == 11
    assert ld.default == 199
    assert ld.type.default == 111
    assert lla.default == [42, 54]
    assert lla.type.default == 11
    assert la.type.parse_value("99") == 99
    with pytest.raises(YangTypeError):
        ld.type.parse_value("99")
    assert ca.presence == (not cb.presence) == cc.presence == False
    assert llb.min_elements == 2
    assert llb.max_elements == 3
    assert lla.min_elements == 0
    assert lla.max_elements is None
    assert llb.user_ordered == (not lla.user_ordered) == True
    assert lsta.get_schema_descendant(lsta.keys[1:]).name == "leafF"
    assert lsta.get_schema_descendant(lsta.unique[0][0]).name == "leafG"
