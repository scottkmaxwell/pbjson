from __future__ import absolute_import

__author__ = 'Scott Maxwell'

# noinspection PyStatementEffect
"""Implementation of PBJSONEncoder"""

from operator import itemgetter
from decimal import Decimal
from struct import pack
from .compat import text_type, binary_type, string_types, integer_types, PY3


def _import_speedups():
    try:
        # noinspection PyUnresolvedReferences
        from . import _speedups
        return _speedups.make_encoder
    except (ImportError, AttributeError):
        return None


c_make_encoder = _import_speedups()

FALSE = b'\x00'
TRUE = b'\x01'
NULL = b'\x02'
TERMINATED_LIST = b'\x0c'
TERMINATOR = b'\x0f'
INT = 0x20
NEGINT = 0x40
FLOAT = 0x60
STRING = 0x80
BINARY = 0xA0
LIST = 0xC0
DICT = 0xE0


def encode_type_and_length(data_type, length):
    if length < 16:
        return pack('B', data_type | length)
    elif length < 2048:
        return pack('BB', data_type | 0x10 | (length >> 8), length & 0xff)
    elif length < 458752:
        return pack('>BH', data_type | 0x18 | (length >> 16), length & 0xffff)
    return pack('>BL', data_type | 0x1f, length)


def encode_type_and_content(data_type, content):
    length = len(content)
    if length < 16:
        return pack('B%ds' % length, data_type | length, content)
    elif length < 2048:
        return pack('BB%ds' % length, data_type | 0x10 | (length >> 8), length & 0xff, content)
    elif length < 458752:
        return pack('>BH%ds' % length, data_type | 0x18 | (length >> 16), length & 0xffff, content)
    return pack('>BL%ds' % length, data_type | 0x1f, length, content)


class PBJSONEncoder(object):
    """Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict, namedtuple  | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).

    """

    # noinspection PyUnusedLocal
    def __init__(self, skipkeys=False, check_circular=True, sort_keys=False,
                 default=None, use_decimal=True, namedtuple_as_object=True,
                 tuple_as_array=True, item_sort_key=None, for_json=False, **kwargs):
        """Constructor for PBJSONEncoder, with sensible defaults.

        If skipkeys is false, then it is a TypeError to attempt
        encoding of keys that are not str.  If skipkeys is True,
        such items are simply skipped.

        If check_circular is true, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If sort_keys is true, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        If use_decimal is true (not the default), ``decimal.Decimal`` will
        be supported directly by the encoder. For the inverse, decode JSON
        with ``parse_float=decimal.Decimal``.

        If namedtuple_as_object is true (the default), objects with
        ``_asdict()`` methods will be encoded as JSON objects.

        If tuple_as_array is true (the default), tuple (and subclasses) will
        be encoded as JSON arrays.

        If specified, item_sort_key is a callable used to sort the items in
        each dictionary. This is useful if you want to sort items other than
        in alphabetical order by key.

        If for_json is true (not the default), objects with a ``for_json()``
        method will use the return value of that method for encoding as JSON
        instead of the object.

        """

        self.skipkeys = skipkeys
        self.check_circular = check_circular
        self.sort_keys = sort_keys
        self.use_decimal = use_decimal
        self.namedtuple_as_object = namedtuple_as_object
        self.tuple_as_array = tuple_as_array
        self.item_sort_key = item_sort_key
        self.for_json = for_json
        if default is not None:
            self.default = default
        if c_make_encoder is not None:
            self.encoder = c_make_encoder(
                check_circular, self.default, self.sort_keys,
                self.skipkeys, self.use_decimal,
                self.namedtuple_as_object, self.tuple_as_array,
                self.item_sort_key, self.for_json,
                Decimal)
        else:
            self.encoder = _make_iterencode(
                check_circular, self.default,
                self.sort_keys,
                self.skipkeys, self.use_decimal,
                self.namedtuple_as_object, self.tuple_as_array,
                self.item_sort_key, self.for_json,
                Decimal=Decimal)
        self.c_encoder = None

    def default(self, o):
        """Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return PBJSONEncoder.default(self, o)

        """
        raise TypeError(repr(o) + " is not JSON serializable")

    def encode(self, o):
        """Return a BinaryJSON representation of a Python data structure.

        >>> from pbjson.encoder import PBJSONEncoder
        >>> PBJSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'

        """
        return b''.join(self.encoder(o))

    def iterencode(self, o):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in PBJSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        return self.encoder(o)


# noinspection PyShadowingBuiltins
def _make_iterencode(check_circular, _default,
                     _sort_keys, _skipkeys,
                     _use_decimal, _namedtuple_as_object, _tuple_as_array,
                     _item_sort_key, _for_json,
                     ## HACK: hand-optimized bytecode; turn globals into locals
                     _PY3=PY3,
                     ValueError=ValueError,
                     string_types=string_types,
                     Decimal=Decimal,
                     dict=dict,
                     float=float,
                     id=id,
                     integer_types=integer_types,
                     isinstance=isinstance,
                     list=list,
                     str=str,
                     tuple=tuple):
    key_cache = {}
    markers = {} if check_circular else None
    if _item_sort_key and not callable(_item_sort_key):
        raise TypeError("item_sort_key must be None or callable")
    elif _sort_keys and not _item_sort_key:
        _item_sort_key = itemgetter(0)

    def _iterencode_list(lst):
        yield encode_type_and_length(LIST, len(lst))
        if not lst:
            return
        if check_circular:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        for value in lst:
            for encoded in _iterencode(value):
                yield encoded
        if check_circular:
            # noinspection PyUnboundLocalVariable
            del markers[markerid]

    def _iterencode_dict(dct):
        yield encode_type_and_length(DICT, len(dct))
        if not dct:
            return
        if check_circular:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        if _PY3:
            iteritems = dct.items()
        else:
            iteritems = dct.iteritems()
        if _item_sort_key:
            items = []
            for k, v in dct.items():
                if not isinstance(k, string_types):
                    if k is None:
                        continue
                items.append((k, v))
            items.sort(key=_item_sort_key)
        else:
            items = iteritems
        for key, value in items:
            if not (_item_sort_key or isinstance(key, string_types)):
                if key is None:
                    # _skipkeys must be True
                    continue
            if key in key_cache:
                yield pack('B', 0x80 | key_cache[key])
            else:
                key_count = len(key_cache)
                if key_count < 128:
                    key_cache[key] = key_count
                yield pack('B', len(key)) + key.encode()
            for encoded in _iterencode(value):
                yield encoded
        if check_circular:
            # noinspection PyUnboundLocalVariable
            del markers[markerid]

    def _iterencode(o):
        if isinstance(o, (text_type, binary_type)):
            if isinstance(o, text_type):
                token = STRING
                o = o.encode()
            else:
                token = BINARY
            yield encode_type_and_content(token, o)
        elif o is None:
            yield b'\02'
        elif o is True:
            yield b'\01'
        elif o is False:
            yield b'\00'
        elif isinstance(o, integer_types):
            if o:
                if o < 0:
                    token = NEGINT
                    o = -o
                else:
                    token = INT
                length = 0
                encoded = []
                while o > 0xffffffff:
                    encoded.append(pack('!I', o & 0xffffffff))
                    o >>= 32
                    length += 4
                if o > 0xffffff:
                    encoded.append(pack('!I', o))
                    length += 4
                elif o > 0xffff:
                    encoded.append(pack('!BH', o >> 16, o & 0xffff))
                    length += 3
                elif o > 0xff:
                    encoded.append(pack('!H', o))
                    length += 2
                elif o:
                    encoded.append(pack('B', o))
                    length += 1
                if len(encoded) > 1:
                    yield encode_type_and_length(token, length)
                    while encoded:
                        yield encoded.pop()
                else:
                    yield encode_type_and_content(token, encoded[0])
            else:
                yield encode_type_and_length(INT, 0)
        elif isinstance(o, float):
            b = pack('!d', o)
            while not b[-1]:
                b = b[:-1]
            yield encode_type_and_content(FLOAT, b)
        else:
            for_json = _for_json and getattr(o, 'for_json', None)
            if for_json and callable(for_json):
                for chunk in _iterencode(for_json()):
                    yield chunk
            elif isinstance(o, list):
                for chunk in _iterencode_list(o):
                    yield chunk
            else:
                _asdict = _namedtuple_as_object and getattr(o, '_asdict', None)
                if _asdict and callable(_asdict):
                    for chunk in _iterencode_dict(_asdict()):
                        yield chunk
                elif _tuple_as_array and isinstance(o, tuple):
                    for chunk in _iterencode_list(o):
                        yield chunk
                elif isinstance(o, dict):
                    for chunk in _iterencode_dict(o):
                        yield chunk
                # elif _use_decimal and isinstance(o, Decimal):
                #     yield str(o)
                else:
                    if check_circular:
                        markerid = id(o)
                        if markerid in markers:
                            raise ValueError("Circular reference detected")
                        markers[markerid] = o
                    try:
                        o = _default(o)
                    except TypeError as e:
                        yield TERMINATED_LIST
                        try:
                            for item in o:
                                for chunk in _iterencode(item):
                                    yield chunk
                            yield TERMINATOR
                        except TypeError:
                            raise e
                    else:
                        for chunk in _iterencode(o):
                            yield chunk
                    if check_circular:
                        # noinspection PyUnboundLocalVariable
                        del markers[markerid]

    return _iterencode
