import json
import pytest
from decimal import Decimal
from yangson import DataModel
from yangson.exceptions import (
    InvalidArgument, InvalidFeatureExpression, UnknownPrefix,
    NonexistentInstance, NonexistentSchemaNode, RawTypeError,
    SchemaError, XPathTypeError, InvalidXPath, NotSupported)
from yangson.instvalue import ArrayValue
from yangson.schemadata import SchemaContext, FeatureExprParser
from yangson.enumerations import ContentType
from yangson.xpathparser import XPathParser

tree = """+--rw (test:choiA)?
|  +--:(test:caseA)
|  |  +--rw test:contC
|  |  |  +--rw leafD? <typB(int16)>
|  |  |  +--rw llistA* <typA(int16)>
|  |  +--rw test:leafH? <ip-address(union)>
|  +--:(testb:leafQ)
|  |  +--rw testb:leafQ? <empty>
|  +--:(test:llistB)
|     +--rw test:llistB* <ip-address-no-zone(union)>
+--rw test:contA
|  +--rw anydA
|  +--rw anyxA?
|  +--rw (testb:choiB)
|  |  +--:(testb:contB)
|  |  |  +--rw testb:contB!
|  |  |     +--rw leafC <typA(int16)>
|  |  +--:(testb:leafI)
|  |  |  +--rw testb:leafI? <typB(int16)>
|  |  +--:(testb:leafN)
|  |     +--rw testb:leafN? <string>
|  +--rw leafA? <typA(int16)>
|  +--rw leafB <typA(int16)>
|  +--rw testb:leafR? <leafref>
|  +--rw testb:leafS? <instance-identifier>
|  +--rw testb:leafT? <identityref>
|  +--rw testb:leafV? <typE(int16)>
|  +--rw listA* [leafE leafF]
|     +--rw contD
|     |  +---x acA
|     |  |  +--ro input
|     |  |  +--ro output
|     |  |     +--ro leafL <boolean>
|     |  +--rw contE!
|     |  |  +--rw leafJ? <empty>
|     |  |  +--rw leafP? <uint8>
|     |  |  +--rw leafU? <boolean>
|     |  +--rw leafG? <yang-identifier(string)>
|     +--rw leafE <hex-number(string)>
|     +--rw leafF <boolean>
|     +--rw leafW? <typE(leafref)>
+--rw test:contT
|  +--rw binary? <binary>
|  +--rw bits? <typD(bits)>
|  +--rw boolean? <boolean>
|  +--rw decimal64? <decimal64>
|  +--rw enumeration? <typC(enumeration)>
|  +--rw int16? <int16>
|  +--rw int32? <int32>
|  +--rw int64? <int64>
|  +--rw int8? <int8>
|  +--rw string? <string>
|  +--rw uint16? <uint16>
|  +--rw uint32? <uint32>
|  +--rw uint64? <uint64>
|  +--rw uint8? <uint8>
+--rw test:leafX? <port-number(uint16)>
+---n testb:noA
|  +--ro testb:leafO? <boolean>
+---x testb:rpcA
   +--ro input
   |  +--ro testb:leafK? <typA(int16)>
   +--ro output
      +--ro testb:llistC* <boolean>
"""


@pytest.fixture
def data_model():
    return DataModel.from_file("yang-modules/test/yang-library.json",
                               ["yang-modules/test", "yang-modules/ietf"])


@pytest.fixture
def instance(data_model):
    data = """
    {
        "test:llistB": ["::1", "127.0.0.1"],
        "test:leafX": 53531,
        "test:contA": {
            "leafB": 9,
            "listA": [{
                "leafE": "C0FFEE",
                "leafF": true,
                "contD": {
                    "leafG": "foo1-bar",
                    "contE": {
                        "leafJ": [null],
                        "leafP": 10
                    }
                }
            },
            {
                "leafE": "ABBA",
                "leafW": 9,
                "leafF": false
            }],
            "testb:leafR": "C0FFEE",
            "testb:leafT": "test:CC-BY",
            "testb:leafV": 99,
            "anydA": {
                "foo:bar": [1, 2, 3]
            },
            "testb:leafN": "hi!"
        },
        "test:contT": {
            "bits": "dos cuatro",
            "decimal64": "4.50",
            "enumeration": "Hearts"
        }
    }
    """
    return data_model.from_raw(json.loads(data))


def test_schema_data(data_model):
    assert len(data_model.schema_data.implement) == 2
    assert data_model.module_set_id() == "dec8dc2d848e7994c38c5e4ae65bc31383922ce8"
    tid = data_model.schema_data.last_revision("test")
    stid = data_model.schema_data.last_revision("subtest")
    tbid = data_model.schema_data.last_revision("testb")
    assert data_model.schema_data.modules[tid].statement.argument == "test"
    assert data_model.schema_data.translate_pname("t:foo", tbid) == ("foo", "test")
    assert data_model.schema_data.translate_pname("sd:foo", stid) == ("foo", "defs")
    with pytest.raises(UnknownPrefix):
        data_model.schema_data.translate_pname("d:foo", stid)
    assert FeatureExprParser("feA and not (not feA or feB)", data_model.schema_data, tid).parse()
    with pytest.raises(InvalidFeatureExpression):
        FeatureExprParser("feA andnot (not feA or feB)", data_model.schema_data, tid).parse()
    assert not data_model.schema_data.is_derived_from(("all-uses", "test"), ("all-uses", "test"))
    assert data_model.schema_data.is_derived_from(
        ("all-uses", "test"), ("licence-property", "test"))
    assert data_model.schema_data.is_derived_from(("CC-BY-SA", "testb"), ("share-alike", "test"))
    assert not data_model.schema_data.is_derived_from(
        ("CC-BY-SA", "testb"), ("derivatives", "test"))
    assert data_model.schema_data.is_derived_from(("CC-BY-SA", "testb"), ("all-uses", "test"))


def test_schema(data_model):
    ca = data_model.get_data_node("/test:contA")
    la = ca.get_child("leafA")
    lsta = data_model.get_data_node("/test:contA/listA")
    ada = ca.get_child("anydA", "test")
    axa = ca.get_child("anyxA", "test")
    cha = data_model.get_schema_node("/test:choiA")
    cc = cha.get_data_child("contC", "test")
    ld = data_model.get_data_node("/test:contC/leafD")
    lla = cc.get_child("llistA", "test")
    chb = data_model.get_schema_node("/test:contA/testb:choiB")
    cb = chb.get_data_child("contB", "testb")
    ln = chb.get_schema_descendant(data_model.schema_data.path2route(
        "/testb:leafN/leafN"))
    lc = cb.get_data_child("leafC", "testb")
    llb = data_model.get_schema_node("/test:choiA/llistB/llistB")
    lj = data_model.get_data_node("/test:contA/listA/contD/contE/leafJ")
    assert data_model.get_data_node("/test:contA/listA/contD/leafM") is None
    llc = data_model.get_schema_node("/testb:rpcA/output/llistC")
    ll = lsta.get_schema_descendant(data_model.schema_data.path2route(
        "test:contD/acA/output/leafL"))
    assert la.parent == chb.parent == ca
    assert ll.parent.name == "output"
    assert chb in ca._mandatory_children
    assert ada in ca._mandatory_children
    assert (ada.content_type() == axa.content_type() == la.content_type() ==
            ld.content_type() == lc.content_type() == lj.content_type() ==
            ln.content_type() == ContentType.config)
    assert ca.content_type() == cha.content_type() == ContentType.all
    assert ll.content_type() == ContentType.nonconfig
    assert lj.config and ca.config and cha.config and not ll.config
    assert la.ns == ld.ns
    assert lc.ns == "testb"
    assert ld.type.default == 111
    assert lla.type.default == 11
    assert la.type.parse_value("99") == 99
    assert not ca.presence and cb.presence and not cc.presence
    assert llb.min_elements == 2
    assert llb.max_elements == 3
    assert lla.min_elements == llc.min_elements == 0
    assert lla.max_elements is None
    assert llb.user_ordered and (not lla.user_ordered)
    assert lsta.get_schema_descendant(lsta.keys[1:]).name == "leafF"
    assert data_model.get_data_node("/test:contA/listA/contD/leafM") is None
    assert data_model.get_data_node("/testb:noA/leafO") is None


def test_tree(data_model):
    assert data_model.ascii_tree() == tree


def test_types(data_model):
    # type conversions
    def tctest(typ, raw, text, value):
        assert (typ.from_raw(raw) == typ.parse_value(text) == value)
    llb = data_model.get_data_node("/test:llistB").type
    assert "192.168.1.254" in llb
    assert "300.1.1.1" not in llb
    assert "127.0.1" not in llb
    assert llb.parse_value("1.2.3.4.5") is None
    assert "2001:db8:0:2::1" in llb
    assert "::1" in llb
    assert "2001::db8:0:2::1" not in llb
    ct = data_model.get_data_node("/test:contT")
    i8 = ct.get_child("int8", "test").type
    tctest(i8, 703697, "703697", 703697)
    tctest(i8, -6378, "-6378", -6378)
    tctest(i8, True, "3.14", None)
    assert i8.from_yang("-0x18EA") == -i8.from_yang("014352") == -6378
    with pytest.raises(InvalidArgument):
        i8.from_yang("0X1")
    assert 100 in i8
    assert -101 not in i8
    i16 = ct.get_child("int16", "test").type
    assert -32768 in i16
    assert 32768 not in i16
    i32 = ct.get_child("int32", "test").type
    assert -2147483648 in i32
    assert 2147483648 not in i32
    i64 = ct.get_child("int64", "test").type
    assert -9223372036854775808 in i64
    assert 9223372036854775808 not in i64
    assert i64.from_raw("-6378") == -6378
    ui8 = ct.get_child("uint8", "test").type
    assert 150 in ui8
    assert 99 not in ui8
    ui16 = ct.get_child("uint16", "test").type
    assert 65535 in ui16
    assert -1 not in ui16
    ui32 = ct.get_child("uint32", "test").type
    assert 4294967295 in ui32
    assert -1 not in ui32
    ui64 = ct.get_child("uint64", "test").type
    assert 18446744073709551615 in ui64
    assert -1 not in ui64
    tctest(ui64, "6378", "6378", 6378)
    tctest(ui64, 6378, "3.14", None)
    assert ui64.from_raw("-6378") == -6378
    d64 = ct.get_child("decimal64", "test").type
    pi = Decimal("3.141592653589793238")
    tctest(d64, "3.141592653589793238", "3.141592653589793238", pi)
    assert d64.from_raw(3.141592653589793238) is None
    assert pi in d64
    assert 10 not in d64
    assert d64.from_raw("3.14159265358979323846264338327950288") == pi
    assert d64.canonical_string(Decimal("0")) == "0.0"
    st = ct.get_child("string", "test").type
    assert st.length.intervals == [[2, 4], [11], [12]]
    assert "hello world" in st
    assert "hello-world" not in st
    assert "h" not in st
    assert "9 \tx" in st
    assert "xx xabcdefg" not in st
    boo = ct.get_child("boolean", "test").type
    tctest(boo, True, "true", True)
    tctest(boo, "true", "1", None)
    assert False in boo
    assert boo.canonical_string(True) == "true"
    en = ct.get_child("enumeration", "test").type
    assert "Mars" not in en
    assert "Deimos" not in en
    assert en.enum["Hearts"] == 101
    bits = ct.get_child("bits", "test").type
    assert bits.as_int(bits.from_raw("dos cuatro")) == 10
    tctest(bits, "un dos", "un dos", ("un", "dos"))
    assert bits.canonical_string(("cuatro", "dos")) == "dos cuatro"
    assert bits.canonical_string("un dos") is None
    assert "un" not in bits
    assert "tres" not in bits
    assert bits.bit["dos"] == 1
    bin = ct.get_child("binary", "test").type
    kun = "Příliš žluťoučký kůň úpěl ďábelské ódy."
    bv = bin.parse_value(
        b'UMWZw61sacWhIMW+bHXFpW91xI1rw70ga8' +
        b'WvxYggw7pwxJtsIMSPw6FiZWxza8OpIMOzZHku')
    assert bv.decode("utf-8") == kun
    assert bin.canonical_string(kun.encode("utf-8")) == (
        "UMWZw61sacWhIMW+bHXFpW91xI1rw70ga8" +
        "WvxYggw7pwxJtsIMSPw6FiZWxza8OpIMOzZHku")
    lw = data_model.get_data_node("/test:contA/listA/leafW").type
    tctest(lw, 10, "10", 10)
    assert lw.from_yang("0xA") == 10


def test_instance(data_model, instance):
    def axtest(expr, res):
        assert [i.json_pointer() for i in expr] == res
    hi = hash(instance)
    instd = instance.add_defaults()
    hix = hash(instance)
    hid = hash(instd)
    assert hi == hix
    assert hi != hid
    rid1 = data_model.parse_resource_id("/test:contA/listA=C0FFEE,true/contD/contE/leafP")
    iid1 = data_model.parse_instance_id("/test:contA/listA[1]/contD/contE/leafP")
    assert instance.peek(rid1) == instance.peek(iid1)
    rid2 = data_model.parse_resource_id("/test:llistB")
    assert len(instance.peek(rid2)) == 2
    conta = instance["test:contA"]
    la = conta["listA"]
    assert la.schema_node.unique[0][0].evaluate(la[0])[0].value == "foo1-bar"
    la1 = la[-1]
    lt = conta["testb:leafT"]
    assert la1.index == 1
    tbln = conta["testb:leafN"]
    inst1 = la1.put_member("leafE", "ABBA").top()
    inst2 = tbln.update("hello!").top()
    assert instance.value == inst1.value
    assert instance.value != inst2.value
    assert instance.timestamp < inst1.timestamp < inst2.timestamp
    assert inst1.json_pointer() == inst2.json_pointer() == "/"
    assert la1.namespace == "test"
    assert la1["leafE"].namespace == "test"
    assert la1["leafF"].value is False
    with pytest.raises(NonexistentInstance):
        la1["contD"]
    assert la1.json_pointer() == "/test:contA/listA/1"
    assert lt.value == ("CC-BY", "test")
    assert str(lt) == "test:CC-BY"
    assert tbln.namespace == "testb"
    assert tbln.json_pointer() == "/test:contA/testb:leafN"
    assert (instance._ancestors() == instance._preceding_siblings() ==
            instance._following_siblings() == [])
    axtest(instance._ancestors_or_self(), ["/"])
    axtest(la1._ancestors(False), ["/test:contA"])
    axtest(la1._ancestors_or_self(("listA", "test")), ["/test:contA/listA/1"])
    axtest(la1._preceding_siblings(), ["/test:contA/listA/0"])
    axtest(la1._following_siblings(), [])
    assert len(conta._children()) == 10
    axtest(la1._children(("leafF", "test")), ["/test:contA/listA/1/leafF"])
    assert len(instance._descendants(with_self=True)) == 32
    axtest(conta._descendants(("listA", "test")),
           ["/test:contA/listA/0", "/test:contA/listA/1"])
    axtest(tbln._ancestors_or_self(("leafN", "testb")), ["/test:contA/testb:leafN"])


def test_xpath(data_model, instance):
    def xptest(expr, back, res=True, node=instance, module="test"):
        mid = data_model.schema_data.last_revision(module)
        xpp = XPathParser(expr, SchemaContext(data_model.schema_data,
                                              module, mid))
        pex = xpp.parse()
        assert str(pex) == back
        assert pex.evaluate(node) == res
    conta = instance["test:contA"]
    lr = conta["testb:leafR"]
    with pytest.raises(InvalidXPath):
        xptest("foo()", "foo()")
    with pytest.raises(NotSupported):
        xptest("id()", "id()")
    xptest("true()", "true()")
    xptest("false()", "false()", False)
    xptest("1 div 0", "1.0 div 0.0", float('inf'))
    xptest("-1 div 0", "-1.0 div 0.0", float('-inf'))
    xptest("string(0 div 0)", "string(0.0 div 0.0)", "NaN")
    xptest("5 mod 2", "5.0 mod 2.0", 1)
    xptest("5 mod -2", "5.0 mod -2.0", 1)
    xptest("- 5 mod 2", "-5.0 mod 2.0", -1)
    xptest("- 5 mod - 2", "-5.0 mod -2.0", -1)
    xptest("count(t:llistB)", "count(test:llistB)", 2)
    xptest("count(*)", "count(*)", 10, conta)
    xptest("count(*[. > 10])", "count(*[. > 10.0])", 2, conta)
    xptest("-leafA", "-test:leafA", -11, conta)
    xptest(" - - leafA", "test:leafA", 11, conta)
    xptest("llistB = '::1'", 'test:llistB = "::1"')
    xptest("llistB != '::1'", 'test:llistB != "::1"')
    xptest("not(llistB = '::1')", 'not(test:llistB = "::1")', False)
    xptest("llistB[position() = 2]", "test:llistB[position() = 2.0]",
           "127.0.0.1")
    xptest("count(child::llistB/following-sibling::*)",
           "count(test:llistB/following-sibling::*)", 1)
    xptest("leafA > leafB", "test:leafA > test:leafB", node=conta)
    xptest("leafA mod leafB", "test:leafA mod test:leafB", 2, node=conta)
    xptest("listA/contD/contE/leafJ = ''",
           'test:listA/test:contD/test:contE/test:leafJ = ""',
           node=conta)
    xptest("""listA[leafE='C0FFEE' ][ leafF = 'true']
           /contD/contE/leafP = 10""",
           'test:listA[test:leafE = "C0FFEE"][test:leafF = "true"]'
           '/test:contD/test:contE/test:leafP = 10.0',
           node=conta)
    xptest("listA/contD/contE/leafP < leafA | leafB",
           "test:listA/test:contD/test:contE/test:leafP < test:leafA | "
           "test:leafB", node=conta)
    xptest("listA/contD/contE/leafP > leafA | leafB",
           "test:listA/test:contD/test:contE/test:leafP > test:leafA | "
           "test:leafB", node=conta)
    xptest("listA/contD/contE/leafP = leafA | /contA/leafB",
           "test:listA/test:contD/test:contE/test:leafP = test:leafA | "
           "/test:contA/test:leafB", False, conta)
    xptest("/t:contA/t:listA[t:leafE=current()]/t:contD/t:leafG = 'foo1-bar'",
           "/test:contA/test:listA[test:leafE = current()]/"
           'test:contD/test:leafG = "foo1-bar"',
           node=lr, module="testb")
    xptest("../leafN = 'hi!'", '../testb:leafN = "hi!"',
           node=lr, module="testb")
    xptest("local-name()", "local-name()", "")
    xptest("name()", "name()", "")
    xptest("local-name(t:contA)", "local-name(test:contA)", "contA")
    xptest("name(t:contA)", "name(test:contA)", "test:contA")
    xptest("local-name()", "local-name()", "leafR", lr)
    xptest("name()", "name()", "testb:leafR", lr)
    xptest("name(../t:listA)", "name(../test:listA)", "listA", lr, "testb")
    xptest("count(descendant-or-self::*)", "count(descendant-or-self::*)", 32)
    xptest("count(descendant::t:leafE)", "count(descendant::test:leafE)", 2)
    xptest("count(preceding-sibling::*)", "count(preceding-sibling::*)",
           0, lr, "testb")
    xptest("count(following-sibling::*)", "count(following-sibling::*)",
           0, lr, "testb")
    xptest("count(descendant-or-self::contA/descendant-or-self::contA)",
           "count(descendant-or-self::test:contA/"
           "descendant-or-self::test:contA)",
           1, conta)
    xptest("count(descendant-or-self::contA/descendant::contA)",
           "count(descendant-or-self::test:contA/descendant::test:contA)",
           0, conta)
    xptest("listA[last()-1]/following-sibling::*/leafE = 'ABBA'",
           'test:listA[last() - 1.0]/following-sibling::*/test:leafE = "ABBA"',
           node=conta)
    xptest("count(//contD/parent::*/following-sibling::*/*)",
           "count(//test:contD/parent::*/following-sibling::*/*)", 4)
    xptest("//leafP = 10", "//test:leafP = 10.0")
    xptest("""count(listA[leafE = 'C0FFEE' and leafF = true()]//
           leafP/ancestor::node())""",
           'count(test:listA[test:leafE = "C0FFEE" and test:leafF = true()]//'
           "test:leafP/ancestor::node())", 5, conta)
    xptest("../* > 9", "../* > 9.0", node=lr, module="testb")
    xptest("local-name(ancestor-or-self::contA)",
           "local-name(ancestor-or-self::test:contA)",
           "contA", conta)
    xptest("string(1.0)", "string(1.0)", "1")
    xptest("string(true())", "string(true())", "true")
    xptest("string(1 = 2)", "string(1.0 = 2.0)", "false")
    xptest("string(t:contT/t:decimal64)", "string(test:contT/test:decimal64)",
           "4.5")
    xptest("string()", "string()", "C0FFEE", lr)
    xptest("concat(../t:leafA, 'foo', ., true())",
           'concat(../test:leafA, "foo", ., true())',
           "11fooC0FFEEtrue", lr, "testb")
    with pytest.raises(InvalidXPath):
        xptest("concat()", "concat()")
    xptest("starts-with(., 'C0F')", 'starts-with(., "C0F")', True, lr, "testb")
    xptest('starts-with(//listA//leafP, "1")',
           'starts-with(//test:listA//test:leafP, "1")')
    xptest("contains(., '0FF')", 'contains(., "0FF")', True, lr, "testb")
    xptest("not(contains(../leafN, '!!'))",
           'not(contains(../testb:leafN, "!!"))', True, lr, "testb")
    xptest("substring-before(//decimal64, '.')",
           'substring-before(//test:decimal64, ".")', "4")
    xptest("substring-after(//decimal64, '.')",
           'substring-after(//test:decimal64, ".")', "5")
    xptest("substring('12345', 1.5, 2.6)",
           'substring("12345", 1.5, 2.6)', "234")
    xptest("substring('12345', 0, 3)", 'substring("12345", 0.0, 3.0)', "12")
    xptest("substring('12345', 0 div 0, 3)",
           'substring("12345", 0.0 div 0.0, 3.0)', "")
    xptest("substring('12345', 1.0, 0.0 div 0.0)",
           'substring("12345", 1.0, 0.0 div 0.0)', "")
    xptest("substring('12345', -42, 1 div 0)",
           'substring("12345", -42.0, 1.0 div 0.0)', "12345")
    xptest("substring('12345', -1 div 0, 1 div 0)",
           'substring("12345", -1.0 div 0.0, 1.0 div 0.0)', "")
    xptest("substring('12345', -1 div 0)", 'substring("12345", -1.0 div 0.0)',
           "12345")
    xptest('substring(//listA[last()]/leafE, "3")',
           'substring(//test:listA[last()]/test:leafE, "3")', "BA")
    xptest("string-length(llistB)", "string-length(test:llistB)", 3)
    xptest("string-length() = 6", "string-length() = 6.0", node=lr)
    xptest("""normalize-space('  \tfoo   bar
           baz    ')""",
           'normalize-space("  &#9;foo   bar&#10;           baz    ")',
           "foo bar baz")
    xptest("translate(., 'ABCDEF', 'abcdef')",
           'translate(., "ABCDEF", "abcdef")', "c0ffee", lr)
    xptest("translate('--abcd--', 'abc-', 'ABC')",
           'translate("--abcd--", "abc-", "ABC")', "ABCd")
    xptest("boolean(foo)", "boolean(test:foo)", False)
    xptest("boolean(descendant::t:leafE)", "boolean(descendant::test:leafE)")
    xptest("boolean(10 mod 2)", "boolean(10.0 mod 2.0)", False)
    xptest("boolean(string(llistB))", "boolean(string(test:llistB))")
    xptest("number(leafA)", "number(test:leafA)", 11, conta)
    xptest("string(number())", "string(number())", "NaN", lr, "testb")
    xptest("string(number('foo'))", 'string(number("foo"))', "NaN")
    xptest("number(true()) = 1", "number(true()) = 1.0")
    xptest("number(false()) = 0", "number(false()) = 0.0")
    xptest("sum(leafA | leafB)", "sum(test:leafA | test:leafB)", 20, conta)
    xptest("string(sum(//leafE))", "string(sum(//test:leafE))", "NaN")
    xptest("sum(//leafF)", "sum(//test:leafF)", 1)
    with pytest.raises(XPathTypeError):
        xptest("sum(42)", "sum(42.0)")
    xptest("floor(t:contT/t:decimal64)", "floor(test:contT/test:decimal64)", 4)
    xptest("ceiling(t:contT/t:decimal64)",
           "ceiling(test:contT/test:decimal64)", 5)
    xptest("round(t:contT/t:decimal64)", "round(test:contT/test:decimal64)", 5)
    xptest("round(- 6.5)", "round(-6.5)", -6)
    xptest("round(1 div 0)", "round(1.0 div 0.0)", float("inf"))
    xptest("round(-1 div 0)", "round(-1.0 div 0.0)", float("-inf"))
    xptest("string(round(0 div 0))", "string(round(0.0 div 0.0))", "NaN")
    xptest("re-match(//t:leafE, '[0-9a-fA-F]*')",
           're-match(//test:leafE, "[0-9a-fA-F]*")')
    xptest("re-match(count(//t:leafE), '[0-9]*')",
           're-match(count(//test:leafE), "[0-9]*")')
    xptest(r"re-match('1.22.333', '\d{1,3}\.\d{1,3}\.\d{1,3}')",
           r're-match("1.22.333", "\d{1,3}\.\d{1,3}\.\d{1,3}")')
    xptest("re-match('aaax', 'a*')", 're-match("aaax", "a*")', False)
    xptest("re-match('a\nb', '.*')", 're-match("a&#10;b", ".*")', False)
    xptest("re-match('a\nb', '[a-z\n]*')",
           're-match("a&#10;b", "[a-z&#10;]*")')
    xptest("deref(.)/../t:leafF", "deref(.)/../test:leafF", True, lr, "testb")
    xptest("deref(../leafS)", "deref(../testb:leafS)", 9, lr, "testb")
    xptest("count(deref(../leafS) | ../leafN)",
           "count(deref(../testb:leafS) | ../testb:leafN)", 2, lr, "testb")
    xptest("derived-from-or-self(../leafT, 't:CC-BY')",
           'derived-from-or-self(../testb:leafT, "t:CC-BY")',
           True, lr, "testb")
    xptest("derived-from(../leafT, 't:CC-BY')",
           'derived-from(../testb:leafT, "t:CC-BY")', False, lr, "testb")
    xptest("derived-from(../leafT, 't:derivatives')",
           'derived-from(../testb:leafT, "t:derivatives")', True, lr, "testb")
    xptest("derived-from(../leafT, 't:share-alike')",
           'derived-from(../testb:leafT, "t:share-alike")', False, lr, "testb")
    xptest("derived-from(../leafT, 't:licence-property')",
           'derived-from(../testb:leafT, "t:licence-property")',
           True, lr, "testb")
    xptest("derived-from(., 't:CC-BY')", 'derived-from(., "t:CC-BY")',
           False, lr, "testb")
    xptest("derived-from(., 'CC-BY')", 'derived-from(., "CC-BY")',
           False, conta)
    xptest("enum-value(//enumeration)", "enum-value(//test:enumeration)", 101)
    xptest("string(enum-value(foo))", "string(enum-value(test:foo))", "NaN")
    xptest("string(enum-value(.))", "string(enum-value(.))", "NaN", conta)
    xptest("string(enum-value(.))", "string(enum-value(.))",
           "NaN", lr, "testb")
    xptest("bit-is-set(//bits, 'dos') and bit-is-set(//bits, 'cuatro')",
           'bit-is-set(//test:bits, "dos") and '
           'bit-is-set(//test:bits, "cuatro")')
    xptest("not(bit-is-set(foo, bar))", "not(bit-is-set(test:foo, test:bar))")
    xptest("bit-is-set(., 'dos')", 'bit-is-set(., "dos")', False, conta)


def test_instance_paths(data_model, instance):
    rid1 = data_model.parse_resource_id("/test:contA/testb:leafN")
    rid2 = data_model.parse_resource_id(
        "/test:contA/listA=C0FFEE,true/contD/contE")
    iid1 = data_model.parse_instance_id("/test:contA/testb:leafN")
    iid2 = data_model.parse_instance_id(
        "/test:contA/listA[leafE='C0FFEE'][leafF = 'true']/contD/contE")
    iid3 = data_model.parse_instance_id("/test:contA/listA[1]/contD/contE")
    bad_pth = "/test:contA/listA=ABBA,true/contD/contE"
    assert instance.peek(rid1) == instance.peek(iid1) == "hi!"
    assert (instance.goto(rid2)["leafP"].value ==
            instance.goto(iid2)["leafP"].value ==
            instance.goto(iid3)["leafP"].value == 10)
    with pytest.raises(NonexistentSchemaNode):
        data_model.parse_resource_id("/test:contA/leafX")
    assert str(data_model.parse_instance_id(
        "/test:contA/llX[. = 'foo']")) == '/test:contA/llX[.="foo"]'
    assert instance.peek(data_model.parse_resource_id(bad_pth)) is None
    with pytest.raises(NonexistentInstance):
        instance.goto(data_model.parse_resource_id(bad_pth))


def test_edits(data_model, instance):
    laii = data_model.parse_instance_id("/test:contA/listA")
    la = instance.goto(laii)
    inst1 = la[1].update(
        {"leafE": "B00F", "leafF": False}, raw=True).top()
    assert instance.peek(laii)[1]["leafE"] == "ABBA"
    assert inst1.peek(laii)[1]["leafE"] == "B00F"
    modla = la.delete_item(1)
    assert len(modla.value) == 1
    llb1 = instance["test:llistB"][1]
    modllb = llb1.update("2001:db8:0:2::1", raw=True).up()
    assert modllb.value == ArrayValue(["::1", "2001:db8:0:2::1"])
    with pytest.raises(RawTypeError):
        llb1.update("2001::2::1", raw=True)


def test_validation(instance):
    inst2 = instance.put_member("testb:leafQ", "ABBA").top()
    with pytest.raises(SchemaError):
        inst2.validate(ctype=ContentType.all)
    inst3 = instance["test:contA"].put_member(
        "testb:leafS",
        "/test:contA/listA[leafE='C0FFEE'][leafF='true']/contD/contE/leafP",
        raw = True).top()
    assert inst3.validate(ctype=ContentType.all) is None
    assert instance.validate(ctype=ContentType.all) is None
