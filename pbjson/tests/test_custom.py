__author__ = 'Scott Maxwell'

import pbjson
from unittest import TestCase, main
from datetime import datetime
import pickle


def encode_date_string(obj):
    return obj.strftime('%Y-%m-%d %I:%M:%S')


def decode_date_string(obj):
    return datetime.strptime(obj, '%Y-%m-%d %I:%M:%S')


class TestCustom(TestCase):
    def test_custom_datetime_with_encode(self):
        self.assertEqual(b'\x0e\x90\x132000-03-17 11:21:45', pbjson.dumps(datetime(2000, 3, 17, 11, 21, 45), custom=(datetime, encode_date_string)))

    def test_custom_datetime_with_decode(self):
        a = datetime(2000, 3, 17, 11, 21, 45)
        p = pbjson.dumps(a, custom=((datetime, encode_date_string),))
        self.assertEqual(a, pbjson.loads(p, custom=decode_date_string))

    def test_custom_datetime_with_pickle(self):
        a = datetime(2000, 3, 17, 11, 21, 45)
        p = pbjson.dumps(a, custom=((datetime, pickle.dumps),))
        self.assertEqual(a, pbjson.loads(p, custom=pickle.loads))


if __name__ == '__main__':
    main()
