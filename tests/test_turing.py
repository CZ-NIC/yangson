import pytest
from yangson import DataModel

@pytest.fixture
def data_model():
    tdir = "examples/turing/"
    with open(tdir + "yang-library.json", encoding="utf-8") as ylfile:
        ylib = ylfile.read()
    return DataModel.from_yang_library(ylib, tdir)
        
def test_top(data_model):
    top = data_model.get_data_node("/turing-machine:turing-machine")
    assert top.qname == "turing-machine:turing-machine"
