from __future__ import absolute_import

__author__ = 'Scott Maxwell'

# noinspection PyStatementEffect
"""Implementation of PBJSON encoder"""

from operator import itemgetter
from decimal import Decimal
from struct import pack
from .compat import text_type, binary_type, string_types, integer_types, PY3
from .tokens import *
from collections import Mapping


def _import_speedups():
    try:
        # noinspection PyUnresolvedReferences
        from . import _speedups
        return _speedups.encode
    except (ImportError, AttributeError):
        return None


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


def default_converter(o):
    """Implement this function such that it returns
    a serializable object for ``o`` or raises a ``TypeError``.

    For example, to support arbitrary iterators, you could
    implement default like this::

        def default(o):
            try:
                iterable = iter(o)
            except TypeError:
                pass
            else:
                return list(iterable)
            raise TypeError(repr(o) + " is not JSON serializable")

    """
    raise TypeError(repr(o) + " is not PBJSON serializable")


def encode(obj, skip_illegal_keys=True, check_circular=True, sort_keys=None, custom=None, convert=default_converter, use_for_json=None):
    if sort_keys:
        if sort_keys is True:
            sort_keys = itemgetter(0)
        elif not callable(sort_keys):
            raise TypeError("sort_keys must be True, False or callable")
    else:
        sort_keys = None
    convert = convert or default_converter
    return b''.join(iterencoder(obj, Decimal, Mapping, skip_illegal_keys, check_circular, sort_keys, custom, convert, use_for_json))


def iterencode(obj, skip_illegal_keys=True, check_circular=True, sort_keys=None, custom=None, convert=default_converter, use_for_json=None):
    if sort_keys:
        if sort_keys is True:
            sort_keys = itemgetter(0)
        elif not callable(sort_keys):
            raise TypeError("sort_keys must be True, False or callable")
    else:
        sort_keys = None
    convert = convert or default_converter
    for i in iterencoder(obj, Decimal, Mapping, skip_illegal_keys, check_circular, sort_keys, custom, convert, use_for_json):
        yield i


# noinspection PyShadowingBuiltins
def py_iterencoder(obj, Decimal, Mapping, skip_illegal_keys, check_circular, sort_keys, custom, convert, use_for_json,
                    ## HACK: hand-optimized bytecode; turn globals into locals
                    _PY3=PY3,
                    ValueError=ValueError,
                    string_types=string_types,
                    float=float,
                    id=id,
                    integer_types=integer_types,
                    isinstance=isinstance,
                    str=str):
    key_cache = {}
    markers = {} if check_circular else None
    if custom and isinstance(custom[0], type):
        custom = (custom, )
    custom_types = tuple(c[0] for c in custom) if custom else None

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
        if sort_keys:
            items = []
            for k, v in dct.items():
                if not isinstance(k, string_types):
                    if k is None:
                        continue
                items.append((k, v))
            items.sort(key=sort_keys)
        else:
            items = iteritems
        for key, value in items:
            if not isinstance(key, string_types):
                if key is None:
                    # _skipkeys must be True
                    continue
            if key in key_cache:
                yield pack('B', 0x80 | key_cache[key])
            else:
                encoded_key = key.encode()
                if len(encoded_key) > 127:
                    # _skipkeys must be True
                    continue
                key_count = len(key_cache)
                if key_count < 128:
                    key_cache[key] = key_count
                yield pack('B', len(encoded_key)) + encoded_key
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
            yield Enc_NULL
        elif o is True:
            yield Enc_TRUE
        elif o is False:
            yield Enc_FALSE
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
        elif isinstance(o, (float, Decimal)):
            s = str(o)
            encoded = []
            nibble = None
            if s[0] == 'n' or s[0] == 'N':
                yield Enc_NAN
            elif s[0] == 'i' or s[0] == 'I':
                yield Enc_INF
            else:
                if s[0] == '-':
                    nibble = FltEnc_Minus << 4
                    s = s[1:]
                    if s[0] == 'i' or s[0] == 'I':
                        yield Enc_NEGINF
                        return
                if s[0] == '0':
                    s = s[1:]
                if s.endswith('.0'):
                    s = s[:-2]
                while s:
                    c, s = float_encode[s[0]], s[1:]
                    if nibble is None:
                        nibble = c << 4
                    else:
                        encoded.append(pack('B', nibble | c))
                        nibble = None
                if nibble is not None:
                    encoded.append(pack('B', nibble | FltEnc_Decimal))
                encoded = b''.join(encoded)
                yield encode_type_and_content(FLOAT, encoded)
        elif custom and isinstance(o, custom_types):
            yield Enc_CUSTOM
            for t in custom:
                if isinstance(o, t[0]):
                    o = t[1](o)
                    for chunk in _iterencode(o):
                        yield chunk
                    break
        else:
            for_json = use_for_json and getattr(o, 'for_json', None)
            if for_json and callable(for_json):
                for chunk in _iterencode(for_json()):
                    yield chunk
            elif isinstance(o, Mapping):
                for chunk in _iterencode_dict(o):
                    yield chunk
            else:
                _asdict = isinstance(o, tuple) and getattr(o, '_asdict', None)
                if _asdict and callable(_asdict):
                    for chunk in _iterencode_dict(_asdict()):
                        yield chunk
                else:
                    try:
                        iter(o)
                    except TypeError:
                        pass
                    else:
                        try:
                            len(o)
                        except Exception:
                            pass
                        else:
                            for chunk in _iterencode_list(o):
                                yield chunk
                            return
                        yield Enc_TERMINATED_LIST
                        for item in o:
                            for chunk in _iterencode(item):
                                yield chunk
                        yield Enc_TERMINATOR
                        return
                    if check_circular:
                        markerid = id(o)
                        if markerid in markers:
                            raise ValueError("Circular reference detected")
                        markers[markerid] = o
                    o = convert(o)
                    for chunk in _iterencode(o):
                        yield chunk
                    if check_circular:
                        # noinspection PyUnboundLocalVariable
                        del markers[markerid]

    return _iterencode(obj)

c_iterencoder = _import_speedups()
iterencoder = c_iterencoder or py_iterencoder
