from unittest import TestCase
import pbjson as json


def default_iterable(obj):
    return list(obj)


class TestCheckCircular(TestCase):
    def test_circular_dict(self):
        dct = {}
        dct['a'] = dct
        self.assertRaises(ValueError, json.dumps, dct)

    def test_circular_list(self):
        lst = []
        lst.append(lst)
        self.assertRaises(ValueError, json.dumps, lst)

    def test_circular_composite(self):
        dct2 = {'a': []}
        dct2['a'].append(dct2)
        self.assertRaises(ValueError, json.dumps, dct2)
