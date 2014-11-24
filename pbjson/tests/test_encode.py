__author__ = 'Scott Maxwell'

from unittest import TestCase, main

import pbjson
from pbjson.compat import PY3
from pbjson.encoder import encode
from struct import unpack_from
from time import time
import json
import marshal
import pickle
from decimal import Decimal
from pbjson.tests.test_decode import sample


class TestEncode(TestCase):

    def test_encode_false(self):
        self.assertEqual(b'\x00', encode(False))

    def test_encode_true(self):
        self.assertEqual(b'\x01', encode(True))

    def test_encode_none(self):
        self.assertEqual(b'\x02', encode(None))

    def test_encode_string(self):
        self.assertEqual(b'\x84test', encode('test'))

    def test_encode_medium_length_string(self):
        self.assertEqual(b'\x90\x20Now is the time for all good men', encode('Now is the time for all good men'))

    def test_int_roundtrip(self):
        encoded = pbjson.dumps(1234567890)
        decoded = pbjson.loads(encoded)
        self.assertEqual(1234567890, decoded)

    def test_e_roundtrip(self):
        encoded = pbjson.dumps(0.123456789e-12)
        decoded = pbjson.loads(encoded)
        self.assertEqual(0.123456789e-12, decoded)

    def test_encode_long_string(self):
        contents = 'a' * 2100
        encoded = encode(contents)
        token, length = unpack_from('!BH', encoded, 0)
        self.assertEqual(0x98, token)
        self.assertEqual(2100, length)
        self.assertEqual(encoded[3:], b'a' * 2100)

    def test_encode_unicode(self):
        self.assertEqual(b'\x84test', encode('test'))

    def test_encode_bytes(self):
        if PY3:
            self.assertEqual(b'\xa4test', encode(b'test'))

    def test_encode_long_binary(self):
        if PY3:
            contents = b'a' * 2100
            encoded = encode(contents)
            token, length = unpack_from('!BH', encoded, 0)
            self.assertEqual(0xb8, token)
            self.assertEqual(2100, length)
            self.assertEqual(encoded[3:], contents)

    def test_zero_float(self):
        self.assertEqual(b'\x60', encode(0.0))

    def test_int_float(self):
        self.assertEqual(b'\x61\x4d', encode(4.0))
        self.assertEqual(b'\x61\xb4', encode(-4.0))

    def test_leading_zero_float(self):
        self.assertEqual(b'\x62\xd2\x5d', encode(0.25))
        self.assertEqual(b'\x62\xbd\x25', encode(-0.25))

    def test_short_float(self):
        self.assertEqual(b'\x62\x4d\x5d', encode(4.5))
        self.assertEqual(b'\x62\xb4\xd5', encode(-4.5))

    def test_long_float(self):
        self.assertEqual(b'\x65\x15\x2d\x79\x82\x3d', encode(152.79823))
        self.assertEqual(b'\x65\xb1\x52\xd7\x98\x23', encode(-152.79823))

    def test_zero_decimal(self):
        self.assertEqual(b'\x60', encode(Decimal('0.0')))

    def test_int_decimal(self):
        self.assertEqual(b'\x61\x4d', encode(Decimal('4.0')))
        self.assertEqual(b'\x61\xb4', encode(Decimal('-4.0')))

    def test_leading_zero_decimal(self):
        self.assertEqual(b'\x62\xd2\x5d', encode(Decimal('0.25')))
        self.assertEqual(b'\x62\xbd\x25', encode(Decimal('-0.25')))

    def test_short_decimal(self):
        self.assertEqual(b'\x62\x4d\x5d', encode(Decimal('4.5')))
        self.assertEqual(b'\x62\xb4\xd5', encode(Decimal('-4.5')))

    def test_long_decimal(self):
        self.assertEqual(b'\x70\x11\x15\x2d\x79\x82\x31\x23\x45\x67\x89\x01\x23\x45\x67\x89\x01\x20\x0d', encode(Decimal('152.79823123456789012345678901200')))
        self.assertEqual(b'\x70\x11\xb1\x52\xd7\x98\x23\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90\x12\x00', encode(Decimal('-152.79823123456789012345678901200')))

    def test_one_byte_int(self):
        self.assertEqual(b'\x21\x04', encode(4))
        self.assertEqual(b'\x41\x04', encode(-4))

    def test_two_byte_int(self):
        self.assertEqual(b'\x22\x04\x00', encode(0x400))
        self.assertEqual(b'\x42\x04\x00', encode(-0x400))

    def test_three_byte_int(self):
        self.assertEqual(b'\x23\x04\x00\x00', encode(0x40000))
        self.assertEqual(b'\x43\x04\x00\x00', encode(-0x40000))

    def test_four_byte_int(self):
        self.assertEqual(b'\x24\x04\x00\x00\x00', encode(0x4000000))
        self.assertEqual(b'\x44\x04\x00\x00\x00', encode(-0x4000000))

    def test_five_byte_int(self):
        self.assertEqual(b'\x25\x04\x00\x00\x00\x00', encode(0x400000000))
        self.assertEqual(b'\x45\x04\x00\x00\x00\x00', encode(-0x400000000))

    def test_sixteen_byte_int(self):
        self.assertEqual(b'\x30\x10\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', encode(0x4000000000000000000000000000000))
        self.assertEqual(b'\x50\x10\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', encode(-0x4000000000000000000000000000000))

    def test_simple_list(self):
        self.assertEqual(b'\xc3\x85jelly\x83jam\x86butter', encode(['jelly', 'jam', 'butter']))

    def test_generator_list(self):
        def sample_generator():
            for x in range(3):
                yield x
        self.assertEqual(b'\x0c\x20\x21\x01\x21\x02\x0f', encode(sample_generator()))

    def test_tuple(self):
        self.assertEqual(b'\xc3\x20\x21\x01\x21\x02', encode((0, 1, 2)))

    if PY3:
        def test_range(self):
            self.assertEqual(b'\xc3\x20\x21\x01\x21\x02', encode(range(3)))

    def test_infinity(self):
        self.assertEqual(b'\x03', encode(float('inf')))

    def test_negative_infinity(self):
        self.assertEqual(b'\x04', encode(float('-inf')))

    def test_nan(self):
        self.assertEqual(b'\x05', encode(float('nan')))

    def test_simple_dict(self):
        encoded = encode(
            {
                "burned": False,
                "dimensions": {
                    "thickness": 0.7,
                    "width": 4.5
                },
                "name": "the best",
                "toast": True,
                "toppings": ["jelly", "jam", "butter"]
            }, sort_keys=True)
        self.assertEqual(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x88the best\x05toast\x01\x08toppings\xc3\x85jelly\x83jam\x86butter', encoded)

    def test_dict_with_long_strings(self):
        encoded = encode(
            {
                "burned": False,
                "dimensions": {
                    "thickness": 0.7,
                    "width": 4.5
                },
                "name": "a" * 0x5000,
                "toast": True,
                "toppings": ["j" * 0x600, "k" * 0x672, "l" * 0x600]
            }, sort_keys=True)
        self.assertEqual(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x98\x50\x00' + b'a' * 0x5000 + b'\x05toast\x01\x08toppings\xc3\x96\x00' + b'j' * 0x600 + b'\x96\x72' + b'k' * 0x672 + b'\x96\x00' + b'l' * 0x600, encoded)

    def test_repeating_keys(self):
        encoded = encode(
            {
                "countries": [
                    {"code": "us", "name": "United States"},
                    {"code": "ca", "name": "Canada"},
                    {"code": "mx", "name": "Mexico"}
                ],
                "region": 3,
            }, sort_keys=True)
        self.assertEqual(b'\xe2\x09countries\xc3\xe2\x04code\x82us\x04name\x8DUnited States\xe2\x81\x82ca\x82\x86Canada\xe2\x81\x82mx\x82\x86Mexico\x06region\x21\x03', encoded)

    def test_dumps(self):
        encoded = pbjson.dumps(
            {
                "countries": [
                    {"code": "us", "name": "United States"},
                    {"code": "ca", "name": "Canada"},
                    {"code": "mx", "name": "Mexico"}
                ],
                "region": 3,
            }, sort_keys=True)
        self.assertEqual(b'\xe2\x09countries\xc3\xe2\x04code\x82us\x04name\x8DUnited States\xe2\x81\x82ca\x82\x86Canada\xe2\x81\x82mx\x82\x86Mexico\x06region\x21\x03', encoded)


def cycle():
    sample = {
        "countries": [
            {"code": "us", "name": "United States"},
            {"code": "ca", "name": "Canada"},
            {"code": "mx", "name": "Mexico"}
        ],
        "region": 3,
        "burned": False,
        "dimensions": {
            "thickness": 0.7,
            "width": 4.5
        },
        "name": "the best",
        "toast": True,
        "toppings": ["jelly", "jam", "butter"]
    }
    # j = json.JSONEncoder(sort_keys=True)
    for i in range(1000):
        encode(sample, sort_keys=True)

if __name__ == '__main__':
    # v = 3.100000000001
    # a = pbjson.dumps(v)
    # b = pbjson.loads(a)
    # s = repr(v)
    # if s[0] == '0':
    #     s = s[1:]
    # length = 1 + int((len(s)+1)/2)
    # print(v, b, v - b if v-b else '', 'Bad length {}, expected {}'.format(len(a), length) if len(a) != length else '')

    iterations = 10000
    start = time()
    for i in range(iterations):
        json_size = len(json.dumps(sample))
    json_time = time() - start

    size = len(pbjson.dumps(sample))
    start = time()
    for i in range(iterations):
        binary_json_size = len(pbjson.dumps(sample))
        # self.assertEqual(size, binary_json_size)
    binary_json_time = time() - start

    start = time()
    for i in range(iterations):
        marshal_size = len(marshal.dumps(sample))
    marshal_time = time() - start

    start = time()
    for i in range(iterations):
        pickle_size = len(pickle.dumps(sample))
    pickle_time = time() - start

    # noinspection PyUnboundLocalVariable
    print('\nPBJSON: {} seconds, {} bytes\nJSON: {} seconds ({}%), {} bytes ({}%)\nMarshal: {} seconds ({}%), {} bytes ({}%)\nPickle: {} seconds ({}%), {} bytes ({}%)'.format(binary_json_time, binary_json_size, json_time, int(json_time / binary_json_time * 100), json_size, int(json_size / binary_json_size * 100), marshal_time, int(marshal_time / binary_json_time * 100), marshal_size, int(marshal_size / binary_json_size * 100), pickle_time, int(pickle_time / binary_json_time * 100), pickle_size, int(pickle_size / binary_json_size * 100)))
    main()
    # import cProfile
    # cProfile.run('cycle()')
