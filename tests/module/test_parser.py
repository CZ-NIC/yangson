from yangson.module.parser import Parser

class TestParser:

    text = """module test { // Nice module
      prefix t;
      namespace /* URI follows */ \t'http://example.com/test';
      leaf foo {
        type string;
        default "hi \\"doc\\"";
      }
      leaf bar {
        mandatory true;
        type uint8;
      }
    }
    """

    def test_parser(self):
        p = Parser(self.text)
        s = p.parse_module()
        ss = s.find_all("leaf")
        sss1 = ss[0].find1("default")
        sss2 = ss[1].find1("type", "uint8")
        assert sss1.keyword == "default"
