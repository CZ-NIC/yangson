import pytest
from yangson import DataModel
from yangson.context import Context, BadPath

@pytest.fixture
def data_model():
    tdir = "examples/turing/"
    with open(tdir + "yang-library.json", encoding="utf-8") as ylfile:
        ylib = ylfile.read()
    return DataModel.from_yang_library(ylib, tdir)
        
def test_schema_nodes(data_model):
    top = data_model.get_data_node("/turing-machine:turing-machine")
    assert top.qname == "turing-machine:turing-machine"
    assert top.config == True
    nonex = top.get_child("NONEXISTENT")
    assert nonex is None
    state = top.get_child("state")
    assert state.config == False
    with pytest.raises(BadPath):
        Context.path2address("transition-function")
    label = top.get_schema_descendant(Context.path2address(
        "turing-machine:transition-function/delta/label"))
    assert label.config == True
