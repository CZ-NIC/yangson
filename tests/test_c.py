import pytest
from yangson import DataModel

"""
Test description

RpcActionNode is derived fromSchemaTreeNode, but it is not a root node,
so the data_path should be empty and the iname should not be erased.
"""


@pytest.fixture
def data_model():
    return DataModel.from_file("yang-modules/testc/yang-library.json",
                               ["yang-modules/testc"])


def test_schema(data_model):
    rpcs = data_model.get_data_node("/testc:rpcs")
    rpcb = rpcs.get_child("rpcB")

    assert rpcb.data_path() == "/testc:rpcs/rpcB"
    assert rpcb.iname() == "rpcB"
