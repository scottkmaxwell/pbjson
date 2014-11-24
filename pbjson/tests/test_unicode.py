# -*- coding: utf-8 -*-

import os
from unittest import TestCase, main
import pbjson


class TestUnicode(TestCase):
    def test_european(self):
        original = ['Politique de Confidentialité', 'Política de Privacidad']
        pbj = pbjson.dumps(original)
        round_trip = pbjson.loads(pbj)
        self.assertEqual(original, round_trip)
        with open('temp.pbj', 'wb') as f:
            f.write(pbj)
        with open('temp.pbj', 'rb') as f:
            fpbj = f.read()
        self.assertEqual(pbj, fpbj)
        with open('temp.pbj', 'rb') as f:
            round_trip = pbjson.load(f)
        self.assertEqual(original, round_trip)
        # os.unlink('temp.pbj')

    def test_asian(self):
        original = ['その子は絶えずくすくす笑っていた', 'お役に立てば幸いです。']
        pbj = pbjson.dumps(original)
        round_trip = pbjson.loads(pbj)
        self.assertEqual(original, round_trip)
        with open('temp.pbj', 'wb') as f:
            f.write(pbj)
        with open('temp.pbj', 'rb') as f:
            fpbj = f.read()
        self.assertEqual(pbj, fpbj)
        with open('temp.pbj', 'rb') as f:
            round_trip = pbjson.load(f)
        self.assertEqual(original, round_trip)
        # os.unlink('temp.pbj')

if __name__ == '__main__':
    main()
