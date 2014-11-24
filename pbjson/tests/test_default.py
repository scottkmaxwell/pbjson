from unittest import TestCase, main

import pbjson


class TestDefault(TestCase):
    def test_default(self):
        self.assertEqual(
            pbjson.dumps(type, convert=repr),
            pbjson.dumps(repr(type)))

if __name__ == '__main__':
    main()
