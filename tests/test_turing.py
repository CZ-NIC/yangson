import pytest
from yangson import DataModel
from yangson.schema import NonexistentSchemaNode
from yangson.context import Context, BadPath

@pytest.fixture
def data_model():
    tdir = "examples/turing/"
    with open(tdir + "yang-library.json", encoding="utf-8") as ylfile:
        ylib = ylfile.read()
    return DataModel.from_yang_library(ylib, tdir)
        
def test_schema_nodes(data_model):
    top = data_model.get_data_node("/turing-machine:turing-machine")
    assert top.instance_name() == "turing-machine:turing-machine"
    assert top.config == True
    assert len(top.state_roots()) == 5
    nonex = top.get_child("NONEXISTENT")
    assert nonex is None
    with pytest.raises(NonexistentSchemaNode):
        data_model.parse_instance_id("/turing-machine:turing-machine/ftate")
    state = top.get_child("state")
    assert state.config == False
    assert state.state_roots() == [["turing-machine:turing-machine", "state"]]
    with pytest.raises(BadPath):
        Context.path2route("transition-function")
    label = top.get_schema_descendant(Context.path2route(
        "turing-machine:transition-function/delta/label"))
    assert label.config == True

def test_feature_expr(data_model):
    assert Context.feature_expr(
        "head-stay or not tm:head-stay and not tm:head-stay",
        ("turing-machine", None)) == True
    assert Context.feature_expr(
        "(head-stay or not tm:head-stay) and not tm:head-stay",
        ("turing-machine", None)) == False
