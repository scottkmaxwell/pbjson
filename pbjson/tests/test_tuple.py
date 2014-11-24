from unittest import TestCase, main

from pbjson.compat import BytesIO
import pbjson


class TestTuples(TestCase):
    def test_tuple_array_dumps(self):
        t = (1, 2, 3)
        expect = pbjson.dumps(list(t))
        # Default is True
        self.assertEqual(expect, pbjson.dumps(t))
        # Ensure that the "default" does not get called
        self.assertEqual(expect, pbjson.dumps(t, convert=repr))

    def test_tuple_array_dump(self):
        t = (1, 2, 3)
        expect = pbjson.dumps(list(t))
        # Default is True
        sio = BytesIO()
        pbjson.dump(t, sio)
        self.assertEqual(expect, sio.getvalue())
        # Ensure that the "default" does not get called
        sio = BytesIO()
        pbjson.dump(t, sio, convert=repr)
        self.assertEqual(expect, sio.getvalue())

if __name__ == '__main__':
    main()
