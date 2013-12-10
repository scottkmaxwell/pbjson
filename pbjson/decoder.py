from __future__ import absolute_import

__author__ = 'Scott Maxwell'
__all__ = ['decode']

# noinspection PyStatementEffect
"""Implementation of PBJSONDecoder"""
import struct
from .tokens import *


class PBJSONDecodeError(ValueError):
    pass


def _import_speedups():
    try:
        # noinspection PyUnresolvedReferences
        from . import _speedups
        return _speedups.decode
    except (ImportError, AttributeError):
        return None


def _decode_int(content):
    accumulator = 0
    length = len(content)
    offset = 0
    while length >= 4:
        accumulator |= struct.unpack_from('!L', content, offset)[0]
        length -= 4
        offset += 4
        if length:
            if length > 4:
                accumulator <<= 32
            else:
                accumulator <<= (length * 8)
    if length == 3:
        b, h = struct.unpack_from('!BH', content, offset)
        accumulator |= ((b << 16) | h)
    elif length == 2:
        accumulator |= struct.unpack_from('!H', content, offset)[0]
    elif length == 1:
        accumulator |= struct.unpack_from('B', content, offset)[0]
    return accumulator


def _decode_float(float_class, content):
    if content:
        encoded = []
        for b in content:
            encoded.append(float_decode[b >> 4])
            encoded.append(float_decode[b & 0xf])
        if encoded and encoded[-1] == '.':
            encoded = encoded[:-1]
        encoded = ''.join(encoded)
    else:
        encoded = '0'
    return float_class(encoded)


def _decode_list(context, data, length=-1):
    result = []
    while length:
        if length < 0 and data[0] == TERMINATOR:
            return result, data[1:]
        item, data = _decode_one(context, data)
        result.append(item)
        length -= 1
    return result, data


def _decode_dict(context, document_class, keys, data, length=-1):
    result = document_class()
    while length:
        if length < 0 and data[0] == TERMINATOR:
            return result, data[1:]
        key_token, data = data[0], data[1:]
        if key_token < 0x80:
            key_name, data = data[:key_token].decode(), data[key_token:]
            if len(keys) < 128:
                keys.append(key_name)
        else:
            key_name = keys[key_token & 0x7f]
        item, data = _decode_one(context, data)
        result[key_name] = item
        length -= 1
    return result, data


def _decode_custom(context, data, custom):
    result, data = _decode_one(context, data)
    return custom(result), data


def _decode_one(context, data):
    """Return the Python representation of ``s`` (a ``bytes`` instance containing a Packed Binary JSON document)"""
    if data:
        first_byte, data = data[0], data[1:]
        token = first_byte & 0xe0
        if not token:
            return context[first_byte](context, data)

        length = first_byte & 0xf
        if first_byte & 0x10:
            if length == 0xf:
                length, data = struct.unpack_from('!L', data, 0)[0], data[4:]
            elif length >= 8:
                length, data = ((length & 7) << 16) | struct.unpack_from('!H', data, 0)[0], data[2:]
            else:
                length, data = ((first_byte & 7) << 8) | data[0], data[1:]
        if token in {LIST, DICT}:
            return context[token](context, data, length)
        return context[token](context, data[:length]), data[length:]


def py_decoder(data, document_class=None, float_class=None, custom=None, unicode_errors='strict'):
    if isinstance(data, memoryview):
        data = data.tobytes()
    float_class = float_class or float
    document_class = document_class or dict
    keys = []
    context = {
        FALSE: lambda context, data: (False, data),
        TRUE: lambda context, data: (True, data),
        NULL: lambda context, data: (None, data),
        INF: lambda context, data: (float_class('inf'), data),
        NEGINF: lambda context, data: (float_class('-inf'), data),
        NAN: lambda context, data: (float_class('nan'), data),
        TERMINATED_LIST: _decode_list,
        INT: lambda context, data: _decode_int(data),
        NEGINT: lambda context, data: -_decode_int(data),
        FLOAT: lambda context, data: _decode_float(float_class, data),
        STRING: lambda context, data: data.decode(errors=unicode_errors),
        BINARY: lambda context, data: data,
        LIST: _decode_list,
        DICT: lambda context, data, length: _decode_dict(context, document_class, keys, data, length),
        CUSTOM: lambda context, data: _decode_custom(context, data, custom),
    }
    return _decode_one(context, data)[0]


# Use speedup if available
c_decoder = _import_speedups()
decode = c_decoder or py_decoder
