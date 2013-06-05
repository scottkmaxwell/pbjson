from unittest import TestCase, main
import pbjson as json

# from http://json.org/JSON_checker/test/pass2.json
JSON = [[[[[[[[[[[[[[[[[[["Not too deep"]]]]]]]]]]]]]]]]]]]


class TestPass2(TestCase):
    def test_parse(self):
        # test in/out equivalence and parsing
        encoded = json.dumps(JSON)
        decoded = json.loads(encoded)
        self.assertEqual(JSON, decoded)

if __name__ == '__main__':
    main()
