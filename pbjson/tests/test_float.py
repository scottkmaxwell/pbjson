import math
from unittest import TestCase, main
from pbjson.compat import long_type
from decimal import Decimal
import pbjson as json


class TestFloat(TestCase):
    def test_degenerates_allow(self):
        for inf in (float('inf'), float('-inf')):
            self.assertEqual(json.loads(json.dumps(inf)), inf)
        # Python 2.5 doesn't have math.isnan
        nan = json.loads(json.dumps(float('nan')))
        self.assertTrue((0 + nan) != nan)

    def test_floats(self):
        for num in [Decimal('1617161771.7650001'), math.pi, math.pi ** 100,
                    math.pi ** -100, 3.1, 3.1000000001, 3.1000000002, 3.10000000001, 3.100000000001, 3.1000000000001, 3.10000000000001, 0.00012345678901234572, 0.00012345678901234574, 0.00012345678901234576, 0.00012345678901234578, 152.79823, 152.798229999999975, 0.7]:
            encoded = json.dumps(float(num))
            decoded = json.loads(encoded)
            s = str(num)
            if s[0] == '0':
                s = s[1:]
            length = 1 + int((len(s)+1)/2)
            self.assertEqual(decoded, float(num))
            self.assertEqual(length, len(encoded), num)

    def test_ints(self):
        for num in [1, long_type(1), 1<<32, 1<<64]:
            self.assertEqual(json.loads(json.dumps(num)), num)

if __name__ == '__main__':
    main()
