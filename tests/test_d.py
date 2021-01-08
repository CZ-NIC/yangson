import pytest
from yangson import DataModel
from yangson.instance import RootNode, OutputFilter

"""
Test description

When an array element is filtered out by the OutputFilter class in call to raw_values,
the corresponding raw_value() call returns an empty dictionary to prevent returning
None. These elements should not be added to the array.
"""


@pytest.fixture
def data_model():
    return DataModel.from_file("yang-modules/testd/yang-library.json",
                               ["yang-modules/testd"])


@pytest.fixture
def data():
    _data = {
        "testd:library": {
            "artist": [
                {
                    "name": "invisible"
                }
            ]
        }
    }
    return _data


@pytest.fixture
def instance(data_model, data):
    return data_model.from_raw(data)


class GetFilter(OutputFilter):
    """
    filter out the container in artist that contains the name node
    """
    def begin_member(self, parent: "InstanceNode", node: "InstanceNode", attr: dict)->bool:
        return parent.name != "artist" or node.name != "name"

    def end_member(self, parent: "InstanceNode", node: "InstanceNode", attr: dict)->bool:
        return parent.name != "artist" or node.name != "name"


@pytest.fixture
def outputfilter():
    return GetFilter()


def test_instance(instance, outputfilter):
    export = instance.raw_value(outputfilter)
    library = export["testd:library"]
    artist = library['artist']

    assert(artist == [])
