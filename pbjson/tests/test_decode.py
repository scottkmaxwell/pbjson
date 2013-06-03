from __future__ import absolute_import
from decimal import Decimal
from unittest import TestCase, main

import pbjson
from collections import OrderedDict
from struct import pack
from pbjson.compat import PY3
from pbjson.decoder import PosInf, NegInf


class TestDecode(TestCase):
    def setUp(self):
        self.decoder = pbjson.PBJSONDecoder()

    if not hasattr(TestCase, 'assertIs'):
        def assertIs(self, a, b):
            self.assertTrue(a is b, '%r is %r' % (a, b))

    def test_decode_false(self):
        self.assertIs(False, self.decoder.decode(b'\x00'))

    def test_decode_true(self):
        self.assertIs(True, self.decoder.decode(b'\x01'))

    def test_decode_none(self):
        self.assertIs(None, self.decoder.decode(b'\x02'))

    def test_decode_string(self):
        self.assertEqual('test', self.decoder.decode(b'\x84test'))

    def test_decode_medium_length_string(self):
        self.assertEqual('Now is the time for all good men', self.decoder.decode(b'\x90\x20Now is the time for all good men'))

    def test_decode_long_string(self):
        encoded = pack('!BH', 0x98, 2100) + b'a' * 2100
        decoded = self.decoder.decode(encoded)
        self.assertEqual('a' * 2100, decoded)

    def test_decode_unicode(self):
        self.assertEqual(u'test', self.decoder.decode(b'\x84test'))

    def test_decode_bytes(self):
        if PY3:
            self.assertEqual(b'test', self.decoder.decode(b'\xa4test'))

    def test_decode_long_binary(self):
        if PY3:
            encoded = pack('!BH', 0xb8, 2100) + b'a' * 2100
            decoded = self.decoder.decode(encoded)
            self.assertEqual(b'a' * 2100, decoded)

    def test_zero_float(self):
        self.assertEqual(0.0, self.decoder.decode(b'\x60'))

    def test_int_float(self):
        self.assertEqual(4.0, self.decoder.decode(b'\x61\x4d'))
        self.assertEqual(-4.0, self.decoder.decode(b'\x61\xb4'))

    def test_leading_zero_float(self):
        self.assertEqual(0.25, self.decoder.decode(b'\x62\xd2\x5d'))
        self.assertEqual(-0.25, self.decoder.decode(b'\x62\xbd\x25'))

    def test_short_float(self):
        self.assertEqual(4.5, self.decoder.decode(b'\x62\x4d\x5d'))
        self.assertEqual(-4.5, self.decoder.decode(b'\x62\xb4\xd5'))

    def test_long_float(self):
        self.assertEqual(152.79823, self.decoder.decode(b'\x65\x15\x2d\x79\x82\x3d'))
        self.assertEqual(-152.79823, self.decoder.decode(b'\x65\xb1\x52\xd7\x98\x23'))

    def test_zero_decimal(self):
        self.assertEqual(Decimal('0.0'), pbjson.loads(b'\x60', float_class=Decimal))

    def test_int_decimal(self):
        self.assertEqual(Decimal('4.0'), pbjson.loads(b'\x61\x4d', float_class=Decimal))
        self.assertEqual(Decimal('-4.0'), pbjson.loads(b'\x61\xb4', float_class=Decimal))

    def test_leading_zero_decimal(self):
        self.assertEqual(Decimal('0.25'), pbjson.loads(b'\x62\xd2\x5d', float_class=Decimal))
        self.assertEqual(Decimal('-0.25'), pbjson.loads(b'\x62\xbd\x25', float_class=Decimal))

    def test_short_decimal(self):
        self.assertEqual(Decimal('4.5'), pbjson.loads(b'\x62\x4d\x5d', float_class=Decimal))
        self.assertEqual(Decimal('-4.5'), pbjson.loads(b'\x62\xb4\xd5', float_class=Decimal))

    def test_long_decimal(self):
        self.assertEqual(Decimal('152.79823123456789012345678901200'), pbjson.loads(b'\x70\x11\x15\x2d\x79\x82\x31\x23\x45\x67\x89\x01\x23\x45\x67\x89\x01\x20\x0d', float_class=Decimal))
        self.assertEqual(Decimal('-152.79823123456789012345678901200'), pbjson.loads(b'\x70\x11\xb1\x52\xd7\x98\x23\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90\x12\x00', float_class=Decimal))

    def test_one_byte_int(self):
        self.assertEqual(4, self.decoder.decode(b'\x21\x04'))
        self.assertEqual(-4, self.decoder.decode(b'\x41\x04'))

    def test_two_byte_int(self):
        self.assertEqual(0x400, self.decoder.decode(b'\x22\x04\x00'))
        self.assertEqual(-0x400, self.decoder.decode(b'\x42\x04\x00'))

    def test_three_byte_int(self):
        self.assertEqual(0x40000, self.decoder.decode(b'\x23\x04\x00\x00'))
        self.assertEqual(-0x40000, self.decoder.decode(b'\x43\x04\x00\x00'))

    def test_four_byte_int(self):
        self.assertEqual(0x4000000, self.decoder.decode(b'\x24\x04\x00\x00\x00'))
        self.assertEqual(-0x4000000, self.decoder.decode(b'\x44\x04\x00\x00\x00'))

    def test_five_byte_int(self):
        self.assertEqual(0x400000000, self.decoder.decode(b'\x25\x04\x00\x00\x00\x00'))
        self.assertEqual(-0x400000000, self.decoder.decode(b'\x45\x04\x00\x00\x00\x00'))

    def test_sixteen_byte_int(self):
        self.assertEqual(0x4000000000000000000000000000000, self.decoder.decode(b'\x30\x10\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'))
        self.assertEqual(-0x4000000000000000000000000000000, self.decoder.decode(b'\x50\x10\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'))

    def test_simple_list(self):
        self.assertEqual(['jelly', 'jam', 'butter'], self.decoder.decode(b'\xc3\x85jelly\x83jam\x86butter'))

    def test_generator_list(self):
        self.assertEqual([0, 1, 2], self.decoder.decode(b'\x0c\x20\x21\x01\x21\x02\x0f'))

    def test_infinity(self):
        self.assertEqual(PosInf, self.decoder.decode(b'\x03'))

    def test_negative_infinity(self):
        self.assertEqual(NegInf, self.decoder.decode(b'\x04'))

    def test_nan(self):
        value = self.decoder.decode(b'\x05')
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
        self.assertDictEqual(encoded, self.decoder.decode(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x88the best\x05toast\x01\x08toppings\xc3\x85jelly\x83jam\x86butter'))

    def test_ordered_dict(self):
        encoded = OrderedDict((
            ("burned", False),
            ("dimensions", OrderedDict((
                ("thickness", 0.7),
                ("width", 4.5)))
            ),
            ("name", "the best"),
            ("toast", True),
            ("toppings", ["jelly", "jam", "butter"])
        ))
        decoded = pbjson.loads(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x88the best\x05toast\x01\x08toppings\xc3\x85jelly\x83jam\x86butter', object_class=OrderedDict)
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
        self.assertEqual(encoded, self.decoder.decode(b'\xe5\x06burned\x00\x0adimensions\xe2\x09thickness\x61\xd7\x05width\x62\x4d\x5d\x04name\x98\x50\x00' + b'a' * 0x5000 + b'\x05toast\x01\x08toppings\xc3\x96\x00' + b'j' * 0x600 + b'\x96\x72' + b'k' * 0x672 + b'\x96\x00' + b'l' * 0x600))

    def test_repeating_keys(self):
        encoded = {
            "countries": [
                {"code": "us", "name": "United States"},
                {"code": "ca", "name": "Canada"},
                {"code": "mx", "name": "Mexico"}
            ],
            "region": 3,
        }
        self.assertEqual(encoded, self.decoder.decode(b'\xe2\x09countries\xc3\xe2\x04code\x82us\x04name\x8DUnited States\xe2\x81\x82ca\x82\x86Canada\xe2\x81\x82mx\x82\x86Mexico\x06region\x21\x03'))

if __name__ == '__main__':
    main()
