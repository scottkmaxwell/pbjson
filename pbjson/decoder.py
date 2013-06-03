from __future__ import absolute_import

__author__ = 'Scott Maxwell'

# noinspection PyStatementEffect
"""Implementation of PBJSONDecoder"""
import struct
from .tokens import *


def _import_speedups():
    try:
        # noinspection PyUnresolvedReferences
        from . import _speedups
        return _speedups.make_decoder
    except (ImportError, AttributeError):
        return None


c_make_decoder = _import_speedups()

__all__ = ['PBJSONDecoder']


# Use speedup if available
# make_decoder = c_make_decoder or py_make_decoder


class PBJSONDecoder(object):
    """Packed Binary JSON decoder"""

    def __init__(self, document_class=None, float_class=None):
        """
        *document_class* allows you to specify an alternate class for objects.
        It will be :class:`dict` if not specified. The class must support __setitem__.

        *float_class* allows you to specify an alternate class for float values
        (e.g. :class:`decimal.Decimal`). The class will be passed a string
         representing the float.
        """
        self.float_class = float_class or float
        self.document_class = document_class or dict
        self.decoders = {
            INT: self._decode_int,
            NEGINT: self._decode_negint,
            FLOAT: self._decode_float,
            STRING: self._decode_string,
            BINARY: self._decode_bytes,
        }

    def _decode_int(self, content):
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

    def _decode_negint(self, content):
        return -self._decode_int(content)

    def _decode_float(self, content):
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
        return self.float_class(encoded)

    def _decode_string(self, content):
        return content.decode()

    def _decode_bytes(self, content):
        return content

    def _decode_list(self, keys, data, length=-1):
        result = []
        while length:
            if length < 0 and data[0] == TERMINATOR:
                return result, data[1:]
            item, data = self.decode_one(keys, data)
            result.append(item)
            length -= 1
        return result, data

    def _decode_dict(self, keys, data, length=-1):
        result = self.document_class()
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
            item, data = self.decode_one(keys, data)
            result[key_name] = item
            length -= 1
        return result, data

    def decode(self, s):
        keys = []
        return self.decode_one(keys, s)[0]

    def decode_one(self, keys, s):
        """Return the Python representation of ``s`` (a ``bytes`` instance containing a Packed Binary JSON document)"""
        if s:
            first_byte, s = s[0], s[1:]
            token = first_byte & 0xe0
            if not token:
                if first_byte == FALSE:
                    return False, s
                if first_byte == TRUE:
                    return True, s
                if first_byte == NULL:
                    return None, s
                if first_byte == INF:
                    return self.float_class('inf'), s
                if first_byte == NEGINF:
                    return self.float_class('-inf'), s
                if first_byte == NAN:
                    return self.float_class('-nan'), s
                if first_byte == TERMINATED_LIST:
                    return self._decode_list(keys, s)
                raise SyntaxError('Unknown token')

            length = first_byte & 0xf
            if first_byte & 0x10:
                if length == 0xf:
                    length, s = struct.unpack_from('!L', s, 0)[0], s[4:]
                elif length >= 8:
                    length, s = ((length & 7) << 16) | struct.unpack_from('!H', s, 0)[0], s[2:]
                else:
                    length, s = ((first_byte & 7) << 8) | s[0], s[1:]
            if token == LIST:
                return self._decode_list(keys, s, length)
            elif token == DICT:
                return self._decode_dict(keys, s, length)
            return self.decoders[token](s[:length]), s[length:]
