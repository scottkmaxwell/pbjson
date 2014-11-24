__author__ = 'Scott Maxwell'

import collections
import pbjson
from operator import itemgetter
from unittest import TestCase, main


class CaseInsensitiveDict(collections.MutableMapping):
    """
    A case-insensitive ``dict``-like object.

    Implements all methods and operations of
    ``collections.MutableMapping`` as well as dict's ``copy``. Also
    provides ``lower_items``.

    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. However, querying and contains
    testing is case insensitive:

        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['aCCEPT'] == 'application/json'  # True
        list(cid) == ['Accept']  # True

    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header, regardless
    of how the header name was originally stored.

    If the constructor, ``.update``, or equality comparison
    operations are given keys that have equal ``.lower()``s, the
    behavior is undefined.

    """
    def __init__(self, data=None, **kwargs):
        self._store = dict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def lower_items(self):
        """Like iteritems(), but with all lowercase keys."""
        return (
            (lowerkey, keyval[1])
            for (lowerkey, keyval)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, collections.Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
         return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, dict(self.items()))


class TestMapping(TestCase):
    def test_simple_first(self):
        a = CaseInsensitiveDict({'a': 1, 'c': 5, 'jack': 'jill', 'pick': 'axe', 'array': [1, 5, 6, 9], 'tuple': (83, 12, 3), 'crate': 'dog', 'zeak': 'oh'})
        self.assertEqual(
            b'\xe8\x01a!\x01\x01c!\x05\x05crate\x83dog\x04jack\x84jill\x04pick\x83axe\x04zeak\x82oh\x05array\xc4!\x01!\x05!\x06!\t\x05tuple\xc3!S!\x0c!\x03',
            pbjson.dumps(a, sort_keys=pbjson.simple_first))

    def test_case(self):
        a = CaseInsensitiveDict({'a': 1, 'c': 5, 'Jack': 'jill', 'pick': 'axe', 'Array': [1, 5, 6, 9], 'tuple': (83, 12, 3), 'crate': 'dog', 'zeak': 'oh'})
        self.assertEqual(
            b'\xe8\x05Array\xc4!\x01!\x05!\x06!\t\x04Jack\x84jill\x01a!\x01\x01c!\x05\x05crate\x83dog\x04pick\x83axe\x05tuple\xc3!S!\x0c!\x03\x04zeak\x82oh',
            pbjson.dumps(a, sort_keys=itemgetter(0)))
        self.assertEqual(
            b'\xe8\x01a!\x01\x05Array\xc4!\x01!\x05!\x06!\t\x01c!\x05\x05crate\x83dog\x04Jack\x84jill\x04pick\x83axe\x05tuple\xc3!S!\x0c!\x03\x04zeak\x82oh',
            pbjson.dumps(a, sort_keys=lambda kv: kv[0].lower()))

if __name__ == '__main__':
    main()
