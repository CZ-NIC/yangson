"""Test examples provided in RFC 8791: YANG Data Structure Extensions."""

import pytest
import re
from yangson import DataModel
from yangson.schemadata import SchemaData
from yangson.instance import ObjectMember
from yangson.xmlparser import XMLParser

@pytest.fixture
def data_model():
    return DataModel.from_file("yang-modules/address-book/yang-library.json", ["yang-modules/address-book", "yang-modules/ietf", 
                                                                               "yang-modules/test" # contains like-yang-instance
                                                                               ])

def strip_pretty(s: str):
    '''
      This function is global because it is used by the various 'test_xml_*' methods.

      It removes all whitespace so that string-comparisons can succeed.
    '''
    return re.sub("[^>]*$", "", re.sub("^[^<]*", "", re.sub(">[\\s\r\n]*<", "><", s)))

@pytest.fixture
def address_book_data():
    _data_json = {
        "example-module:address-book": {
            "address": [        
                {
                    "city": "Bedrock",
                    "first": "Fred",
                    "last": "Flintstone",
                    "street": "301 Cobblestone Way"
                },
                {
                    "city": "Bedrock",
                    "first": "Charlie",
                    "last": "Root",
                    "street": "4711 Cobblestone Way"
                }
            ]
        }
    }

    _data_xml = """
        <content-data xmlns="urn:example:like-yang-instance">
            <address-book xmlns="urn:example:example-module">
                <address>
                    <last>Flintstone</last>
                    <first>Fred</first>
                    <street>301 Cobblestone Way</street>
                    <city>Bedrock</city>
                </address>
                <address>
                    <last>Root</last>
                    <first>Charlie</first>
                    <street>4711 Cobblestone Way</street>
                    <city>Bedrock</city>
                </address>
            </address-book>
        </content-data>
    """

    return (_data_json, strip_pretty(_data_xml))

@pytest.fixture
def address_book_aug_data():
    _data_json = {
        "example-module:address-book": {
            "address": [        
                {
                    "city": "Bedrock",
                    "example-module-aug:zipcode": "70777",
                    "first": "Fred",
                    "last": "Flintstone",
                    "street": "301 Cobblestone Way"
                },
                {
                    "city": "Bedrock",
                    "example-module-aug:zipcode": "70777",
                    "first": "Charlie",
                    "last": "Root",
                    "street": "4711 Cobblestone Way"
                }
            ]
        }
    }

    _data_xml = """
        <content-data xmlns="urn:example:like-yang-instance">
            <address-book xmlns="urn:example:example-module">
                <address>
                    <last>Flintstone</last>
                    <first>Fred</first>
                    <street>301 Cobblestone Way</street>
                    <city>Bedrock</city>
                    <zipcode xmlns="urn:example:example-module-aug">70777</zipcode>
                </address>
                <address>
                    <last>Root</last>
                    <first>Charlie</first>
                    <street>4711 Cobblestone Way</street>
                    <city>Bedrock</city>
                    <zipcode xmlns="urn:example:example-module-aug">70777</zipcode>
                </address>
            </address-book>
        </content-data>
    """

    return (_data_json, strip_pretty(_data_xml))

def test_address_book(data_model, address_book_data):
    for (i, data_format) in enumerate(("json", "xml")):
        #breakpoint()
        if i == 0:
            cooked = data_model.from_raw(address_book_data[i])
        elif i == 1:
            parsed = XMLParser(address_book_data[i])
            precooked = data_model.from_xml(parsed.root)
            # It seems that toplevel XML tag is ignored
            #cooked = precooked["like-yang-instance:content-data"]

        address_book = cooked["example-module:address-book"]
        assert type(address_book) == ObjectMember
        address = address_book["address"]
        assert type(address) == ObjectMember
        assert len(address.value) == 2
        book = address[0]
        assert book["city"].value == "Bedrock"
        assert book["last"].value == "Flintstone"
        book = address[1]
        assert book["first"].value == "Charlie"
        assert book["street"].value == "4711 Cobblestone Way"


def test_address_book_aug(data_model, address_book_aug_data):
    for (i, data_format) in enumerate(("json", "xml")):
        #breakpoint()
        if i == 0:
            cooked = data_model.from_raw(address_book_aug_data[i])
        elif i == 1:
            parsed = XMLParser(address_book_aug_data[i])
            cooked = data_model.from_xml(parsed.root)
        address_book = cooked["example-module:address-book"]
        assert type(address_book) == ObjectMember
        address = address_book["address"]
        assert type(address) == ObjectMember
        assert len(address.value) == 2
        book = address[0]
        assert book["example-module-aug:zipcode"].value == "70777"
        book = address[1]
        assert book["example-module-aug:zipcode"].value == "70777"
