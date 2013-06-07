from unittest import TestCase, main

import pbjson as json


class TestDefault(TestCase):
    def test_default(self):
        self.assertEqual(
            json.dumps(type, convert=repr),
            json.dumps(repr(type)))

if __name__ == '__main__':
    main()
