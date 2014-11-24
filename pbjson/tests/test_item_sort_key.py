from unittest import TestCase, main

import pbjson
from operator import itemgetter


class TestItemSortKey(TestCase):
    def test_simple_first(self):
        a = {'a': 1, 'c': 5, 'jack': 'jill', 'pick': 'axe', 'array': [1, 5, 6, 9], 'tuple': (83, 12, 3), 'crate': 'dog', 'zeak': 'oh'}
        self.assertEqual(
            b'\xe8\x01a!\x01\x01c!\x05\x05crate\x83dog\x04jack\x84jill\x04pick\x83axe\x04zeak\x82oh\x05array\xc4!\x01!\x05!\x06!\t\x05tuple\xc3!S!\x0c!\x03',
            pbjson.dumps(a, sort_keys=pbjson.simple_first))

    def test_case(self):
        a = {'a': 1, 'c': 5, 'Jack': 'jill', 'pick': 'axe', 'Array': [1, 5, 6, 9], 'tuple': (83, 12, 3), 'crate': 'dog', 'zeak': 'oh'}
        self.assertEqual(
            b'\xe8\x05Array\xc4!\x01!\x05!\x06!\t\x04Jack\x84jill\x01a!\x01\x01c!\x05\x05crate\x83dog\x04pick\x83axe\x05tuple\xc3!S!\x0c!\x03\x04zeak\x82oh',
            pbjson.dumps(a, sort_keys=itemgetter(0)))
        self.assertEqual(
            b'\xe8\x01a!\x01\x05Array\xc4!\x01!\x05!\x06!\t\x01c!\x05\x05crate\x83dog\x04Jack\x84jill\x04pick\x83axe\x05tuple\xc3!S!\x0c!\x03\x04zeak\x82oh',
            pbjson.dumps(a, sort_keys=lambda kv: kv[0].lower()))

if __name__ == '__main__':
    main()
