from unittest import TestCase, main
import pbjson

# from http://json.org/JSON_checker/test/pass2.json
JSON = [[[[[[[[[[[[[[[[[[["Not too deep"]]]]]]]]]]]]]]]]]]]


class TestPass2(TestCase):
    def test_parse(self):
        # test in/out equivalence and parsing
        encoded = pbjson.dumps(JSON)
        decoded = pbjson.loads(encoded)
        self.assertEqual(JSON, decoded)

if __name__ == '__main__':
    main()
