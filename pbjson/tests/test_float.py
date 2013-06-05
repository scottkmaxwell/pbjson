import math
from unittest import TestCase
from pbjson.compat import long_type, text_type
import pbjson as json


class TestFloat(TestCase):
    def test_degenerates_allow(self):
        for inf in (float('inf'), float('-inf')):
            self.assertEqual(json.loads(json.dumps(inf)), inf)
        # Python 2.5 doesn't have math.isnan
        nan = json.loads(json.dumps(float('nan')))
        self.assertTrue((0 + nan) != nan)

    def test_floats(self):
        for num in [1617161771.7650001, math.pi, math.pi**100,
                    math.pi**-100, 3.1]:
            self.assertEqual(json.loads(json.dumps(num)), num)

    def test_ints(self):
        for num in [1, long_type(1), 1<<32, 1<<64]:
            self.assertEqual(json.loads(json.dumps(num)), num)
