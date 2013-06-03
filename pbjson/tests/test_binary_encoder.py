__author__ = 'Scott Maxwell'

import unittest

import pbjson
from pbjson.compat import PY3
from pbjson.encoder import PBJSONEncoder, c_make_encoder
from struct import unpack_from
from time import time
from json import dumps as json
from marshal import dumps as marshal
from pickle import dumps as pickle
from decimal import Decimal


class TestBinaryEncoder(unittest.TestCase):

    def setUp(self):
        self.decoder = pbjson.PBJSONDecoder()
        self.encoder = PBJSONEncoder(sort_keys=True)

    def test_encode_false(self):
        self.assertEqual(b'\x00', self.encoder.encode(False))

    def test_encode_true(self):
        self.assertEqual(b'\x01', self.encoder.encode(True))

    def test_encode_none(self):
        self.assertEqual(b'\x02', self.encoder.encode(None))

    def test_encode_string(self):
        self.assertEqual(b'\x84test', self.encoder.encode('test'))

    def test_encode_medium_length_string(self):
        self.assertEqual(b'\x90\x20Now is the time for all good men', self.encoder.encode('Now is the time for all good men'))

    def test_encode_long_string(self):
        contents = 'a' * 2100
        encoded = self.encoder.encode(contents)
        token, length = unpack_from('!BH', encoded, 0)
        self.assertEqual(0x98, token)
        self.assertEqual(2100, length)
        self.assertEqual(encoded[3:], b'a' * 2100)

    def test_encode_unicode(self):
        self.assertEqual(b'\x84test', self.encoder.encode(u'test'))

    def test_encode_bytes(self):
        if PY3:
            self.assertEqual(b'\xa4test', self.encoder.encode(b'test'))

    def test_encode_long_binary(self):
        if PY3:
            contents = b'a' * 2100
            encoded = self.encoder.encode(contents)
            token, length = unpack_from('!BH', encoded, 0)
            self.assertEqual(0xb8, token)
            self.assertEqual(2100, length)
            self.assertEqual(encoded[3:], contents)

    def test_zero_float(self):
        self.assertEqual(b'\x60', self.encoder.encode(0.0))

    def test_int_float(self):
        self.assertEqual(b'\x61\x4d', self.encoder.encode(4.0))
        self.assertEqual(b'\x61\xb4', self.encoder.encode(-4.0))

    def test_leading_zero_float(self):
        self.assertEqual(b'\x62\xd2\x5d', self.encoder.encode(0.25))
        self.assertEqual(b'\x62\xbd\x25', self.encoder.encode(-0.25))

    def test_short_float(self):
        self.assertEqual(b'\x62\x4d\x5d', self.encoder.encode(4.5))
        self.assertEqual(b'\x62\xb4\xd5', self.encoder.encode(-4.5))

    def test_long_float(self):
        self.assertEqual(b'\x65\x15\x2d\x79\x82\x3d', self.encoder.encode(152.79823))
        self.assertEqual(b'\x65\xb1\x52\xd7\x98\x23', self.encoder.encode(-152.79823))

    def test_zero_decimal(self):
        self.assertEqual(b'\x60', self.encoder.encode(Decimal('0.0')))

    def test_int_decimal(self):
        self.assertEqual(b'\x61\x4d', self.encoder.encode(Decimal('4.0')))
        self.assertEqual(b'\x61\xb4', self.encoder.encode(Decimal('-4.0')))

    def test_leading_zero_decimal(self):
        self.assertEqual(b'\x62\xd2\x5d', self.encoder.encode(Decimal('0.25')))
        self.assertEqual(b'\x62\xbd\x25', self.encoder.encode(Decimal('-0.25')))

    def test_short_decimal(self):
        self.assertEqual(b'\x62\x4d\x5d', self.encoder.encode(Decimal('4.5')))
        self.assertEqual(b'\x62\xb4\xd5', self.encoder.encode(Decimal('-4.5')))

    def test_long_decimal(self):
        self.assertEqual(b'\x70\x11\x15\x2d\x79\x82\x31\x23\x45\x67\x89\x01\x23\x45\x67\x89\x01\x20\x0d', self.encoder.encode(Decimal('152.79823123456789012345678901200')))
        self.assertEqual(b'\x70\x11\xb1\x52\xd7\x98\x23\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90\x12\x00', self.encoder.encode(Decimal('-152.79823123456789012345678901200')))

    def test_one_byte_int(self):
        self.assertEqual(b'\x21\x04', self.encoder.encode(4))
        self.assertEqual(b'\x41\x04', self.encoder.encode(-4))

    def test_two_byte_int(self):
        self.assertEqual(b'\x22\x04\x00', self.encoder.encode(0x400))
        self.assertEqual(b'\x42\x04\x00', self.encoder.encode(-0x400))

    def test_three_byte_int(self):
        self.assertEqual(b'\x23\x04\x00\x00', self.encoder.encode(0x40000))
        self.assertEqual(b'\x43\x04\x00\x00', self.encoder.encode(-0x40000))

    def test_four_byte_int(self):
        self.assertEqual(b'\x24\x04\x00\x00\x00', self.encoder.encode(0x4000000))
        self.assertEqual(b'\x44\x04\x00\x00\x00', self.encoder.encode(-0x4000000))

    def test_five_byte_int(self):
        self.assertEqual(b'\x25\x04\x00\x00\x00\x00', self.encoder.encode(0x400000000))
        self.assertEqual(b'\x45\x04\x00\x00\x00\x00', self.encoder.encode(-0x400000000))

    def test_sixteen_byte_int(self):
        self.assertEqual(b'\x30\x10\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', self.encoder.encode(0x4000000000000000000000000000000))
        self.assertEqual(b'\x50\x10\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', self.encoder.encode(-0x4000000000000000000000000000000))

    def test_simple_list(self):
        self.assertEqual(b'\xc3\x85jelly\x83jam\x86butter', self.encoder.encode(['jelly', 'jam', 'butter']))

    def test_generator_list(self):
        def sample_generator():
            for x in range(3):
                yield x
        self.assertEqual(b'\x0c\x20\x21\x01\x21\x02\x0f', self.encoder.encode(sample_generator()))

    def test_tuple(self):
        self.assertEqual(b'\xc3\x20\x21\x01\x21\x02', self.encoder.encode((0, 1, 2)))

    if PY3:
        def test_range(self):
            self.assertEqual(b'\xc3\x20\x21\x01\x21\x02', self.encoder.encode(range(3)))

    def test_infinity(self):
        self.assertEqual(b'\x03', self.encoder.encode(float('inf')))

    def test_negative_infinity(self):
        self.assertEqual(b'\x04', self.encoder.encode(float('-inf')))

    def test_nan(self):
        self.assertEqual(b'\x05', self.encoder.encode(float('nan')))

    def test_simple_dict(self):
        encoded = self.encoder.encode(
            {
                "burned": False,
                "dimensions": {
                    "thickness": 0.7,
                    "width": 4.5
                },
                "name": "the best",
                "toast": True,
                "toppings": ["jelly", "jam", "butter"]
            }
        )
        self.assertEqual(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x88the best\x05toast\x01\x08toppings\xc3\x85jelly\x83jam\x86butter', encoded)

    def test_dict_with_long_strings(self):
        encoded = self.encoder.encode(
            {
                "burned": False,
                "dimensions": {
                    "thickness": 0.7,
                    "width": 4.5
                },
                "name": "a" * 0x5000,
                "toast": True,
                "toppings": ["j" * 0x600, "k" * 0x672, "l" * 0x600]
            }
        )
        self.assertEqual(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x98\x50\x00' + b'a' * 0x5000 + b'\x05toast\x01\x08toppings\xc3\x96\x00' + b'j' * 0x600 + b'\x96\x72' + b'k' * 0x672 + b'\x96\x00' + b'l' * 0x600, encoded)

    def test_repeating_keys(self):
        encoded = self.encoder.encode(
            {
                "countries": [
                    {"code": "us", "name": "United States"},
                    {"code": "ca", "name": "Canada"},
                    {"code": "mx", "name": "Mexico"}
                ],
                "region": 3,
            }
        )
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
            }, sort_keys=True
        )
        self.assertEqual(b'\xe2\x09countries\xc3\xe2\x04code\x82us\x04name\x8DUnited States\xe2\x81\x82ca\x82\x86Canada\xe2\x81\x82mx\x82\x86Mexico\x06region\x21\x03', encoded)

    if c_make_encoder:
        def test_speed(self):
            sample = {
                "countries": [
                    {"code": "us", "name": "United States"},
                    {"code": "ca", "name": "Canada"},
                    {"code": "mx", "name": "Mexico"}
                ],
                "dimensions": {
                    "thickness": 0.7,
                    "width": 4.5
                },
                "toast": True,
                "wrapped": False,
                "remote": None,
                "elapsed": 0.047220706939697266,
                "level": "WARNING",
                "levelno": 30,
                "port": 8443,
                "statusCode": 400,
                "ts": 1369935672.178207,
                "entries": [
                    {
                        "function": "func",
                        "level": "WARNING",
                        "levelno": 30,
                        "module": "server.api",
                        "text": "Invalid email or password",
                        "ts": 1369935672.2237792
                    },
                    {
                        "level": "INFO",
                        "levelno": 20,
                        "text": "POST /login 200",
                        "ts": 1369935672.2253869
                    }
                ],
                "request": {
                    "hostname": "example.com",
                    "method": "POST",
                    "path": "/login",
                    "params": {
                        "email": "test@example.com",
                        "format_type": "json",
                        "pin": "********",
                    }
                },
                "response": {
                    "length": 56,
                    "result": 200,
                    "type": "application/json"
                },
                "user": {
                    "country": "US",
                    "ip": "198.168.0.10",
                    "locale": "en-US"
                }
            }
            iterations = 10000

            start = time()
            for i in range(iterations):
                json_size = len(json(sample))
            json_time = time() - start

            start = time()
            j = PBJSONEncoder(check_circular=False)
            for i in range(iterations):
                binary_json_size = len(j.encode(sample))
            binary_json_time = time() - start

            start = time()
            for i in range(iterations):
                marshal_size = len(marshal(sample))
            marshal_time = time() - start

            start = time()
            for i in range(iterations):
                pickle_size = len(pickle(sample))
            pickle_time = time() - start

            # noinspection PyUnboundLocalVariable
            print('\nPBJSON: {} seconds, {} bytes\nJSON: {} seconds ({}%), {} bytes ({}%)\nMarshal: {} seconds ({}%), {} bytes ({}%)\nPickle: {} seconds ({}%), {} bytes ({}%)'.format(binary_json_time, binary_json_size, json_time, int(json_time / binary_json_time * 100), json_size, int(json_size / binary_json_size * 100), marshal_time, int(marshal_time / binary_json_time * 100), marshal_size, int(marshal_size / binary_json_size * 100), pickle_time, int(pickle_time / binary_json_time * 100), pickle_size, int(pickle_size / binary_json_size * 100)))
            self.assertLess(binary_json_time, json_time)


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
    j = PBJSONEncoder(sort_keys=True)
    # j = json.JSONEncoder(sort_keys=True)
    for i in range(1000):
        j.encode(sample)

if __name__ == '__main__':
    unittest.main()
    # import cProfile
    # cProfile.run('cycle()')
