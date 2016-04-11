from yangson import DataModel

def test_turing():
    tdir = "examples/turing/"
    with open(tdir + "yang-library.json", encoding="utf-8") as ylfile:
        ylib = ylfile.read()
    dm = DataModel.from_yang_library(ylib, tdir)
    top = dm.get_data_node("/turing-machine:turing-machine")
    assert top.name == "turing-machine"
    assert top.ns == "turing-machine"
