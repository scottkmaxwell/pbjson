from unittest import TestCase, main
import pbjson


def default_iterable(obj):
    return list(obj)


class TestCheckCircular(TestCase):
    def test_circular_dict(self):
        dct = {}
        dct['a'] = dct
        self.assertRaises(ValueError, pbjson.dumps, dct)

    def test_circular_list(self):
        lst = []
        lst.append(lst)
        self.assertRaises(ValueError, pbjson.dumps, lst)

    def test_circular_composite(self):
        dct2 = {'a': []}
        dct2['a'].append(dct2)
        self.assertRaises(ValueError, pbjson.dumps, dct2)

if __name__ == '__main__':
    main()
