__author__ = 'Scott Maxwell'

import unittest

import json
from pbjson.compat import PY3
from pbjson.encoder import PBJSONEncoder
from struct import unpack_from
from time import time
from marshal import dumps as marshal
from pickle import dumps as pickle
from pbjson.decoder import NaN, PosInf, NegInf


class TestBinaryEncoder(unittest.TestCase):

    def setUp(self):
        self.decoder = json.JSONDecoder()
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

    def test_short_float(self):
        self.assertEqual(b'\x62\x40\x12', self.encoder.encode(4.5))
        self.assertEqual(b'\x62\xc0\x12', self.encoder.encode(-4.5))

    def test_long_float(self):
        self.assertEqual(b'\x68\x3f\xe6\x66\x66\x66\x66\x66\x66', self.encoder.encode(0.7))
        self.assertEqual(b'\x68\xbf\xe6\x66\x66\x66\x66\x66\x66', self.encoder.encode(-0.7))

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
        self.assertEqual(b'\x0c\x20\x21\x01\x21\x02\x0f', self.encoder.encode(range(3)))

    def test_infinity(self):
        self.assertEqual(b'\x62\x7f\xf0', self.encoder.encode(PosInf))

    def test_negative_infinity(self):
        self.assertEqual(b'\x62\xff\xf0', self.encoder.encode(NegInf))

    def test_nan(self):
        self.assertEqual(b'\x62\x7f\xf8', self.encoder.encode(NaN))

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
        self.assertEqual(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x68\x3f\xe6\x66\x66\x66\x66\x66\x66\x05width\x62\x40\x12\x04name\x88the best\x05toast\x01\x08toppings\xc3\x85jelly\x83jam\x86butter', encoded)

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
        self.assertEqual(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x68\x3f\xe6\x66\x66\x66\x66\x66\x66\x05width\x62\x40\x12\x04name\x98\x50\x00' + b'a' * 0x5000 + b'\x05toast\x01\x08toppings\xc3\x96\x00' + b'j' * 0x600 + b'\x96\x72' + b'k' * 0x672 + b'\x96\x00' + b'l' * 0x600, encoded)

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
        encoded = json.dumps(
            {
                "countries": [
                    {"code": "us", "name": "United States"},
                    {"code": "ca", "name": "Canada"},
                    {"code": "mx", "name": "Mexico"}
                ],
                "region": 3,
            }, cls=PBJSONEncoder, sort_keys=True
        )
        self.assertEqual(b'\xe2\x09countries\xc3\xe2\x04code\x82us\x04name\x8DUnited States\xe2\x81\x82ca\x82\x86Canada\xe2\x81\x82mx\x82\x86Mexico\x06region\x21\x03', encoded)

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
        j = json.JSONEncoder(check_circular=False)
        for i in range(iterations):
            json_size = len(j.encode(sample))
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
