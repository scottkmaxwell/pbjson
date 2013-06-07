from __future__ import absolute_import
from decimal import Decimal
from unittest import TestCase, main
from time import time
from pbjson import loads
from collections import OrderedDict
from struct import pack
from pbjson.compat import PY3

import pbjson
import json
import marshal
import pickle

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


class TestDecode(TestCase):
    if not hasattr(TestCase, 'assertIs'):
        def assertIs(self, a, b):
            self.assertTrue(a is b, '%r is %r' % (a, b))

    def test_decode_false(self):
        self.assertIs(False, loads(b'\x00'))

    def test_decode_true(self):
        self.assertIs(True, loads(b'\x01'))

    def test_decode_none(self):
        self.assertIs(None, loads(b'\x02'))

    def test_decode_string(self):
        self.assertEqual('test', loads(b'\x84test'))

    def test_decode_medium_length_string(self):
        self.assertEqual('Now is the time for all good men', loads(b'\x90\x20Now is the time for all good men'))

    def test_decode_long_string(self):
        encoded = pack('!BH', 0x98, 2100) + b'a' * 2100
        decoded = loads(encoded)
        self.assertEqual('a' * 2100, decoded)

    def test_decode_unicode(self):
        self.assertEqual('test', loads(b'\x84test'))

    def test_decode_bytes(self):
        if PY3:
            self.assertEqual(b'test', loads(b'\xa4test'))

    def test_decode_long_binary(self):
        if PY3:
            encoded = pack('!BH', 0xb8, 2100) + b'a' * 2100
            decoded = loads(encoded)
            self.assertEqual(b'a' * 2100, decoded)

    def test_zero_float(self):
        self.assertEqual(0.0, loads(b'\x60'))

    def test_int_float(self):
        self.assertEqual(4.0, loads(b'\x61\x4d'))
        self.assertEqual(-4.0, loads(b'\x61\xb4'))

    def test_leading_zero_float(self):
        self.assertEqual(0.25, loads(b'\x62\xd2\x5d'))
        self.assertEqual(-0.25, loads(b'\x62\xbd\x25'))

    def test_short_float(self):
        self.assertEqual(4.5, loads(b'\x62\x4d\x5d'))
        self.assertEqual(-4.5, loads(b'\x62\xb4\xd5'))

    def test_long_float(self):
        self.assertEqual(152.79823, loads(b'\x65\x15\x2d\x79\x82\x3d'))
        self.assertEqual(-152.79823, loads(b'\x65\xb1\x52\xd7\x98\x23'))

    def test_zero_decimal(self):
        self.assertEqual(Decimal('0.0'), loads(b'\x60', float_class=Decimal))

    def test_int_decimal(self):
        self.assertEqual(Decimal('4.0'), loads(b'\x61\x4d', float_class=Decimal))
        self.assertEqual(Decimal('-4.0'), loads(b'\x61\xb4', float_class=Decimal))

    def test_leading_zero_decimal(self):
        self.assertEqual(Decimal('0.25'), loads(b'\x62\xd2\x5d', float_class=Decimal))
        self.assertEqual(Decimal('-0.25'), loads(b'\x62\xbd\x25', float_class=Decimal))

    def test_short_decimal(self):
        self.assertEqual(Decimal('4.5'), loads(b'\x62\x4d\x5d', float_class=Decimal))
        self.assertEqual(Decimal('-4.5'), loads(b'\x62\xb4\xd5', float_class=Decimal))

    def test_long_decimal(self):
        self.assertEqual(Decimal('152.79823123456789012345678901200'), loads(b'\x70\x11\x15\x2d\x79\x82\x31\x23\x45\x67\x89\x01\x23\x45\x67\x89\x01\x20\x0d', float_class=Decimal))
        self.assertEqual(Decimal('-152.79823123456789012345678901200'), loads(b'\x70\x11\xb1\x52\xd7\x98\x23\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90\x12\x00', float_class=Decimal))

    def test_one_byte_int(self):
        self.assertEqual(4, loads(b'\x21\x04'))
        self.assertEqual(-4, loads(b'\x41\x04'))

    def test_two_byte_int(self):
        self.assertEqual(0x400, loads(b'\x22\x04\x00'))
        self.assertEqual(-0x400, loads(b'\x42\x04\x00'))

    def test_three_byte_int(self):
        self.assertEqual(0x40000, loads(b'\x23\x04\x00\x00'))
        self.assertEqual(-0x40000, loads(b'\x43\x04\x00\x00'))

    def test_four_byte_int(self):
        self.assertEqual(0x4000000, loads(b'\x24\x04\x00\x00\x00'))
        self.assertEqual(-0x4000000, loads(b'\x44\x04\x00\x00\x00'))

    def test_five_byte_int(self):
        self.assertEqual(0x400000000, loads(b'\x25\x04\x00\x00\x00\x00'))
        self.assertEqual(-0x400000000, loads(b'\x45\x04\x00\x00\x00\x00'))

    def test_sixteen_byte_int(self):
        self.assertEqual(0x4000000000000000000000000000000, loads(b'\x30\x10\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'))
        self.assertEqual(-0x4000000000000000000000000000000, loads(b'\x50\x10\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'))

    def test_simple_list(self):
        self.assertEqual(['jelly', 'jam', 'butter'], loads(b'\xc3\x85jelly\x83jam\x86butter'))

    def test_generator_list(self):
        self.assertEqual([0, 1, 2], loads(b'\x0c\x20\x21\x01\x21\x02\x0f'))

    def test_infinity(self):
        self.assertEqual(float('inf'), loads(b'\x03'))

    def test_negative_infinity(self):
        self.assertEqual(float('-inf'), loads(b'\x04'))

    def test_nan(self):
        value = loads(b'\x05')
        self.assertNotEqual(value, value)

    def test_simple_dict(self):
        encoded = {
            "burned": False,
            "dimensions": {
                "thickness": 0.7,
                "width": 4.5
            },
            "name": "the best",
            "toast": True,
            "toppings": ["jelly", "jam", "butter"]
        }
        self.assertDictEqual(encoded, loads(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x88the best\x05toast\x01\x08toppings\xc3\x85jelly\x83jam\x86butter'))
        self.assertDictEqual(encoded, loads(bytearray(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x88the best\x05toast\x01\x08toppings\xc3\x85jelly\x83jam\x86butter')))
        self.assertDictEqual(encoded, loads(memoryview(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x88the best\x05toast\x01\x08toppings\xc3\x85jelly\x83jam\x86butter')))

    def test_ordered_dict(self):
        encoded = OrderedDict((
            ("burned", False),
            ("dimensions", OrderedDict((
                ("thickness", 0.7),
                ("width", 4.5)))),
            ("name", "the best"),
            ("toast", True),
            ("toppings", ["jelly", "jam", "butter"])
        ))
        decoded = loads(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x88the best\x05toast\x01\x08toppings\xc3\x85jelly\x83jam\x86butter', document_class=OrderedDict)
        self.assertEqual(encoded, decoded)
        self.assertIsInstance(decoded, OrderedDict)
        self.assertIsInstance(decoded['dimensions'], OrderedDict)

    def test_dict_with_long_strings(self):
        encoded = {
            "burned": False,
            "dimensions": {
                "thickness": 0.7,
                "width": 4.5
            },
            "name": "a" * 0x5000,
            "toast": True,
            "toppings": ["j" * 0x600, "k" * 0x672, "l" * 0x600]
        }
        self.assertEqual(encoded, loads(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x98\x50\x00' + b'a' * 0x5000 + b'\x05toast\x01\x08toppings\xc3\x96\x00' + b'j' * 0x600 + b'\x96\x72' + b'k' * 0x672 + b'\x96\x00' + b'l' * 0x600))

    def test_repeating_keys(self):
        encoded = {
            "countries": [
                {"code": "us", "name": "United States"},
                {"code": "ca", "name": "Canada"},
                {"code": "mx", "name": "Mexico"}
            ],
            "region": 3,
        }
        self.assertEqual(encoded, loads(b'\xe2\x09countries\xc3\xe2\x04code\x82us\x04name\x8DUnited States\xe2\x81\x82ca\x82\x86Canada\xe2\x81\x82mx\x82\x86Mexico\x06region\x21\x03'))

    def test_speed(self):
        if pbjson._has_decoder_speedups():
            encoded = json.dumps(sample)
            start = time()
            for i in range(100):
                json.loads(encoded)
            json_time = time() - start

            encoded = pbjson.dumps(sample)
            start = time()
            for i in range(100):
                pbjson.loads(encoded)
            binary_json_time = time() - start

            # noinspection PyUnboundLocalVariable
            # print('\nPBJSON: {} seconds\nJSON: {} seconds ({}%)\nMarshal: {} seconds ({}%)\nPickle: {} seconds ({}%)'.format(binary_json_time, json_time, int(json_time / binary_json_time * 100), marshal_time, int(marshal_time / binary_json_time * 100), pickle_time, int(pickle_time / binary_json_time * 100)))
            self.assertLess(binary_json_time, json_time)


if __name__ == '__main__':
    iterations = 10000
    encoded = json.dumps(sample)
    start = time()
    for i in range(iterations):
        json.loads(encoded)
    json_time = time() - start

    encoded = pbjson.dumps(sample)
    start = time()
    for i in range(iterations):
        pbjson.loads(encoded)
    binary_json_time = time() - start

    encoded = marshal.dumps(sample)
    start = time()
    for i in range(iterations):
        marshal.loads(encoded)
    marshal_time = time() - start

    encoded = pickle.dumps(sample)
    start = time()
    for i in range(iterations):
        pickle.loads(encoded)
    pickle_time = time() - start

    print('\nPBJSON: {} seconds\nJSON: {} seconds ({}%)\nMarshal: {} seconds ({}%)\nPickle: {} seconds ({}%)'.format(binary_json_time, json_time, int(json_time / binary_json_time * 100), marshal_time, int(marshal_time / binary_json_time * 100), pickle_time, int(pickle_time / binary_json_time * 100)))
    main()

