import unittest

from pbjson.compat import BytesIO
import pbjson as json


class TestTuples(unittest.TestCase):
    def test_tuple_array_dumps(self):
        t = (1, 2, 3)
        expect = json.dumps(list(t))
        # Default is True
        self.assertEqual(expect, json.dumps(t))
        # Ensure that the "default" does not get called
        self.assertEqual(expect, json.dumps(t, default=repr))

    def test_tuple_array_dump(self):
        t = (1, 2, 3)
        expect = json.dumps(list(t))
        # Default is True
        sio = BytesIO()
        json.dump(t, sio)
        self.assertEqual(expect, sio.getvalue())
        # Ensure that the "default" does not get called
        sio = BytesIO()
        json.dump(t, sio, default=repr)
        self.assertEqual(expect, sio.getvalue())
